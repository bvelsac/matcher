# Visual Style

The application's styling must have the look of the reference image below. This is a
requirement from the user (10 October 2026). The current templates still use default
Bootstrap 5 (white background, blue navbar) and do not follow it yet.

![Style reference: grainy duotone close-up in pink and black](img/style-reference.webp)

The image is a mood reference for the look only. It is not an asset to use in the
application.

## The look

- **Duotone, almost two colours**: deep black with a hint of aubergine for the shadows, and a
  light pink-lilac for the highlights. Mid-tones are violet. There is hardly any other colour.
- **Hard contrast**: blacks are crushed and highlights are blown out. Large areas are pure
  black, with few grey transitions in between (posterised).
- **Analogue texture**: grain, video noise and a low-resolution, VHS-like softness with slight
  colour bleed at the edges.
- **Tight framing**: an extreme close-up that runs off the edges of the frame, with large dark
  areas as negative space.
- **A rare warm accent**: a small touch of peach or amber against the pink and black.
- **Mood**: nocturnal, raw, live on stage, like a club or concert film.

## Palette taken from the image

| Role | Colour | Share of the image |
|---|---|---|
| Background, black | `#030001` | ~45 % (with `#000000` and `#0c0007`) |
| Dark surface, aubergine | `#1c0719` | ~13 % |
| Violet, mid-tone | `#612d58` | ~12 % |
| Pink, muted | `#cf8dc9` | ~8 % |
| Pink-lilac, highlight | `#ffc0fc` | ~17 % |
| Warm accent, peach | `#eec19a` | well under 1 % |

These values are a starting point. The final tokens are set when the templates are restyled.

## To work out

- **Readability**: the tool is a workbench where the planner spends most of the day, with dense
  tables and forms. Body text and data should still meet WCAG AA contrast (pink-lilac on black
  does). Grain and noise belong on surfaces such as the navbar, headers and the login page, not
  behind text or tables.
- **Status colours** (confirmed, cancelled, changed since confirmation, warnings) have to remain
  distinguishable within or next to the duotone palette, not only through colour.
- **How to apply it**: probably by overriding Bootstrap 5's CSS variables in one shared
  stylesheet instead of styling each template separately.
