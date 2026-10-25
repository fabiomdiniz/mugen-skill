---
name: mugen
description: "Use for M.U.G.E.N packs: install chars, port screenpacks."
version: 0.1.0
author: Hermes
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [MUGEN, Gaming, Emulation, Retro, Fighting-game, Screenpacks]
---

# MUGEN engine pack work

## When to Use
Installing characters/stages, migrating an old WinMUGEN pack, porting/fixing a screenpack (select screen, lifebars), rebuilding a `select.def` roster, or diagnosing a MUGEN crash on this Windows host.

## Core rule: migrate, don't fix the old engine
- Old **WinMUGEN** (pre-2006, `winmugen.exe`, `alleg40.dll` + DirectX 7) crashes on Win7+ with `0xc0000005` in `alleg40.dll`. Do NOT try to repair it — **move the content into MUGEN 1.1b1** (`mugen.exe`, 2013), which runs natively on Win11.
- 1.1b1 loads WinMUGEN-era chars/stages fine (log line: `Info: <char> loading in pre-1.0 compatible mode`).
- Confirm a real crash vs. a process-check false negative via the event log: `powershell.exe -NoProfile -Command 'Get-WinEvent -FilterHashtable @{LogName="Application"; Id=1000} -MaxEvents 30 | ? { $_.Message -like "*<exe>*" } | select -First 5 | fl TimeCreated,Message'`. A `0xc0000005` for the OLD exe = engine fault; the 1.1b1 `mugen.exe` should have none.

## Layout (1.1b1)
`chars/<folder>/<folder>.def` · `stages/*.def` · `data/mugen.cfg` (holds `motif = ...`) · `data/select.def` (roster) · `data/<motif>/` (screenpack files) · `font/` · `sound/`.

## Install characters from .rar/.zip archives
- Extract with 7-Zip (NOT on PATH — use the full path): `"/c/Program Files/7-Zip/7z.exe" x "arch.rar" -o"chars" -y`. `unzip` IS on PATH for .zip.
- Archives carry a top-level folder = the char folder; extract into `chars/` so it lands as `chars/<name>/`. Watch the `-o` target: it is relative to the cwd — point it at `mugen-1.1b1/chars`, not a stray `chars/` beside the MUGEN folder.
- Two archives differing only by case (`Silvio Santos` vs `SILVIO SANTOS`) COLLIDE on case-insensitive NTFS. If they are genuinely different chars, extract the second to a distinct folder (`chars/<name> MV/`) and reference its `.def` by explicit path in the roster.
- Some archives are FLAT — char files at the archive top level with no folder (e.g. "Madness Mario", "Leo Stronda", "ronaldo", "simba", many pre-2010 chars). Detect with `7z l -slt arch | grep 'Path = '`: the `.def` sits at top level, not `<folder>\.def`. Extract to a temp dir, wrap the top-level entries in a folder named after the `.def` basename (or the char), then move that folder into `chars/`.
- After installing a char, MOVE its archive into the sibling `chars done/` folder — the user files the consumed input archives there, not in `chars to install/`.

## Build select.def from the FOLDERS on disk (ground truth)
Mega-packs ship a `select.def` that lists only a fraction of the chars actually present, with broken entries. Enumerate `chars/*/` folders instead, resolve each one's `.def`, and write a fresh roster. Resolution per folder: `<folder>.def` (case-insensitive match) → bare folder name; else exactly one non-storyboard `.def` → `folder/that.def`; else skip. `ending.def`/`intro.def` are storyboards, not chars. A folder with a second `.def` (e.g. `zero.def` + `zerosvc.def`) uses the folder-matching one.
- Char names with SPACES are fine — the select.def char field is everything up to the first comma.
- Stage field: `random` (picks from `[ExtraStages]`) is the safe default when there's no curated per-char stage.
- `randomselect` on its own line adds a random-select tile. The user wants exactly ONE, at the very END of the roster.
- **MUGEN 1.1b1 has no empty-cell keyword in `select.def`.** A blank line, the word `empty`, and a lone `,` are all parsed as CHARACTER NAMES — each logs `Error reading character file: chars/<x>/<x>.def` (or `chars//.def`) and is skipped, so the grid fills contiguously with no gap. The `empty`/`,` empty-cell keyword exists only in LATER MUGEN builds (screenpacks like Legacy NoZ ship a `select.def` full of `empty` placeholders that silently fail on 1.1b1). To reserve a screenpack's big-portrait (face) areas, do NOT blank cells in select.def — narrow/reposition the grid instead (see Re-grid). A `;`-comment line is ignored (no cell).
- After a bulk install, report a COUNT plus a THEMATIC grouping of the chars (memes/real-life personalities, Chaves/El-Chavo universe, fighting-game/classic MUGEN, Disney/cartoons, anime, Mario/Nintendo, SpongeBob, Pokémon) — the user wants the summary grouped, not just a number.

## Port a screenpack (select screen) to 1.1b1
- Copy the old `data/` screenpack files into `data/<motif>/`: `system.def`, `system.sff`/`.snd`, `fight.def`/`.sff`/`.snd`, `fightfx.*`, `select.sff`, the BG/versus/options/gameover/credits files, and any bare-referenced fonts.
- Set `motif = data/<motif>/system.def` in `data/mugen.cfg`.
- Put `select.def` in BOTH `data/` and `data/<motif>/` (field resolution differs; cheap insurance).
- `spr`/`snd`/`fight` in system.def resolve relative to the motif dir; fonts are searched in order: motif/system dir → MUGEN root → `data/` → `font/`. Copy WinMUGEN `.fnt` fonts into `font/` so `font/xxx.fnt` refs resolve.
- Some screenpacks reference assets by MUGEN-ROOT-relative paths (e.g. `title.bgm = data/MENU.ogg` in `[Music]`), so they must be installed as the DEFAULT motif (`data/system.def`), NOT a sub-motif — dropping them in `data/<motif>/` breaks those refs. Grep `system.def` for `data/...` refs to tell which layout the pack expects.

## Lifebar cropping = coordinate-space mismatch (the classic bug)
WinMUGEN screenpacks use a **320×240** localcoord (no `localcoord` line = 320×240 default). The stock 1.1b1 lifebar is authored for **1280×720** (`p1.pos = 590,40`). Pointing a 320×240 screenpack at the stock `fight.def` puts the lifebar off-screen → "healthbar cropped". **Use the screenpack's own `fight.def`** (anchors like `p1.pos = 160,0`), not the stock one. The old lifebar is NOT what crashes the match — verify before swapping it out.

## Re-grid a select screen to fit N characters
Capacity = `rows × columns` in `[Select Info]` of `system.def`. Grid size in the motif's localcoord space: `width = columns×cell.size.x + (columns−1)×cell.spacing`, `height = rows×cell.size.y + (rows−1)×cell.spacing`. Center it with `pos = (localcoord.x−width)/2, (localcoord.y−height)/2`.
- The clean base for a large-portrait roster is the built-in **`big` motif** (`data/big/system.def`): `localcoord=1280,720` and it reuses `../mugen1/system.sff` + `../mugen1/fight.def`, so its localcoord MATCHES the stock lifebar — no cropping. 200 slots = `rows=10, columns=20` at `cell.size=35`, `cell.spacing=5`, centered `pos=242,162`.
- When you change `cell.size`, also rescale `cell.bg.scale`/`cell.random.scale` in proportion: the `big` motif's cell sprite (`cell.bg.spr=150,0`) is ~100px native and ships at `cell.size=50` with `scale=.5`, i.e. scale = cell.size/native_size. Leaving scale stale while shrinking the cell overflows the box.
- `wrapping = 1` lets the cursor wrap around the grid.
- To keep cells out from under a screenpack's big face/portrait panels (top-left/top-right), cut `columns` to the middle band and recenter `pos` so the grid sits BETWEEN the two face offsets (e.g. Legacy NoZ 24-col → `columns=12`, `pos` pushed right; then set `p1.cursor.startcell`/`p2.cursor.startcell` to the new first/last columns). This is the only reliable reserve on 1.1b1.
- A 320×240 screenpack cannot show 200 readable cells (its 8px cells are built for ~1000); re-grid a 1280×720 motif instead.
- Purpose-built large-roster screenpacks (228/235/400+ slots): Mugen Archive (`mugenarchive.com/forums/downloads.php?do=cat&id=117-screenpacks`, may need a free account) and OldGamer on Mugen Guild (`network.mugenguild.com/oldgamer/`, direct `.rar` links). Prefer 1.1b1-native 1280×720 packs.

## Verify by launching and reading mugen.log
`mugen.exe` (re)writes `mugen.log` in its own folder on every launch. Read it instead of guessing:
- `Initializing select screen...finding characters...OK` = roster parsed, no errors.
- `Character <x>.def loaded OK` = a char fully loaded; `Opening fight data file data/<motif>/fight.def...OK` = correct lifebar in use.
- `Error loading VictoryBG` is cosmetic (old screenpacks lack the 1.1 `[Victory Screen]` section); ignore it.
- **Quick-VS** tests a match headlessly: `./mugen.exe <p1> <p2> [-s <stage>]` (e.g. `./mugen.exe kfm kfm720 -s kfm`). Omit `-s` if unsure of a stage name; char names with spaces go in quotes.
- Confirm the process is actually running with `tasklist | grep -i mugen` — never `tasklist //FI` (see windows-terminal-ops).

## Pitfalls
- Double-slash `tasklist //FI` / `taskkill //F //IM` report a live process as dead — single slash only (`tasklist | grep`, `taskkill /F /IM mugen.exe`).
- A `.def` filename may not match its folder (e.g. folder `Silvio Santos MV` → `Silvio Santos.def`); always check the actual `.def` name before writing the roster.
- Old screenpacks' logo/intro storyboards can hang or crash the 1.1 engine (the "DJ-VAN" loader is a known point). Disable with `logo.storyboard =` (empty) / `intro.storyboard =` in system.def — they're just splash screens.
- Disable attract/demo mode (`[Demo Mode] enabled = 0`) when a large pack has flaky chars, so the title screen doesn't auto-play random matches and hit a broken one.
- Non-ASCII filenames (accents like `ç`) can mismatch between a stage/char `.def`'s internal `bgmusic = sound/...` reference (often CP1252) and the on-disk name (Unicode), so BGM silently fails. Normalize such filenames to ASCII and fix the `.def` reference to match. Stages' `bgmusic` paths point at the MUGEN-root `sound/` dir, NOT the stage folder — install `.mp3`s into `sound/`, and the `.def`/`.sff` into `stages/` flat.
- SFF **v1.01** chars (most pre-2010 WinMUGEN chars) have no 9000-series portrait sprites in their main SFF, so 1.1b1 auto-generates the select-screen portraits from the LARGEST sprite — often a huge full-body/effect frame (300–2000px) that overflows the CELL and the FACE. The `.def` `portrait = <sff>, <group>, <image>` field sets ONLY the BIG hover/selected portrait (9000,1); the CELL thumbnail is sprite 9000,0 **inside the character's own main SFF** and is drawn at NATIVE size — so a `portrait =` line (even pointing at a separate portrait SFF) can never fix cell overflow. Fix the cell by appending a ≤cell-size 9000,0 (and a 120×140 9000,1) sprite into the main SFF. First run `scripts/scan_portraits.py` to list exactly which v1.01 chars need it (9000,0 missing, tiny <20px, or bigger than cell.size — v2 SFFs are auto-skipped), then run `scripts/fix_cell_portraits.py <folder>...`; binary format and procedure in `references/sff-v101-portraits.md`. Narrowing the grid (see Re-grid) only stops the FACE covering cells — it does not shrink the cell thumbnails. Detect SFF version from the byte at offset 15 (after `ElecbyteSpr` + NUL + 3 reserved): `0x01`=v1.01, `0x02`=v2.00.
- Files extracted from `.rar`/`.zip` often carry the Windows READ-ONLY (and hidden) attribute → `PermissionError` when editing `.def`s. Run `attrib -R -H` over the extracted tree before patching files.
