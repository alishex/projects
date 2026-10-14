# Original visual assets

All imagery in `public/assets/` is original, hand-authored inline SVG — not photographs, and not AI-generated raster images (this environment had no image-generation tool available). Each file is self-contained (no external fonts, no external image requests) and uses only the Dark Rose design tokens from `style.css`. Every icon is deliberately abstract/geometric — a stylized silhouette and accent color, not a literal or explicit rendering — appropriate as a tasteful placeholder for this product category.

Each of the 12 demo products has its own distinct silhouette and accent tint — no single graphic is reused across the catalog.

- `hero.svg` — a wide cinematic composition: a near-black gradient, a soft burgundy side-glow, and an abstract faceted silhouette, leaving negative space on the left for the campaign headline.
- `velvet-touch.svg`, `silk-wand-red.svg`, `onyx-pulse.svg`, `dual-harmony.svg`, `twilight-teaser.svg` — distinct abstract massager silhouettes.
- `noir-probe.svg`, `velvet-plug-classic.svg`, `rose-jewel-plug.svg` — distinct abstract silhouettes for the anal-care line.
- `kama-sutra-cards.svg` — a fanned card-deck icon.
- `saqlash-xaltachasi.svg` — a drawstring pouch icon.
- `silk-glide-lubrikant.svg`, `tozalovchi-sprey.svg` — bottle/spray icons for the care companions.
- `favicon.svg` — an "IS" (INTIM SHOP) monogram in dark rose.

**These are explicitly placeholder graphics, not product photography.** The storefront marks the catalog as a demo (`DEMO_MODE=true`) specifically because of this. Before taking real orders, replace each product's image through the admin panel (`/admin` → Mahsulotlar → Tahrirlash → Rasmlar) with real photography of your actual stock, then set `DEMO_MODE=false` in `.env`.
