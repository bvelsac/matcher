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
- **Background, one per screen**: a part of the reference images, reduced to 200 pixels wide,
  mapped onto the palette with ordered dithering, and enlarged by the browser without smoothing
  (`image-rendering: pixelated`), so it shows as coarse pixels. The login page has the eye; the
  other screens each have a part cut from the first photo (table below). It is faded behind the
  working screens (20 % opacity, less saturation) and shows more on the login page (55 %). A
  tile of loose pink pixels lies over it for grain.
- **Accent, one per screen**: the other tints found in the images. The accent colours the active
  menu item, the icon of the page title, the bar on the left of card headers, the line under
  table headers, and the navbar line with the strip of pixels below it.
- **Navbar**: black with a line in the accent colour, and below it a strip of pixels that thins
  out.
- **Surfaces**: cards are near-black and slightly transparent, so the background stays faintly
  visible;
  card headers carry a softened grain. All corners are square.
- **Buttons**: filled pink with black text, inverting to black with pink text on hover; outline
  buttons fill with their colour on hover.
- **Images**: `tools/style_assets.py` builds `eye.png`, the `bg-*.png` backgrounds, `grain.png`
  and `edge.png` in `static/img` from the reference images.

## Screens

| Screen | Background | Accent |
|---|---|---|
| Login | the eye (`eye-reference.png`) | pink-lilac |
| Dashboard | eye and eyebrow, from the first photo | gold |
| Interpreters | hand on the microphone | rose |
| Add or edit an interpreter | beard | rose |
| Meetings | mouth and cigarette | lavender |
| Add or edit a meeting | nose | lavender |
| Error pages | forehead and eyebrow | salmon |

A screen chooses its look with a class on `<body>` (`screen-dashboard`, `screen-meetings`, ...),
set in the template's `body_class` block. A new screen gets a new class, a new crop in
`tools/style_assets.py` and an entry in `tests/test_browser.py`.

## Palette

| Role | Colour | Use |
|---|---|---|
| Black | `#030001` | page background, text on light colours |
| Ink | `#0c0007` | surfaces |
| Aubergine | `#1c0719` | headers, table heads, input add-ons |
| Violet | `#612d58` | lines and borders, secondary buttons and badges |
| Pink, muted | `#cf8dc9` | secondary text, info |
| Pink-lilac | `#ffc0fc` | text, primary buttons, accent of the login page |
| Lavender | `#cfa1ee` | success |
| Peach | `#eec19a` | warning |
| Coral | `#f2907e` | danger, delete buttons |
| Gold | `#fedb95` | accent of the dashboard |
| Rose | `#fbb4c2` | accent of the interpreter screens |
| Salmon | `#fec6b8` | accent of the error pages |

Lavender, peach, coral, gold, rose and salmon also come from the images (the rare cooler and
warmer touches: the analysis grouped the saturated pixels by hue), so that statuses and accents
stay within the palette. Lavender is both the accent of the meeting screens and the colour of
success; statuses always carry an icon or a label as well. All text colours reach at least 7:1
against black (pink-lilac 14:1), well above WCAG AA; violet is only used for lines and as a
background behind pink-lilac (7:1). `tests/test_browser.py` checks the font, the background and
accent of every screen, and the contrast of buttons, badges and the active menu item.
