# Canyon parallax set

Nine 1536 × 1024 PNGs generated with the built-in image_gen tool.

Each of `dawn/`, `noon/`, and `night/` contains:

- `far.png`: opaque sky and distant mesas; suggested scroll factor 0.15.
- `middle.png`: canyon walls with alpha; suggested scroll factor 0.45.
- `near.png`: rocky rim with alpha; suggested scroll factor 0.85.

Stack far → middle → near, aligning all three full canvases at the same origin and scale. Use standard alpha blending. Open `preview.html` in a browser to compare times and inspect scrolling or individual layers.

Noon and night were generated as lighting edits of the corresponding dawn layers. Major landmarks match visually, but exact pixel registration and seamless horizontal repeats are not guaranteed. The preview repeats the images so joins can be assessed before engine integration.

All nine PNG dimensions and color types were checked. The preview has not been browser-tested. Exact generation and edit prompts are recorded in `prompts.json`.
