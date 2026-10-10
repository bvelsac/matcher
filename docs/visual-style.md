# Visual Style

PDC has a **gritty, pixelated black-and-white look, coloured with the palette of the reference
images**, and uses **Arial** throughout. These are requirements from the user (10 October 2026).
The style is built: `static/css/pdc.css` on top of Bootstrap 5.3 in dark mode, with the images in
`static/img`.

## References

![Style reference: grainy duotone close-up in pink and black](img/style-reference.webp)

![The eye: extreme close-up, the background of PDC](img/eye-reference.png)

The images come from concert footage. The user gave explicit permission to use them in the
application (10 October 2026). A second reference (the face behind a microphone, from the same
footage) was shown in the conversation but is not in the repository; the eye above is cropped
from it.

## The look

- **Duotone, almost two colours**: deep black with a hint of aubergine for the shadows, and a
  light pink-lilac for the highlights. Mid-tones are violet. There is hardly any other colour.
- **Hard contrast**: blacks are crushed and highlights are blown out, with few grey transitions
  in between (posterised).
- **Gritty and pixelated**: grain, coarse pixel clusters, low resolution.
- **Tight framing**: an extreme close-up that runs off the edges, with large dark areas.
- **A rare warm accent**: a small touch of peach against the pink and black.
- **Mood**: nocturnal, raw, live on stage.

## How it is applied

- **Font**: Arial (with Helvetica and sans-serif as fallbacks), for everything. Page titles,
  card titles, buttons, labels and table headers are bold upper case with wide letter spacing.
- **Background**: the eye, reduced to 200 pixels wide, mapped onto the palette with ordered
  dithering, and enlarged by the browser without smoothing (`image-rendering: pixelated`), so it
  shows as coarse pixels. It is faded behind the working screens (20 % opacity, less
  saturation) and shows more on the login page (55 %). A tile of loose pink pixels lies over it
  for grain.
- **Navbar**: black with a pink line, and below it a strip of pink pixels that thins out.
- **Surfaces**: cards are near-black and slightly transparent, so the eye stays faintly visible;
  card headers carry a softened grain. All corners are square.
- **Buttons**: filled pink with black text, inverting to black with pink text on hover; outline
  buttons fill with their colour on hover.
- **Images**: `tools/style_assets.py` builds `eye.png`, `grain.png` and `edge.png` in
  `static/img` from the reference image.

## Palette

| Role | Colour | Use |
|---|---|---|
| Black | `#030001` | page background, text on light colours |
| Ink | `#0c0007` | surfaces |
| Aubergine | `#1c0719` | headers, table heads, input add-ons |
| Violet | `#612d58` | lines and borders, secondary buttons and badges |
| Pink, muted | `#cf8dc9` | secondary text, info |
| Pink-lilac | `#ffc0fc` | text, primary buttons, active navigation |
| Lavender | `#cfa1ee` | success |
| Peach | `#eec19a` | warning |
| Coral | `#f2907e` | danger, delete buttons |

Lavender, peach and coral also come from the images (the rare cooler and warmer touches), so
that statuses stay distinguishable within the palette. All text colours reach at least 7:1
against black (pink-lilac 14:1), well above WCAG AA; violet is only used for lines and as a
background behind pink-lilac (7:1). Statuses also carry an icon or a label, not only a colour.
`tests/test_browser.py` checks the font, the background and the contrast of buttons and badges.
