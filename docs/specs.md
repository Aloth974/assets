# Technical specs

What `tools/check.py` enforces. The look is in [style.md](style.md).

## Families

| Family | Size | Shape | Other |
|---|---|---|---|
| `icons` | 256–512 px | square | opaque, full-bleed: background painted into every corner |
| `textures` | 1024 × 1024 px | square | opaque, seamless on both axes |

All images are PNG, RGB or fully opaque RGBA, at most 5 MB each.

**Icons** bake no rounded border, alpha fade, rarity frame, cooldown, count, letters or UI
state: the game adds those. Keep the silhouette clear of the corners.

**Textures** are the material itself, straight-on, filling the canvas: never a scene, an
object, a swatch or a contact sheet. Even density and lighting, no vignette, border or
focal point.

## Naming

Stems are lowercase `[a-z0-9_]`, starting with a letter. A brief's stem is its ID.

## Prompt starters

Paste one in front of the brief's description.

**Icon:**

```text
Square opaque 512 by 512 game icon for Apolarion, a stylised hand-painted fantasy MMO,
in the style of World of Warcraft icons. One dominant subject readable as a flat silhouette
at 32 px, one upper-left warm key light and cool violet bounce, bold painterly brushwork,
no pure black. Background painted into every corner. No border, frame, text, letters,
watermark or transparency.
```

**Texture:**

```text
Generate ONE square opaque 1024 by 1024 seamless repeating albedo texture for Apolarion,
a stylised hand-painted fantasy MMO, orthographic straight-on, filling the whole canvas.
The material itself, never a scene, object, swatch or contact sheet. Bold deliberate
painterly brushwork, broad readable material forms, gently rounded edges, painted soft
ambient shadow, restrained warm highlights with muted cool shadows. No photorealistic grain
or noisy microdetail. Moderate contrast and no pure black. Tiles continuously on BOTH axes
with even density and lighting; no vignette, border, spotlight or focal point. No lettering,
watermark, logos or symbols. No transparency.
```
