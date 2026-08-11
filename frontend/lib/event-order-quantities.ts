import type { EventOrder } from "./event-ordering-api";
import type { EventProductSlide } from "./event-product-slide-api";

export type EventOrderQuantities = Record<string, number>;

export type EventOrderPayload = {
  quantity: number;
  variant_quantities: Record<string, number>;
};

export function initialEventOrderQuantities(
  slide: EventProductSlide,
  existingOrder: Pick<EventOrder, "quantity" | "variant_quantities"> | null,
): EventOrderQuantities {
  if (!existingOrder) return {};
  if (slide.product_variants.length) {
    return Object.fromEntries(
      slide.product_variants
        .filter(
          (variant) =>
            existingOrder.variant_quantities[variant.model_number] !==
            undefined,
        )
        .map((variant) => [
          variant.model_number,
          existingOrder.variant_quantities[variant.model_number],
        ]),
    );
  }
  return {
    __primary: existingOrder.quantity,
  };
}

function validWholeQuantity(value: number, label: string): number {
  if (!Number.isFinite(value) || !Number.isInteger(value) || value < 0) {
    throw new Error(
      `${label} quantity must be a whole number of zero or more.`,
    );
  }
  return value;
}

export function buildEventOrderPayload(
  slide: EventProductSlide,
  quantities: EventOrderQuantities,
): EventOrderPayload {
  if (slide.product_variants.length) {
    const variantQuantities = Object.fromEntries(
      slide.product_variants.map((variant) => {
        const quantity = validWholeQuantity(
          quantities[variant.model_number] ?? 0,
          variant.model_number,
        );
        if (quantity > 0 && quantity < variant.minimum_order_quantity) {
          throw new Error(
            `${variant.model_number} requires a minimum quantity of ${variant.minimum_order_quantity}.`,
          );
        }
        return [variant.model_number, quantity];
      }),
    );
    const quantity = Object.values(variantQuantities).reduce(
      (total, itemQuantity) => total + itemQuantity,
      0,
    );
    if (quantity < 1) {
      throw new Error("Enter a quantity for at least one product.");
    }
    return { quantity, variant_quantities: variantQuantities };
  }

  const quantity = validWholeQuantity(quantities.__primary ?? 0, "Product");
  if (quantity < slide.minimum_order_quantity) {
    throw new Error(
      `Quantity must meet the minimum order quantity of ${slide.minimum_order_quantity}.`,
    );
  }
  return { quantity, variant_quantities: {} };
}

export function eventOrderEstimatedSpend(
  slide: EventProductSlide,
  quantities: EventOrderQuantities,
): number {
  if (slide.product_variants.length) {
    return slide.product_variants.reduce(
      (total, variant) =>
        total +
        (quantities[variant.model_number] ?? 0) *
          Number(variant.event_unit_cost),
      0,
    );
  }
  return (quantities.__primary ?? 0) * Number(slide.event_unit_cost);
}
