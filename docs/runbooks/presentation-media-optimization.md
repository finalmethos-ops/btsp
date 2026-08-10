# Presentation Media Optimization

New live-presentation slide images are fully decoded during upload, limited to
40 megapixels, resized within 1920×1080, and converted to high-quality WebP when
that reduces transfer size. Vendor logos are limited to 1200×600 and use
lossless WebP. Already normalized WebP assets are not recompressed.

Existing assets can be measured without modifying data from the production
backend container:

```bash
docker compose --env-file .env.intranet -p btsp-intranet \
  -f docker-compose.yml -f docker-compose.production.yml \
  -f docker-compose.intranet.yml -f docker-compose.tunnel.yml \
  exec -T backend python -m scripts.optimize_presentation_images
```

Create and verify an encrypted database/file backup before applying the change.
Then repeat the command with both explicit mutation guards:

```bash
docker compose --env-file .env.intranet -p btsp-intranet \
  -f docker-compose.yml -f docker-compose.production.yml \
  -f docker-compose.intranet.yml -f docker-compose.tunnel.yml \
  exec -T backend python -m scripts.optimize_presentation_images \
  --apply --confirm OPTIMIZE_PRESENTATION_IMAGES
```

The command reports aggregate counts and byte totals without exposing slide
names or image content. Run the dry mode again afterward; `assets_changed`
should be zero. Validate the projector and presenter views before removing the
pre-change backup under the normal retention policy.
