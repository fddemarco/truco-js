# Art prompts: avatars, señas and cards

The table art is raster images made with an image model from the prompts below. Source art lives in `assets/` at the repo root, which is gitignored. Only the imported WebPs in `frontend/static/` are committed.

## Workflow

**Avatars.** The model returns galleries: grids of cells, usually 3×3, often with a fake checkerboard baked into the pixels. `tools/art/avatars.py` turns them into sprites (run it with `uv run`; it brings its own dependencies):

1. **Start a character** from its base image and a first gallery:
   `uv run tools/art/avatars.py init <id> --base <base image> --sheet <gallery>`.
   The frame is that gallery's head-and-shoulders cell (`--ref-cell`, 6 by default). This writes `assets/avatars/approved/<id>/base.png`, the neutral face in that frame and the table's resting image, and `portrait.png`, the full character for avatar selection.
2. **Process a gallery:** `uv run tools/art/avatars.py sheet <id> <gallery> [--grid 3x3]`.
   - It removes the background from every cell and aligns the cell to the character's `base.png` by the hair/hat silhouette, so the head never moves when a seña plays.
   - A hat cut off by the cell edge is rebuilt from the neutral face.
   - White, checkerboard and black backgrounds are removed, and a uniform grey frame around a cell is stripped. A black background is turned white first, keeping a line-width band next to the drawing as its outline. Black shapes touching it (headphones) can't be told apart from it, so for those cells the body below the chin is rebuilt from the neutral face. The tool warns about any cell it can't cut out. White or checkerboard backgrounds still give the cleanest results.
   - Output goes to `assets/avatars/candidates/<id>/`: one PNG per cell, plus `<gallery>-review.png` showing the neutral and every cell at 200 px and at the table's 80 px.
3. **Mirror** instead of regenerating when a seña has a mirror-image partner. Image models rarely put a wink or a mouth corner on the requested side, so 03 is built from the approved 04, and 02 from a wink on the wrong eye:
   `uv run tools/art/avatars.py mirror <id> <source> <seña> --box X0,Y0,X1,Y1`.
   Inside the box, the source is replaced by its reflection across the face's own symmetry axis; hair, hats and props outside it stay put. `tools/art/mirror-recipes.sh` records the commands and boxes used for every mirrored seña, with tips for picking boxes.
4. **Review** each candidate against the bar below. Then move it to `approved/<id>/<seña>.png`, `alternates/<id>/` (passes, but not the pick) or `failed/<id>/` (name the reason in the file name). Keep the status in `assets/avatars/REVIEW.md`.

**Cards.** Save them as `assets/cards/<name>.png` (names in §2.5); they need no processing.

Then run `cd frontend && pnpm import-art`. It lists missing or misnamed files and writes nothing until the set is complete; `--partial` imports what is there. Avatar variants are not trimmed, because they share the frame. Check the result in the app (`make dev`) and commit `frontend/static/avatars/` and `frontend/static/cards/`.

### Review bar (avatars)

A cell is approved only if all of these hold:

- **Right gesture, and only that one.** For example, an 01 with the mouth open also reads as 07. A hand gesture or closed eyes (the old 11) is not a seña.
- **Right side** (C.1). The character's right is the image's left: 02 winks the eye on the image's left, 03 pulls the corner toward the image's left, and 04 toward the image's right.
- **Readable at 80 px** next to the neutral face. Check the bottom row of the review sheet. Moustaches and hair easily hide mouth señas.
- **Same character and frame:** outfit, colours and props match, and nothing is cut off in the aligned frame.

Total: **54 avatar images** (6 characters × 9) and **51 cards** (48 + 2 comodines + dorso).

---

## Part 1: Avatars

### 1.1 Style guide (paste at the top of every avatar prompt)

> Character portrait in a **pngtuber style**: a cute, expressive **stickman** with a big round head (about 45% of the image height), a simple thin stick body, stick arms and round mitten hands. Thick clean dark outlines (#2b2b2b), flat colours with one soft cel-shading tone, small blush marks. Bust shot from the waist up, facing the viewer straight on, **centred on a fully transparent background**, square 1024×1024. The whole head and both arms are inside the frame. Both hands rest in front of the chest holding a small fan of three face-down cards with dark red backs. The face is large, clear and **never covered** by hands, hair, glasses lenses or props. No text, no logo, no background scenery, no drop shadow.

Why these constraints:

- The reglamento forbids covering the face (Anexo C.1), and señas must read at the table's size of about **80 px**. Faces must stay big and uncluttered, and eyebrows, eyes, mouth and nose must stay clearly visible.
- Every seña is a facial gesture. There is no 08, 09, 10 or 11 (C.3).
- Use the same framing and scale for all six characters so the table looks even. The import script trims empty margins and fits each image into 512×512.

### 1.2 The six characters

Poker-table archetypes with a truco flavour. Each character's **base** prompt is the style guide plus the sheet below. Keep the sheet's colours and props in every variant.

| #   | id (folder)   | Archetype                                           | Character sheet                                                                                                                                                                                                                                                                                              |
| --- | ------------- | --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1   | `tiburon`     | The shark: calm, calculating, always a step ahead   | Slicked-back black hair with one loose strand, a toothpick in the corner of the mouth, a **smug half-smile** and half-lidded confident eyes. Charcoal waistcoat over a white shirt with rolled sleeves. Accent colour deep teal #1f6f78.                                                                     |
| 2   | `maniaca`     | The maniac: loose, aggressive, raises everything    | A big wild cloud of magenta hair held back by a yellow bandana, a **huge toothy grin**, sparkly wide eyes, a freckle across the nose. Oversized orange bomber jacket. A tiny lightning-bolt earring. Accent colour hot orange #e8642c.                                                                       |
| 3   | `roca`        | The rock: an old-timer who only plays premium hands | Older stickman with a black **boina** (flat beret), a thick white walrus moustache that does **not** cover the lips, bushy white eyebrows, a calm stern stare. Brown cardigan over a light shirt. A small mate gourd with a bombilla tucked against the chest beside the cards. Accent colour olive #6b7a3a. |
| 4   | `novato`      | The fish: nervous beginner, tells everywhere        | Light-blue knit **beanie** with a pom-pom, big round anxious eyes, a single sweat drop on the temple, a wobbly unsure smile. Baggy green hoodie with the strings uneven. Accent colour mint #5bbf9a.                                                                                                         |
| 5   | `calculadora` | The pro: counts every card, all maths               | Neat bob haircut in dark purple, **round thin-rimmed glasses with clear lenses** (eyes fully visible), a focused raised-corner smirk, headphones resting around the neck. Grey zip hoodie. A small pencil behind one ear. Accent colour violet #7a4f9a.                                                      |
| 6   | `fanfarron`   | The showman: loud, bluffs for fun                   | Wide-brimmed **gaucho hat** tipped back (it must not shade the eyes), a wide closed-mouth showman grin with one eyebrow cocked, a gold chain over a red neckerchief, a puffed-out chest. A white shirt with a dark leather vest. Accent colour gold #d19a2a.                                                 |

Base prompt template:

> [style guide] Character: [character sheet]. Neutral resting expression for this character, eyes open, mouth closed, both hands holding the cards in front of the chest.

**Note on resting faces:** each base must leave room for every seña to read as a _change_. The resting mouth should be closed and roughly neutral for the character. The eyes should be open and the eyebrows relaxed.

### 1.3 The 9 variants per character

Make each variant as an **image edit of that character's `base`** with an edit-capable model (for example Gemini image editing, gpt-image edit or FLUX Kontext). Start every edit with:

> Edit this image. Keep the character, pose, colours, outfit, props, framing, scale and transparent background **exactly identical**. Change only this:

and then add the line from the table. Keep señas **subtle but clearly readable at small size**: a natural table gesture, not a cartoon exaggeration.

**Right and left are the character's own (Anexo C.1).** The character faces the viewer, so **the character's right side is on the viewer's LEFT**. For the wink (02) and the mouth corners (03, 04), the prompts name **only the side of the image**. When the first batch said "the character's right" or "the viewer's left", the model put every one of them on the image's right. Check those three by eye: a wink on the image's right is seña 02 done wrong.

| File (`assets/avatars/approved/<id>/…`) | Seña (Anexo C.2)     | Edit line                                                                                                                                                                                                          |
| --------------------------------------- | -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `base.png`                              | none                 | (the base image itself)                                                                                                                                                                                            |
| `sena_01.png`                           | 01: as de espadas    | Raise **both eyebrows** clearly higher than in the base, eyes a little wider. **The mouth stays exactly as in the base, closed** (an open mouth is seña 07). The change must be obvious next to the base at 80 px. |
| `sena_02.png`                           | 02: as de bastos     | Close **only the eye on the LEFT side of the image** in a curved wink line. The eye on the right side of the image stays fully open.                                                                               |
| `sena_03.png`                           | 03: siete de espadas | Slide the mouth toward **the LEFT side of the image**: the mouth corner on the left side of the image moves outward and slightly up. The corner on the right side of the image stays put.                          |
| `sena_04.png`                           | 04: siete de oros    | Slide the mouth toward **the RIGHT side of the image**: the mouth corner on the right side of the image moves outward and slightly up. The corner on the left side of the image stays put.                         |
| `sena_05.png`                           | 05: cualquier tres   | **Gently bite the lower lip**: the upper teeth show a little, resting on the lower lip.                                                                                                                            |
| `sena_06.png`                           | 06: cualquier dos    | **Pucker the lips forward** into a small round kiss shape.                                                                                                                                                         |
| `sena_07.png`                           | 07: anchos falsos    | **Open the mouth slightly** into a small relaxed oval, as if about to speak.                                                                                                                                       |
| `sena_12.png`                           | 12: buen envido      | **Wrinkle the nose**: short crease lines on the bridge, the cheeks pushed up a little. The eyes stay open.                                                                                                         |

### 1.4 Review checklist (per character)

- [ ] All 9 files share the same outfit, colours, props, framing and scale. Flip through them quickly: only the seña should "move".
- [ ] Wink and mouth-corner señas are on the **correct side** (character's right = viewer's left).
- [ ] Each seña is visible when the image is shrunk to 80 px, but it is not a cartoon grimace.
- [ ] The face is never covered, and the background is transparent.

---

## Part 2: Cards

### 2.1 Deck style guide (paste at the top of every card prompt)

> A single playing card from a **Spanish 48-card deck (baraja española)**, front view, filling the whole image edge to edge, portrait **2:3 at 800×1200**. Warm cream paper (#fbf7ee) with a subtle printed texture, rounded corners, a thin dark outline. Hand-drawn illustration style with clean ink lines and flat colours with soft shading, matching a cosy cartoon card table. Suit colours: **oros** golden yellow #c9961a, **copas** red #b3261e, **espadas** blue #1f4e8c, **bastos** green #2e6b30, with gold #e0b43a accents. The card **number appears in the top-left and bottom-right corners** in a serif numeral. A thin decorative frame runs around the border, interrupted by the traditional **pinta gaps** for the suit: oros no gap, copas one gap, espadas two gaps, bastos three gaps. No text other than the numerals, no watermark.

### 2.2 Number cards 1–9

> [deck style guide] The card is the **[N] de [suit plural]**. Show **exactly [N]** [suit symbol] symbols arranged symmetrically in the traditional Spanish-deck layout. [extra]

Suit symbols:

- **oros**: a gold coin with a sun face/rays.
- **copas**: a red goblet/chalice.
- **espadas**: a blue straight sword, point up.
- **bastos**: a green wooden club/cudgel with knots.

Extras:

- **1 (as)**: one large ornate central symbol inside a laurel wreath. **1 de espadas** (the ancho de espadas, the top truco card) is the most ornate. **1 de bastos** is the second most ornate.
- **2–9**: plain pips, no wreath. Espadas and bastos crossed or interlaced in the traditional way where the layout calls for it.

**Count the pips on every card before saving.** Image models often draw the wrong number. Reroll any card whose count is off.

### 2.3 Figures: sota (10), caballo (11), rey (12)

Draw them in the same cartoon-ink style, as full-length figures (not mirrored halves, as in a Spanish deck). Each one holds or shows the suit symbol clearly:

- **10 sota**: a young page standing, holding the suit symbol.
- **11 caballo**: a rider on a horse, holding the suit symbol.
- **12 rey**: a crowned king standing with a cape, holding the suit symbol.

> [deck style guide] The card is the **[10/11/12] de [suit plural]**: [figure description], holding [suit symbol], dressed in [suit colour] and gold.

### 2.4 Comodines and dorso

- **`comodin-1.png`**: > [deck style guide, without the corner numerals] A **comodín** (joker) card: a grinning jester in a red and gold harlequin outfit, juggling the four suit symbols (coin, goblet, sword, club).
- **`comodin-2.png`**: > [same] A second, different **comodín**: a jester in a blue and green harlequin outfit, doing a handstand and balancing a goblet on one foot.
- **`dorso.png`**: > A playing-card **back**, portrait 2:3 at 800×1200, filling the whole image edge to edge, rounded corners. A repeating **dark oxblood (#8e1b17) and gold (#e0b43a) rhombus pattern** with small gold dots, a double gold frame, and a central cream oval medallion holding a small blue sword. It must be **symmetric under 180° rotation**, with no text.

### 2.5 File names (`assets/cards/…`)

| Files                                                                                                          | Count |
| -------------------------------------------------------------------------------------------------------------- | ----- |
| `<n>-<suit>.png` for n = 1…12 and suit = `espada`, `basto`, `oro`, `copa` (e.g. `1-espada.png`, `12-copa.png`) | 48    |
| `comodin-1.png`, `comodin-2.png`                                                                               | 2     |
| `dorso.png`                                                                                                    | 1     |

The suit in the file name is **singular** (`espada`, not `espadas`).

### 2.6 Review checklist

- [ ] The pip count matches the number on every 1–9 card.
- [ ] The corner numerals are correct and the suit colour and pinta gaps match the suit.
- [ ] All 51 cards share the same paper, frame and line style.
- [ ] The cards are readable at the table's size (about 96 px wide).
