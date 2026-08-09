import { afterEach, describe, expect, it, vi } from "vitest";
import {
  prunePresentationImages,
  touchPresentationImage,
} from "./presentation-image-cache";

describe("presentation image cache", () => {
  afterEach(() => vi.restoreAllMocks());

  it("retains the active image and evicts the least-recent unprotected image", () => {
    const revoke = vi
      .spyOn(URL, "revokeObjectURL")
      .mockImplementation(() => undefined);
    const cache = new Map([
      ["slide-1", "blob:slide-1"],
      ["slide-2", "blob:slide-2"],
      ["slide-3", "blob:slide-3"],
    ]);

    expect(touchPresentationImage(cache, "slide-1")).toBe("blob:slide-1");
    expect([...cache.keys()]).toEqual(["slide-2", "slide-3", "slide-1"]);

    prunePresentationImages(cache, new Set(["slide-1"]), 2);

    expect([...cache.keys()]).toEqual(["slide-3", "slide-1"]);
    expect(revoke).toHaveBeenCalledWith("blob:slide-2");
  });

  it("does not evict images in the active preload window", () => {
    const revoke = vi
      .spyOn(URL, "revokeObjectURL")
      .mockImplementation(() => undefined);
    const cache = new Map([
      ["current", "blob:current"],
      ["next", "blob:next"],
    ]);

    prunePresentationImages(cache, new Set(["current", "next"]), 1);

    expect(cache.size).toBe(2);
    expect(revoke).not.toHaveBeenCalled();
  });
});
