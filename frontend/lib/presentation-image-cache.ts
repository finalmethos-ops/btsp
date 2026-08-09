"use client";

import { useEffect, useRef, useState } from "react";

type PresentationImageCacheOptions = {
  activeImageId: string | null | undefined;
  cacheScope: string;
  loadImage: (imageId: string) => Promise<Blob>;
  maxEntries?: number;
  preloadImageIds?: string[];
};

async function decodedObjectUrl(blob: Blob): Promise<string | null> {
  const url = URL.createObjectURL(blob);
  if (typeof Image === "undefined") return url;
  const image = new Image();
  image.src = url;
  if (typeof image.decode !== "function") return url;
  try {
    await image.decode();
    return url;
  } catch {
    URL.revokeObjectURL(url);
    return null;
  }
}

export function touchPresentationImage(
  cache: Map<string, string>,
  imageId: string,
) {
  const url = cache.get(imageId) ?? null;
  if (!url) return null;
  cache.delete(imageId);
  cache.set(imageId, url);
  return url;
}

export function prunePresentationImages(
  cache: Map<string, string>,
  protectedIds: Set<string>,
  maxEntries: number,
) {
  while (cache.size > maxEntries) {
    let removableId: string | null = null;
    for (const imageId of cache.keys()) {
      if (!protectedIds.has(imageId)) {
        removableId = imageId;
        break;
      }
    }
    if (!removableId) return;
    const url = cache.get(removableId);
    if (url) URL.revokeObjectURL(url);
    cache.delete(removableId);
  }
}

export function usePresentationImageCache({
  activeImageId,
  cacheScope,
  loadImage,
  maxEntries = 8,
  preloadImageIds = [],
}: PresentationImageCacheOptions): string | null {
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const cacheRef = useRef(new Map<string, string>());
  const downloadsRef = useRef(new Map<string, symbol>());
  const activeImageIdRef = useRef(activeImageId);
  const generationRef = useRef(0);
  const preloadKey = preloadImageIds.join("|");

  useEffect(() => {
    const cache = cacheRef.current;
    const downloads = downloadsRef.current;
    generationRef.current += 1;
    for (const url of cache.values()) URL.revokeObjectURL(url);
    cache.clear();
    downloads.clear();
    setImageUrl(null);
    return () => {
      generationRef.current += 1;
      for (const url of cache.values()) URL.revokeObjectURL(url);
      cache.clear();
      downloads.clear();
    };
  }, [cacheScope]);

  useEffect(() => {
    activeImageIdRef.current = activeImageId;
    const requestedIds = Array.from(
      new Set(
        [activeImageId, ...(preloadKey ? preloadKey.split("|") : [])].filter(
          (imageId): imageId is string => Boolean(imageId),
        ),
      ),
    );
    const protectedIds = new Set(requestedIds);
    setImageUrl(
      activeImageId
        ? touchPresentationImage(cacheRef.current, activeImageId)
        : null,
    );

    for (const imageId of requestedIds) {
      if (cacheRef.current.has(imageId) || downloadsRef.current.has(imageId))
        continue;
      const downloadToken = Symbol(imageId);
      const generation = generationRef.current;
      downloadsRef.current.set(imageId, downloadToken);
      void loadImage(imageId)
        .then(decodedObjectUrl)
        .then((url) => {
          if (!url) return;
          if (generation !== generationRef.current) {
            URL.revokeObjectURL(url);
            return;
          }
          cacheRef.current.set(imageId, url);
          prunePresentationImages(
            cacheRef.current,
            protectedIds,
            Math.max(maxEntries, requestedIds.length),
          );
          if (activeImageIdRef.current === imageId) setImageUrl(url);
        })
        .catch(() => undefined)
        .finally(() => {
          if (downloadsRef.current.get(imageId) === downloadToken) {
            downloadsRef.current.delete(imageId);
          }
        });
    }
    prunePresentationImages(
      cacheRef.current,
      protectedIds,
      Math.max(maxEntries, requestedIds.length),
    );
  }, [activeImageId, loadImage, maxEntries, preloadKey]);

  return imageUrl;
}
