"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  createEventProductSlide,
  deleteEventProductSlide,
  EventFillerCategory,
  EventProductSlide,
  EventProductSlideWrite,
  EventProductWebFill,
  importEventProductImage,
  listEventProductSlides,
  reorderEventProductSlides,
  updateEventProductSlide,
  uploadEventProductImage,
  uploadEventSlideVendorLogo,
  webFillEventProduct,
} from "@/lib/event-product-slide-api";
import { ManagedSubEvent } from "@/lib/event-admin-api";
import { searchModelCatalog } from "@/lib/model-catalog-api";
import { VendorModel } from "@/lib/vendor-model-api";

const optionalNumber = (value: FormDataEntryValue | null) => {
  const text = String(value ?? "").trim();
  return text ? Number(text) : null;
};

type SlideProduct = EventProductSlide["product_variants"][number];

const emptySlideProduct = (): SlideProduct => ({
  model_number: "",
  name: "",
  event_unit_cost: "",
  standard_cost: null,
  minimum_order_quantity: 1,
});

export function EventProductSlideBuilder({
  subEvents,
}: {
  subEvents: ManagedSubEvent[];
}) {
  const [subEventId, setSubEventId] = useState(subEvents[0]?.id ?? "");
  const [slides, setSlides] = useState<EventProductSlide[]>([]);
  const [catalog, setCatalog] = useState<VendorModel[]>([]);
  const [catalogCode, setCatalogCode] = useState("");
  const [catalogVendorFilter, setCatalogVendorFilter] = useState("");
  const [catalogSearch, setCatalogSearch] = useState("");
  const [editing, setEditing] = useState<EventProductSlide | null>(null);
  const [slideProducts, setSlideProducts] = useState<SlideProduct[]>([]);
  const [slideType, setSlideType] = useState<"product" | "filler">("product");
  const [fillerCategory, setFillerCategory] =
    useState<EventFillerCategory>("trivia");
  const [productMode, setProductMode] = useState<"single" | "multiple">(
    "single",
  );
  const [draggingSlideId, setDraggingSlideId] = useState<string | null>(null);
  const [webFill, setWebFill] = useState<EventProductWebFill | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!subEvents.some((item) => item.id === subEventId)) {
      setSubEventId(subEvents[0]?.id ?? "");
    }
  }, [subEventId, subEvents]);

  useEffect(() => {
    void searchModelCatalog()
      .then(setCatalog)
      .catch(() => setCatalog([]));
  }, []);

  useEffect(() => {
    if (!subEventId) {
      setSlides([]);
      return;
    }
    void listEventProductSlides(subEventId)
      .then(setSlides)
      .catch((caught: unknown) =>
        setError(
          caught instanceof Error
            ? caught.message
            : "Unable to load the lineup.",
        ),
      );
  }, [subEventId]);

  const catalogProduct = catalog.find(
    (item) => item.product_code === catalogCode,
  );
  const catalogVendors = useMemo(
    () =>
      [
        ...new Set(catalog.map((item) => item.vendor_code).filter(Boolean)),
      ].sort(),
    [catalog],
  );
  const filteredCatalog = useMemo(() => {
    const query = catalogSearch.trim().toLowerCase();
    return catalog.filter((item) => {
      if (catalogVendorFilter && item.vendor_code !== catalogVendorFilter)
        return false;
      if (!query) return true;
      return [
        item.model_identifier,
        item.model_number,
        item.name,
        item.product_code,
      ]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(query));
    });
  }, [catalog, catalogSearch, catalogVendorFilter]);
  const defaults = editing ?? catalogProduct;

  async function refresh() {
    if (subEventId) setSlides(await listEventProductSlides(subEventId));
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!subEventId) return;
    const data = new FormData(event.currentTarget);
    const filler = slideType === "filler";
    const fullScreenImage = filler && fillerCategory === "full_screen_image";
    const multipleProducts = !filler && productMode === "multiple";
    const productImage = data.get("product_image");
    const vendorLogo = data.get("vendor_logo");
    if (
      fullScreenImage &&
      !editing?.has_image &&
      (!(productImage instanceof File) || productImage.size === 0)
    ) {
      setError("A full-screen image slide requires an uploaded image.");
      return;
    }
    if (multipleProducts && slideProducts.length < 2) {
      setError("A multiple-product slide requires at least two products.");
      return;
    }
    const firstProduct = multipleProducts ? slideProducts[0] : null;
    const payload: EventProductSlideWrite = {
      slide_type: slideType,
      filler_category: filler ? fillerCategory : null,
      catalog_product_code:
        filler || multipleProducts
          ? null
          : String(data.get("catalog_product_code") || "") || null,
      model_number: filler
        ? null
        : multipleProducts
          ? firstProduct!.model_number.trim()
          : String(data.get("model_number")).trim(),
      name: String(data.get(filler ? "filler_name" : "name")).trim(),
      vendor_code: filler
        ? null
        : String(data.get("vendor_code")).trim().toUpperCase(),
      category: filler
        ? null
        : String(data.get("category") || "").trim() || null,
      description: fullScreenImage
        ? null
        : String(
              data.get(filler ? "filler_description" : "description") || "",
            ) || null,
      specifications: filler
        ? null
        : String(data.get("specifications") || "") || null,
      event_unit_cost: filler
        ? null
        : multipleProducts
          ? String(firstProduct!.event_unit_cost)
          : String(data.get("event_unit_cost")),
      standard_cost: filler
        ? null
        : multipleProducts
          ? firstProduct!.standard_cost
            ? String(firstProduct!.standard_cost)
            : null
          : String(data.get("standard_cost") || "") || null,
      currency: String(data.get("currency") || "USD").toUpperCase(),
      minimum_order_quantity: filler
        ? 1
        : multipleProducts
          ? 1
          : Number(data.get("minimum_order_quantity")),
      available_inventory: filler
        ? null
        : optionalNumber(data.get("available_inventory")),
      max_event_units: filler
        ? null
        : optionalNumber(data.get("max_event_units")),
      allow_waitlist: !filler && data.get("allow_waitlist") === "on",
      delivery_window_start: filler
        ? null
        : String(data.get("delivery_window_start")),
      delivery_window_end: filler
        ? null
        : String(data.get("delivery_window_end")),
      vendor_delivery_notes:
        String(data.get("vendor_delivery_notes") || "") || null,
      presenter_notes: String(data.get("presenter_notes") || "") || null,
      product_variants:
        filler || !multipleProducts
          ? []
          : slideProducts.map((product) => ({
              ...product,
              model_number: product.model_number.trim(),
              name: product.name.trim(),
              event_unit_cost: String(product.event_unit_cost),
              standard_cost: product.standard_cost
                ? String(product.standard_cost)
                : null,
              minimum_order_quantity: Number(product.minimum_order_quantity),
            })),
      status: String(data.get("status")) as "draft" | "ready" | "archived",
    };
    setBusy(true);
    setError(null);
    try {
      const saved = editing
        ? await updateEventProductSlide(editing.id, payload)
        : await createEventProductSlide(subEventId, payload);
      if (productImage instanceof File && productImage.size > 0) {
        await uploadEventProductImage(saved.id, productImage);
      } else if (webFill?.image_url) {
        await importEventProductImage(saved.id, webFill.image_url);
      }
      if (!filler && vendorLogo instanceof File && vendorLogo.size > 0) {
        await uploadEventSlideVendorLogo(saved.id, vendorLogo);
      }
      await refresh();
      setEditing(null);
      setSlideType("product");
      setFillerCategory("trivia");
      setProductMode("single");
      setCatalogCode("");
      setSlideProducts([]);
      setWebFill(null);
      setMessage(editing ? "Slide updated." : "Slide added to the lineup.");
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Unable to save the slide.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function saveOrder(ordered: EventProductSlide[]) {
    setBusy(true);
    setError(null);
    try {
      setSlides(
        await reorderEventProductSlides(
          subEventId,
          ordered.map((item) => item.id),
        ),
      );
      setMessage("Presentation order updated.");
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Unable to reorder the lineup.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function moveTo(index: number, target: number) {
    if (
      index < 0 ||
      target < 0 ||
      index >= slides.length ||
      target >= slides.length ||
      index === target
    )
      return;
    const ordered = [...slides];
    const [moving] = ordered.splice(index, 1);
    ordered.splice(target, 0, moving);
    await saveOrder(ordered);
  }

  async function removeSlide(slide: EventProductSlide) {
    if (!window.confirm(`Remove slide “${slide.name}”?`)) return;
    setBusy(true);
    setError(null);
    try {
      await deleteEventProductSlide(slide.id);
      await refresh();
      if (editing?.id === slide.id) {
        setEditing(null);
        setSlideType("product");
        setFillerCategory("trivia");
        setProductMode("single");
        setSlideProducts([]);
      }
      setMessage("Slide removed.");
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Unable to remove the slide.",
      );
    } finally {
      setBusy(false);
    }
  }

  if (!subEvents.length) {
    return (
      <section className="event-ui rounded-2xl border border-dashed p-5 text-slate-600">
        Add a sub-event first, then build its live product presentation lineup.
      </section>
    );
  }

  return (
    <section className="event-ui rounded-2xl border p-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="brand-eyebrow">020B · Live buying</p>
          <h3 className="text-xl font-bold">
            Product lineup and slide builder
          </h3>
          <p className="text-sm text-slate-600">
            Drag slides or use the position controls. This lineup is the
            presenter’s live order.
          </p>
        </div>
        <label className="text-sm font-semibold">
          Sub-event
          <select
            className="ml-2 rounded-lg border p-2"
            onChange={(event) => {
              setSubEventId(event.target.value);
              setEditing(null);
              setSlideType("product");
              setFillerCategory("trivia");
              setProductMode("single");
              setSlideProducts([]);
            }}
            value={subEventId}
          >
            {subEvents.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
      </div>
      {message ? (
        <p className="mt-3 rounded-lg bg-green-50 p-2 text-green-800">
          {message}
        </p>
      ) : null}
      {error ? (
        <p className="mt-3 rounded-lg bg-red-50 p-2 text-red-800">{error}</p>
      ) : null}

      <div className="mt-5 grid gap-5 xl:grid-cols-[320px_1fr]">
        <div className="max-h-[72dvh] space-y-2 overflow-y-auto overscroll-contain pr-2">
          <div className="rounded-xl border border-blue-200 bg-blue-50 p-3">
            <strong className="text-sm text-blue-950">
              Presentation order
            </strong>
            <p className="mt-1 text-xs text-blue-800">
              Drag on desktop, or use the arrows and Move to control on any
              device.
            </p>
          </div>
          {slides.map((slide, index) => (
            <div
              className={`rounded-xl border bg-white p-3 transition ${draggingSlideId === slide.id ? "border-blue-500 opacity-60" : ""}`}
              draggable={!busy}
              key={slide.id}
              onDragEnd={() => setDraggingSlideId(null)}
              onDragOver={(event) => event.preventDefault()}
              onDragStart={() => setDraggingSlideId(slide.id)}
              onDrop={(event) => {
                event.preventDefault();
                const source = slides.findIndex(
                  (item) => item.id === draggingSlideId,
                );
                setDraggingSlideId(null);
                if (source >= 0) void moveTo(source, index);
              }}
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <span className="text-xs font-bold text-blue-800">
                    SLIDE {slide.position}
                  </span>
                  <strong className="block">
                    {slide.slide_type === "filler"
                      ? slide.filler_category?.replaceAll("_", " ")
                      : slide.model_number}
                  </strong>
                  <span className="text-sm">{slide.name}</span>
                </div>
                <div className="flex gap-1">
                  <button
                    aria-label="Move earlier"
                    className="min-h-10 min-w-10 rounded-lg border bg-slate-50 font-black disabled:opacity-30"
                    disabled={busy || index === 0}
                    onClick={() => void moveTo(index, index - 1)}
                    type="button"
                  >
                    ↑
                  </button>
                  <button
                    aria-label="Move later"
                    className="min-h-10 min-w-10 rounded-lg border bg-slate-50 font-black disabled:opacity-30"
                    disabled={busy || index === slides.length - 1}
                    onClick={() => void moveTo(index, index + 1)}
                    type="button"
                  >
                    ↓
                  </button>
                </div>
              </div>
              <p className="mt-2 text-xs text-slate-500">
                {slide.slide_type === "filler"
                  ? slide.filler_category === "full_screen_image"
                    ? "Full-screen image · non-ordering"
                    : "Non-ordering filler"
                  : slide.max_event_units
                    ? `${slide.max_event_units} unit event cap`
                    : "No event cap"}{" "}
                · {slide.status}
              </p>
              <label className="mt-2 block text-xs font-semibold text-slate-600">
                Move to
                <select
                  aria-label={`Move ${slide.name} to slide position`}
                  className="ml-2 min-h-10 rounded-lg border bg-white px-2"
                  disabled={busy}
                  onChange={(event) =>
                    void moveTo(index, Number(event.target.value))
                  }
                  value={index}
                >
                  {slides.map((_, position) => (
                    <option key={position} value={position}>
                      Slide {position + 1}
                    </option>
                  ))}
                </select>
              </label>
              <div className="mt-2 flex flex-wrap gap-2">
                <button
                  className="text-sm font-semibold text-blue-800"
                  onClick={() => {
                    setEditing(slide);
                    setSlideType(slide.slide_type);
                    setFillerCategory(slide.filler_category ?? "trivia");
                    setProductMode(
                      slide.product_variants.length ? "multiple" : "single",
                    );
                    setCatalogCode(slide.catalog_product_code ?? "");
                    setSlideProducts(slide.product_variants);
                  }}
                  type="button"
                >
                  Edit
                </button>
                <button
                  className="text-sm font-semibold text-red-700"
                  disabled={busy}
                  onClick={() => void removeSlide(slide)}
                  type="button"
                >
                  Delete slide
                </button>
                <label className="cursor-pointer text-sm font-semibold text-blue-800">
                  {slide.has_image ? "Replace image" : "Add image"}
                  <input
                    accept="image/png,image/jpeg,image/webp"
                    className="sr-only"
                    type="file"
                    onChange={(event) => {
                      const file = event.target.files?.[0];
                      if (file) {
                        setBusy(true);
                        void uploadEventProductImage(slide.id, file)
                          .then(refresh)
                          .catch((caught: unknown) =>
                            setError(
                              caught instanceof Error
                                ? caught.message
                                : "Image upload failed",
                            ),
                          )
                          .finally(() => setBusy(false));
                      }
                    }}
                  />
                </label>
                {slide.slide_type === "product" ? (
                  <label className="cursor-pointer text-sm font-semibold text-blue-800">
                    {slide.has_vendor_logo
                      ? "Replace vendor logo"
                      : "Add vendor logo"}
                    <input
                      accept="image/png,image/jpeg,image/webp"
                      className="sr-only"
                      type="file"
                      onChange={(event) => {
                        const file = event.target.files?.[0];
                        if (file) {
                          setBusy(true);
                          void uploadEventSlideVendorLogo(slide.id, file)
                            .then(refresh)
                            .catch((caught: unknown) =>
                              setError(
                                caught instanceof Error
                                  ? caught.message
                                  : "Vendor logo upload failed",
                              ),
                            )
                            .finally(() => setBusy(false));
                        }
                      }}
                    />
                  </label>
                ) : null}
              </div>
            </div>
          ))}
          {!slides.length ? (
            <p className="rounded-xl bg-slate-50 p-4 text-sm text-slate-500">
              No products in this lineup yet.
            </p>
          ) : null}
        </div>

        <form
          className="grid self-start gap-3 rounded-xl bg-slate-50 p-4 sm:grid-cols-2"
          key={`${editing?.id ?? "new"}-${slideType}-${fillerCategory}-${productMode}-${catalogCode}-${webFill?.source_url ?? ""}`}
          onSubmit={save}
        >
          <h4 className="font-bold sm:col-span-2">
            {editing ? `Edit slide ${editing.position}` : "Add lineup slide"}
          </h4>
          <label className="text-sm font-semibold sm:col-span-2">
            Slide type
            <select
              className="mt-1 w-full rounded-lg border bg-white p-2"
              onChange={(event) => {
                const mode = event.target.value as
                  | "product"
                  | "filler"
                  | "full_screen_image";
                setSlideType(mode === "full_screen_image" ? "filler" : mode);
                setFillerCategory(
                  mode === "full_screen_image" ? "full_screen_image" : "trivia",
                );
                setProductMode("single");
                setCatalogCode("");
                setSlideProducts([]);
                setWebFill(null);
              }}
              value={
                slideType === "filler" &&
                fillerCategory === "full_screen_image"
                  ? "full_screen_image"
                  : slideType
              }
            >
              <option value="product">Orderable product</option>
              <option value="filler">Non-ordering filler</option>
              <option value="full_screen_image">
                Full-screen image (intro, outro, or intermission)
              </option>
            </select>
          </label>
          {slideType === "filler" ? (
            <>
              {fillerCategory !== "full_screen_image" ? (
                <label className="text-sm font-semibold">
                  Filler category
                  <select
                    className="mt-1 w-full rounded-lg border bg-white p-2"
                    onChange={(event) =>
                      setFillerCategory(
                        event.target.value as EventFillerCategory,
                      )
                    }
                    name="filler_category"
                    required
                    value={fillerCategory}
                  >
                    <option value="trivia">Trivia</option>
                    <option value="giveaway">Giveaway</option>
                    <option value="sponsorship">Sponsorship</option>
                    <option value="special_thanks">Special thanks</option>
                    <option value="raffle">Raffle</option>
                  </select>
                </label>
              ) : null}
              <label className="text-sm font-semibold sm:col-span-2">
                {fillerCategory === "full_screen_image"
                  ? "Internal slide label"
                  : "Slide title"}
                <input
                  className="mt-1 w-full rounded-lg border bg-white p-2"
                  defaultValue={
                    editing?.name ??
                    (fillerCategory === "full_screen_image"
                      ? "Full-screen image"
                      : "")
                  }
                  name="filler_name"
                  required
                />
                {fillerCategory === "full_screen_image" ? (
                  <span className="mt-1 block font-normal text-slate-500">
                    Used in the editor and presenter monitor only; it is not
                    shown on the projector.
                  </span>
                ) : null}
              </label>
              {fillerCategory !== "full_screen_image" ? (
                <label className="text-sm font-semibold sm:col-span-2">
                  Slide content
                  <textarea
                    className="mt-1 min-h-32 w-full rounded-lg border bg-white p-2"
                    defaultValue={editing?.description ?? ""}
                    name="filler_description"
                  />
                </label>
              ) : null}
            </>
          ) : null}
          <fieldset
            className={slideType === "product" ? "contents" : "hidden"}
            disabled={slideType === "filler"}
          >
            <label className="text-sm font-semibold sm:col-span-2">
              Product layout
              <select
                className="mt-1 w-full rounded-lg border bg-white p-2"
                onChange={(event) => {
                  const nextMode = event.target.value as "single" | "multiple";
                  if (nextMode === "multiple" && !slideProducts.length) {
                    const form = event.currentTarget.form;
                    const data = form ? new FormData(form) : null;
                    setSlideProducts([
                      {
                        model_number: String(data?.get("model_number") ?? ""),
                        name: String(data?.get("name") ?? ""),
                        event_unit_cost: String(
                          data?.get("event_unit_cost") ?? "",
                        ),
                        standard_cost:
                          String(data?.get("standard_cost") ?? "") || null,
                        minimum_order_quantity: Number(
                          data?.get("minimum_order_quantity") ?? 1,
                        ),
                      },
                      emptySlideProduct(),
                    ]);
                  }
                  if (nextMode === "single") setSlideProducts([]);
                  setProductMode(nextMode);
                  setCatalogCode("");
                  setWebFill(null);
                }}
                value={productMode}
              >
                <option value="single">Single product</option>
                <option value="multiple">Multiple products</option>
              </select>
            </label>
            <label
              className={
                productMode === "single"
                  ? "text-sm font-semibold sm:col-span-2"
                  : "hidden"
              }
            >
              Start from BTSP catalog
              <div className="mt-1 grid gap-2 sm:grid-cols-2">
                <select
                  aria-label="Filter catalog by vendor"
                  className="w-full rounded-lg border bg-white p-2 font-normal"
                  onChange={(event) =>
                    setCatalogVendorFilter(event.target.value)
                  }
                  value={catalogVendorFilter}
                >
                  <option value="">All vendors</option>
                  {catalogVendors.map((vendor) => (
                    <option key={vendor} value={vendor}>
                      {vendor}
                    </option>
                  ))}
                </select>
                <input
                  aria-label="Search catalog models"
                  className="w-full rounded-lg border bg-white p-2 font-normal"
                  onChange={(event) => setCatalogSearch(event.target.value)}
                  placeholder="Search model or product name"
                  value={catalogSearch}
                />
              </div>
              <select
                className="mt-1 w-full rounded-lg border bg-white p-2"
                disabled={productMode === "multiple"}
                name="catalog_product_code"
                onChange={(event) => {
                  setCatalogCode(event.target.value);
                  setEditing(null);
                  setFillerCategory("trivia");
                  setSlideProducts([]);
                  setWebFill(null);
                }}
                value={catalogCode}
              >
                <option value="">Manual event product</option>
                {filteredCatalog.map((item) => (
                  <option key={item.product_code} value={item.product_code}>
                    {item.model_identifier} — {item.name}
                  </option>
                ))}
              </select>
            </label>
            <label
              className={
                productMode === "single" ? "text-sm font-semibold" : "hidden"
              }
            >
              Model number
              <input
                className="mt-1 w-full rounded-lg border bg-white p-2"
                defaultValue={defaults?.model_number ?? ""}
                disabled={productMode === "multiple"}
                name="model_number"
                required
              />
            </label>
            <label className="text-sm font-semibold">
              Vendor code
              <input
                className="mt-1 w-full rounded-lg border bg-white p-2"
                defaultValue={defaults?.vendor_code ?? ""}
                name="vendor_code"
                required
              />
            </label>
            <label
              className={
                productMode === "single"
                  ? "text-sm font-semibold sm:col-span-2"
                  : "hidden"
              }
            >
              Product name
              <input
                className="mt-1 w-full rounded-lg border bg-white p-2"
                defaultValue={defaults?.name ?? ""}
                disabled={productMode === "multiple"}
                name="name"
                required
              />
            </label>
            {productMode === "multiple" ? (
              <label className="text-sm font-semibold sm:col-span-2">
                Slide headline
                <input
                  className="mt-1 w-full rounded-lg border bg-white p-2"
                  defaultValue={editing?.name ?? "Multiple-product offer"}
                  name="name"
                  required
                />
                <span className="mt-1 block font-normal text-slate-500">
                  This shared title replaces the single-product name on the
                  presentation.
                </span>
              </label>
            ) : null}
            <label className="text-sm font-semibold sm:col-span-2">
              Product category
              <input
                className="mt-1 w-full rounded-lg border bg-white p-2"
                defaultValue={
                  editing?.category ??
                  catalogProduct?.product_category_code ??
                  catalogProduct?.department ??
                  ""
                }
                maxLength={128}
                name="category"
                placeholder="For example: Appliances, Furniture, or Electronics"
              />
              <span className="mt-1 block font-normal text-slate-500">
                This label appears on the live projector display and may be
                edited for this event offer.
              </span>
            </label>
            <div
              className={
                productMode === "single"
                  ? "flex items-end sm:col-span-2"
                  : "hidden"
              }
            >
              <button
                className="rounded-lg border border-blue-300 bg-white px-4 py-2 font-semibold text-blue-800"
                disabled={busy}
                onClick={(event) => {
                  const form = event.currentTarget.form;
                  if (!form) return;
                  const data = new FormData(form);
                  const modelNumber = String(
                    data.get("model_number") || "",
                  ).trim();
                  if (!modelNumber) {
                    setError(
                      "Enter or select a model number before using Web Fill.",
                    );
                    return;
                  }
                  setBusy(true);
                  setError(null);
                  void webFillEventProduct(
                    modelNumber,
                    String(data.get("name") || ""),
                  )
                    .then(setWebFill)
                    .catch((caught: unknown) =>
                      setError(
                        caught instanceof Error
                          ? caught.message
                          : "Web Fill failed",
                      ),
                    )
                    .finally(() => setBusy(false));
                }}
                type="button"
              >
                Search model on web & fill slide
              </button>
            </div>
            {webFill && productMode === "single" ? (
              <div className="rounded-lg border border-blue-200 bg-blue-50 p-3 text-sm sm:col-span-2">
                <strong>{webFill.title}</strong>
                <p className="mt-1">{webFill.summary}</p>
                <a
                  className="mt-2 inline-block font-semibold text-blue-800 underline"
                  href={webFill.source_url}
                  rel="noreferrer"
                  target="_blank"
                >
                  Review source
                </a>
                {webFill.image_url ? (
                  <p className="mt-1 text-green-800">
                    A web image will be imported when the slide is saved.
                  </p>
                ) : (
                  <p className="mt-1 text-amber-800">
                    No usable image was returned; upload one below.
                  </p>
                )}
              </div>
            ) : null}
            <label className="text-sm font-semibold sm:col-span-2">
              Description
              <textarea
                className="mt-1 w-full rounded-lg border bg-white p-2"
                defaultValue={webFill?.summary ?? editing?.description ?? ""}
                name="description"
              />
            </label>
            <label className="text-sm font-semibold sm:col-span-2">
              Specifications
              <textarea
                className="mt-1 w-full rounded-lg border bg-white p-2"
                defaultValue={editing?.specifications ?? ""}
                name="specifications"
              />
            </label>
            {productMode === "multiple" ? (
              <div className="rounded-xl border bg-white p-3 sm:col-span-2">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <strong className="text-sm">Products on this slide</strong>
                    <p className="mt-1 text-xs font-normal text-slate-500">
                      Add every orderable model included in this combined offer.
                    </p>
                  </div>
                  <button
                    className="rounded-lg border border-blue-300 bg-blue-50 px-3 py-2 text-sm font-semibold text-blue-900"
                    disabled={slideProducts.length >= 50}
                    onClick={(event) => {
                      const form = event.currentTarget.form;
                      const data = form ? new FormData(form) : null;
                      setSlideProducts((current) => {
                        if (current.length)
                          return [...current, emptySlideProduct()];
                        return [
                          {
                            model_number: String(
                              data?.get("model_number") ?? "",
                            ),
                            name: String(data?.get("name") ?? ""),
                            event_unit_cost: String(
                              data?.get("event_unit_cost") ?? "",
                            ),
                            standard_cost:
                              String(data?.get("standard_cost") ?? "") || null,
                            minimum_order_quantity: Number(
                              data?.get("minimum_order_quantity") ?? 1,
                            ),
                          },
                          emptySlideProduct(),
                        ];
                      });
                    }}
                    type="button"
                  >
                    + Add another product
                  </button>
                </div>
                <div className="mt-3 grid gap-3">
                  {slideProducts.map((product, index) => (
                    <fieldset
                      className="grid gap-2 rounded-lg border border-slate-200 bg-slate-50 p-3 sm:grid-cols-2"
                      key={index}
                    >
                      <legend className="px-1 text-xs font-bold uppercase text-blue-900">
                        Product {index + 1}
                      </legend>
                      <label className="text-xs font-semibold sm:col-span-2">
                        Fill from catalog
                        <select
                          className="mt-1 w-full rounded-lg border bg-white p-2 font-normal"
                          onChange={(event) => {
                            const selected = catalog.find(
                              (item) =>
                                item.product_code === event.target.value,
                            );
                            if (!selected) return;
                            setSlideProducts((current) =>
                              current.map((item, itemIndex) =>
                                itemIndex === index
                                  ? {
                                      model_number:
                                        selected.model_number ??
                                        selected.model_identifier,
                                      name: selected.name,
                                      event_unit_cost: selected.unit_price,
                                      standard_cost: selected.unit_price,
                                      minimum_order_quantity: Number(
                                        selected.minimum_order_quantity ?? 1,
                                      ),
                                    }
                                  : item,
                              ),
                            );
                          }}
                          value=""
                        >
                          <option value="">
                            Select an optional catalog product
                          </option>
                          {filteredCatalog.map((item) => (
                            <option
                              key={item.product_code}
                              value={item.product_code}
                            >
                              {item.model_identifier} — {item.name}
                            </option>
                          ))}
                        </select>
                      </label>
                      {[
                        ["Model number", "model_number", "text"],
                        ["Product name", "name", "text"],
                        ["Event price", "event_unit_cost", "number"],
                        ["Standard Cost", "standard_cost", "number"],
                        ["MOQ", "minimum_order_quantity", "number"],
                      ].map(([label, field, type]) => (
                        <label
                          className={`text-xs font-semibold ${field === "name" ? "sm:col-span-2" : ""}`}
                          key={field}
                        >
                          {label}
                          <input
                            className="mt-1 w-full rounded-lg border bg-white p-2"
                            min={
                              type === "number"
                                ? field === "minimum_order_quantity"
                                  ? 1
                                  : 0
                                : undefined
                            }
                            onChange={(event) =>
                              setSlideProducts((current) =>
                                current.map((item, itemIndex) =>
                                  itemIndex === index
                                    ? {
                                        ...item,
                                        [field]:
                                          field === "minimum_order_quantity"
                                            ? Number(event.target.value)
                                            : event.target.value,
                                      }
                                    : item,
                                ),
                              )
                            }
                            required
                            step={
                              type === "number" &&
                              field !== "minimum_order_quantity"
                                ? "0.01"
                                : undefined
                            }
                            type={type}
                            value={product[field as keyof SlideProduct] ?? ""}
                          />
                        </label>
                      ))}
                      <button
                        className="justify-self-start text-sm font-semibold text-red-700 sm:col-span-2"
                        onClick={() =>
                          setSlideProducts((current) =>
                            current.filter(
                              (_, itemIndex) => itemIndex !== index,
                            ),
                          )
                        }
                        type="button"
                      >
                        Remove product
                      </button>
                    </fieldset>
                  ))}
                </div>
              </div>
            ) : null}
            <label
              className={
                productMode === "single" ? "text-sm font-semibold" : "hidden"
              }
            >
              Event unit cost
              <input
                className="mt-1 w-full rounded-lg border bg-white p-2"
                defaultValue={
                  editing?.event_unit_cost ?? catalogProduct?.unit_price ?? ""
                }
                min="0"
                name="event_unit_cost"
                disabled={productMode === "multiple"}
                required
                step="0.01"
                type="number"
              />
            </label>
            <label
              className={
                productMode === "single" ? "text-sm font-semibold" : "hidden"
              }
            >
              Standard Cost
              <input
                className="mt-1 w-full rounded-lg border bg-white p-2"
                defaultValue={
                  editing?.standard_cost ?? catalogProduct?.unit_price ?? ""
                }
                min="0"
                name="standard_cost"
                disabled={productMode === "multiple"}
                step="0.01"
                type="number"
              />
            </label>
            <label className="text-sm font-semibold">
              Currency
              <input
                className="mt-1 w-full rounded-lg border bg-white p-2"
                defaultValue={defaults?.currency ?? "USD"}
                maxLength={3}
                name="currency"
                required
              />
            </label>
            <label
              className={
                productMode === "single" ? "text-sm font-semibold" : "hidden"
              }
            >
              MOQ
              <input
                className="mt-1 w-full rounded-lg border bg-white p-2"
                defaultValue={
                  editing?.minimum_order_quantity ??
                  Number(catalogProduct?.minimum_order_quantity ?? 1)
                }
                min="1"
                name="minimum_order_quantity"
                disabled={productMode === "multiple"}
                required
                type="number"
              />
            </label>
            <label className="text-sm font-semibold">
              Available inventory
              <input
                className="mt-1 w-full rounded-lg border bg-white p-2"
                defaultValue={editing?.available_inventory ?? ""}
                min="0"
                name="available_inventory"
                type="number"
              />
            </label>
            <label className="text-sm font-semibold">
              Maximum event units
              <input
                className="mt-1 w-full rounded-lg border bg-white p-2"
                defaultValue={editing?.max_event_units ?? ""}
                min="1"
                name="max_event_units"
                type="number"
              />
            </label>
            <label className="text-sm font-semibold">
              Delivery window start
              <input
                className="mt-1 w-full rounded-lg border bg-white p-2"
                defaultValue={editing?.delivery_window_start ?? ""}
                name="delivery_window_start"
                required
                type="date"
              />
            </label>
            <label className="text-sm font-semibold">
              Delivery window end
              <input
                className="mt-1 w-full rounded-lg border bg-white p-2"
                defaultValue={editing?.delivery_window_end ?? ""}
                name="delivery_window_end"
                required
                type="date"
              />
            </label>
            <label className="flex items-center gap-2 text-sm font-semibold">
              <input
                defaultChecked={editing?.allow_waitlist ?? false}
                name="allow_waitlist"
                type="checkbox"
              />{" "}
              Allow waitlist above event cap
            </label>
          </fieldset>
          <label className="text-sm font-semibold">
            Slide status
            <select
              className="mt-1 w-full rounded-lg border bg-white p-2"
              defaultValue={editing?.status ?? "draft"}
              name="status"
            >
              <option value="draft">Draft</option>
              <option value="ready">Ready</option>
              <option value="archived">Archived</option>
            </select>
          </label>
          <label className="text-sm font-semibold sm:col-span-2">
            {fillerCategory === "full_screen_image"
              ? "Full-screen slide image"
              : "Slide image"}
            <input
              accept="image/png,image/jpeg,image/webp"
              className="mt-1 block w-full rounded-lg border bg-white p-2"
              name="product_image"
              required={
                fillerCategory === "full_screen_image" && !editing?.has_image
              }
              type="file"
            />
            <span className="mt-1 block font-normal text-slate-500">
              {fillerCategory === "full_screen_image"
                ? "Use a high-resolution 16:9 image (ideally 1920 × 1080). The projector shows only this image, without headers or overlays."
                : "Upload an image now. Product slides can also use Web Fill."}
            </span>
          </label>
          {slideType === "product" ? (
            <>
              <label className="text-sm font-semibold sm:col-span-2">
                Vendor logo
                <input
                  accept="image/png,image/jpeg,image/webp"
                  className="mt-1 block w-full rounded-lg border bg-white p-2"
                  name="vendor_logo"
                  type="file"
                />
                <span className="mt-1 block font-normal text-slate-500">
                  Optional. PNG with a transparent background is recommended.
                  The logo appears at the bottom of the projector Offer Details
                  panel.
                </span>
              </label>
              <label className="text-sm font-semibold sm:col-span-2">
                Vendor delivery notes
                <textarea
                  className="mt-1 w-full rounded-lg border bg-white p-2"
                  defaultValue={editing?.vendor_delivery_notes ?? ""}
                  name="vendor_delivery_notes"
                />
              </label>
            </>
          ) : null}
          <label className="text-sm font-semibold sm:col-span-2">
            Private presenter notes
            <textarea
              className="mt-1 w-full rounded-lg border bg-white p-2"
              defaultValue={editing?.presenter_notes ?? ""}
              name="presenter_notes"
            />
          </label>
          <div className="flex justify-end gap-2 sm:col-span-2">
            {editing ? (
              <button
                className="rounded-lg border px-4 py-2 font-semibold"
                onClick={() => {
                  setEditing(null);
                  setSlideType("product");
                  setFillerCategory("trivia");
                  setProductMode("single");
                  setCatalogCode("");
                  setSlideProducts([]);
                }}
                type="button"
              >
                Cancel edit
              </button>
            ) : null}
            <button
              className="rounded-lg bg-blue-800 px-5 py-2 font-semibold text-white"
              disabled={busy}
              type="submit"
            >
              {busy ? "Saving…" : editing ? "Save slide" : "Add to lineup"}
            </button>
          </div>
        </form>
      </div>
    </section>
  );
}
