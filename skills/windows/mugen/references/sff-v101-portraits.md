# SFF v1.01 select-screen portraits: mechanism, binary format, overflow fix

## How 1.1b1 picks the select-screen portraits
- CELL thumbnail = sprite 9000,0 **in the character's main SFF** (the file named by `sprite =` in the `.def`), drawn at NATIVE size — a 460×595 portrait spills over a 50×50 cell. There is no cell-scaling setting in `[Select Info]`.
- FACE (big hover/selected preview) = sprite 9000,1 (system.def `p1.face.spr = 9000,1`), scaled by `p1.face.scale`.
- The `.def` `portrait = <sff>, <g>, <i>` field sets ONLY the big portrait (9000,1). It never changes the cell (MUGEN FAQ: "Except for the big portrait (9000,1), the answer is no"). A separate `*_portrait.sff` referenced via `portrait =` therefore fixes the FACE only.
- A v1.01 SFF missing 9000,0/9000,1 → MUGEN auto-generates both from the LARGEST sprite in that SFF → overflow of cell and face. The only real fix for the CELL is writing a small 9000,0 (and 9000,1) sprite INTO the main SFF. Grid narrowing (SKILL.md Re-grid) only keeps the face from covering cells.
- Standard sizes: 9000,0 = 25×25 or 50×50 (≤ cell.size), 9000,1 = 120×140, axis (0,0) (matches kfm).

## SFF v1.01 binary format (verified by parsing)
Header, 512 bytes:
- 0–11 `ElecbyteSpr\0` signature · 12–15 version (byte 15: 1 = v1.01, 2 = v2.00) · 16 num_groups u32 · 20 num_images u32 · 24 offset of first subfile u32 · 28 a field that *claims* to be the subheader size but is UNRELIABLE (some SFFs store 512 there; real subfile headers are ALWAYS 32 bytes — never trust offset 28) · 32 palette type (1 = shared, 0 = individual).

Subfile = 32-byte header + PCX data, chained as a linked list (NOT contiguous):
- +0 next subfile offset u32 (0 = last) · +4 data length u32 (excluding header) · +8 axis x i16 · +10 axis y i16 · +12 group u16 · +14 image u16 · +16 linked-copy index u16 · +18 palette flag u8 (1 = reuse previous sprite's palette, 0 = own 768-byte palette at the end of the PCX).
- Walk: start at the header's first-subfile offset, follow the next pointers until 0.
- The FIRST subfile in the list is 9000,0 when the SFF already has portraits — sff2png numbers sprites sequentially in linked-list order, so `spr000.png` may be 9000,0, not group 0,0. Never assume the first sprite is the idle pose.

## Portrait source: strip the source sprite's background FIRST
- The source sprite (usually the SFF's largest) is extracted by sff2png with its own palette applied; its palette index 0 = the char's transparent/background colour (commonly MAGENTA 255,0,255, sometimes black). If you scale that sprite as-is, the background colour becomes an opaque box in the portrait ("character with a magenta/black border overflowing the cell").
- Strip it: read the extracted PNG's `getpalette()[0:3]`, then in an RGBA copy set every pixel equal to that colour to alpha 0. THEN fit/scale on a transparent canvas.
- Transparency convention in the generated portrait: palette index 0 IS transparent in MUGEN v1.01. Build the final palette explicitly as `[magenta] + quantize(rgb,255)` palette, map every alpha<128 pixel to index 0 and every other pixel to (quantized index + 1). Do NOT rely on `quantize(256)` luck — it can put a blended edge colour at index 0, leaving the real background opaque.
- Give the fitted content a small margin (fit within cell−4 px, e.g. 46×46 on a 50×50 canvas) so the art doesn't sit flush against the cell edges (read as "overflowing a bit").
- Tiny existing 9000,0 sprites (10×10) render as "no portrait at all" — the same append (rename old to 8999, append a fresh 50×50) fixes them. Scan for 9000,0 < 20px or missing across all v1.01 main SFFs; v2 SFFs (byte 15 = 2) already carry their own 9000 sprites and must be skipped in that scan.

## Appending a portrait sprite to a v1.01 SFF
1. Generate the portrait as 8-bit indexed PNG (PIL: resize to fit the target box, `quantize(256)`).
2. Build the PCX bytes: 128-byte header (0x0A, version 5, RLE=1, 8bpp, xmin/ymin 0, xmax/ymax w−1/h−1, planes=1, bytes-per-line = width rounded up to EVEN, palette-info=1) + per-scanline RLE (runs capped at 63; a byte with top-2-bits set MUST be encoded as a run, even length 1) + `0x0C` marker + 768-byte palette (PIL `getpalette()`).
3. Append the 32-byte subfile header + PCX at EOF (new subfile's next = 0); set the CURRENT last subfile's next pointer to the new offset; bump header num_images (+1 per sprite) and num_groups (recompute distinct groups, counting renames).
4. If an old 9000,0/9000,1 already exists, rewrite its group to 8999 in place (u16 at subfile+12) so it cannot shadow the new sprite — duplicate (group,image) resolution is unspecified.
5. Verify: walk the list and confirm walked count == header num_images (a shortfall means an orphaned subfile = corruption); re-extract with sff2png (should yield the original count + the new sprites, new 9000,0 = the target size); quick-VS the char and require `Character <x>.def loaded OK`; re-run `scripts/scan_portraits.py` and confirm the char is no longer listed.
`scripts/fix_cell_portraits.py <folder>...` performs steps 1–5 for a list of char folders (takes the main SFF from the `.def` `sprite =` field, so subdir SFFs are handled).

## Pitfalls
- Using the header field at offset 28 as the subheader size CORRUPTS the SFF: the bounds check `off + size <= filelen` then stops the linked-list walk one subfile early whenever the last subfile's PCX < size−32 bytes, so the append orphans the true last subfile and the char fails to load. ALWAYS hardcode 32.
- A corrupted-by-append SFF is easiest to restore by copying the original SFF back from the older sibling pack (same chars) and re-running the append correctly — do not hand-repair the linked list.
- sprmake2 (only needed for separate portrait SFFs, which fix the FACE via `portrait =`): its `[Sprite]` lines (`group, image, filename, x, y`) break when the image path contains SPACES ("Sprite: Too few arguments") — put the `.def`, PNGs and `.act` in one workdir and reference bare filenames; pass the output via `-o` (one argv element, spaces fine). Its `[Pal]` section wants an `.act` (768-byte RGB), not a PNG.
- `glob.glob` treats `[ ]` in a folder name as a character class and silently returns nothing — use `os.listdir` + filter for such paths.
- Char `.def` files may write the files section as `Sprite =x.sff` (capital, no spaces) — match with `(?mi)^\s*sprite\s*=\s*([^\r\n;]+)`. A capture like `[^;]+` spans newlines and swallows the rest of the file.
- The face overflow and the cell overflow are TWO different bugs with two different fixes (grid vs SFF append) — a user reporting "portraits still overflowing" after a face fix is now talking about the cell.