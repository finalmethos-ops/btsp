import { describe, expect, it } from "vitest";
import {
  buildEventOrderPayload,
  eventOrderEstimatedSpend,
  initialEventOrderQuantities,
} from "./event-order-quantities";
import type { EventProductSlide } from "./event-product-slide-api";

const slide = {
  id: "slide-1",
  model_number: "COMBINED",
  name: "Combined offer",
  event_unit_cost: "100.00",
  minimum_order_quantity: 1,
  product_variants: [
    {
      model_number: "MODEL-A",
      name: "Model A",
      event_unit_cost: "100.00",
      standard_cost: "130.00",
      minimum_order_quantity: 1,
      available_inventory: 50,
      max_event_units: 40,
    },
    {
      model_number: "MODEL-B",
      name: "Model B",
      event_unit_cost: "250.50",
      standard_cost: "300.00",
      minimum_order_quantity: 2,
      available_inventory: 30,
      max_event_units: 20,
    },
  ],
} as EventProductSlide;

describe("combined-slide order quantities", () => {
  it("restores each saved product quantity independently", () => {
    const existingOrder = {
      quantity: 5,
      variant_quantities: { "MODEL-A": 3, "MODEL-B": 2 },
    };

    expect(initialEventOrderQuantities(slide, existingOrder)).toEqual({
      "MODEL-A": 3,
      "MODEL-B": 2,
    });
  });

  it("builds an independent quantity map and weighted total", () => {
    const quantities = { "MODEL-A": 3, "MODEL-B": 2 };

    expect(buildEventOrderPayload(slide, quantities)).toEqual({
      quantity: 5,
      variant_quantities: quantities,
    });
    expect(eventOrderEstimatedSpend(slide, quantities)).toBe(801);
  });

  it("permits skipping a product but enforces its minimum when selected", () => {
    expect(
      buildEventOrderPayload(slide, { "MODEL-A": 1, "MODEL-B": 0 }),
    ).toEqual({
      quantity: 1,
      variant_quantities: { "MODEL-A": 1, "MODEL-B": 0 },
    });
    expect(() =>
      buildEventOrderPayload(slide, { "MODEL-A": 1, "MODEL-B": 1 }),
    ).toThrow("MODEL-B requires a minimum quantity of 2");
  });

  it("rejects empty, fractional, and negative combined orders locally", () => {
    expect(() =>
      buildEventOrderPayload(slide, { "MODEL-A": 0, "MODEL-B": 0 }),
    ).toThrow("Enter a quantity for at least one product");
    expect(() =>
      buildEventOrderPayload(slide, { "MODEL-A": 1.5, "MODEL-B": 0 }),
    ).toThrow("MODEL-A quantity must be a whole number");
    expect(() =>
      buildEventOrderPayload(slide, { "MODEL-A": -1, "MODEL-B": 0 }),
    ).toThrow("MODEL-A quantity must be a whole number");
  });
});
