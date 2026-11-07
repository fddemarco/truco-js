#!/usr/bin/env bash
# The mirrored señas in assets/avatars/approved/, as made by `tools/art/avatars.py mirror`.
# Image models can't reliably put a seña on the requested side, so the 03s are built from the
# approved 04s and the 02s from winks on the wrong eye. Boxes are in the 512 frame. Rerun a line
# to remake a seña, check candidates/<id>/<seña>-mirrored-review.png, then move
# candidates/<id>/<seña>-mirrored.png to approved/<id>/<seña>.png.
#
# Picking boxes:
# - Mouth only, when the eyes are symmetric (tiburon 03).
# - Brows, eyes and mouth together, when one brow is raised: otherwise the mirrored mouth corner
#   lands on the other eye. Stay below hair, hats and bandanas so they aren't flipped.
# - --exact with one box per eye when an asymmetric detail crosses an eye (tiburon's hair strand),
#   and --erase for the stroke the old expression leaves behind.
set -euo pipefail
cd "$(dirname "$0")/../.."
mirror() { uv run tools/art/avatars.py mirror "$@"; }
A=assets/avatars/approved
F=assets/avatars/failed

# 03 from the approved 04
mirror tiburon "$A/tiburon/sena_04.png" sena_03 --box 200,290,370,385
mirror maniaca "$A/maniaca/sena_04.png" sena_03 --box 140,203,370,362
mirror novato "$A/novato/sena_04.png" sena_03 --box 150,197,365,330
mirror fanfarron "$A/fanfarron/sena_04.png" sena_03 --box 130,200,380,372

# 02 from the first batch's winks on the character's left eye (cell 2 of each gallery)
mirror tiburon "$F/tiburon/cell2-sena_02.png" sena_02 --exact \
  --box 160,252,245,306 --box 287,238,378,306 --erase 128,256,156,296
mirror maniaca "$F/maniaca/cell2-sena_02.png" sena_02 --box 140,203,370,362
mirror roca "$F/roca/cell2-sena_02.png" sena_02 --box 120,168,400,262
mirror novato "$F/novato/cell2-sena_02.png" sena_02 --box 150,197,365,330
mirror fanfarron "$F/fanfarron/cell2-sena_02.png" sena_02 --box 130,200,380,372
