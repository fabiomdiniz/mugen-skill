# mugen — agent skill for M.U.G.E.N 1.1b1 packs

A [Hermes](https://hermes-agent.nousresearch.com/docs) / Claude-compatible agent
skill for working with the **M.U.G.E.N 1.1b1** fighting-game engine: installing
characters and stages, porting/fixing screenpacks, rebuilding rosters, and
surgically fixing the two classic select-screen portrait bugs (overflowing cell
thumbnails and huge face previews on SFF v1.01 characters).

## Layout

```
skills/windows/mugen/
├── SKILL.md                         # main instructions (loaded on trigger)
├── references/
│   └── sff-v101-portraits.md        # SFF v1.01 binary format + portrait-append procedure
└── scripts/
    ├── scan_portraits.py            # list chars whose cell portrait is missing/tiny/oversized
    └── fix_cell_portraits.py        # append a proper 9000,0/9000,1 into a char's main SFF
```

The skill follows the standard `skills/<category>/<skill>/SKILL.md` layout (max
two levels under `skills/`), so it is discoverable by `npx skills add` /
skills.sh and by harnesses that scan a repo's `skills/` tree. Reference files
are loaded on demand (they cost nothing until a question needs them); the two
scripts are run, not loaded.

## Install

**Hermes** — clone and symlink, or let the skills CLI do it:

```bash
npx skills add https://github.com/fabiomdiniz/mugen-skill --global
```

**Manual** — place the `mugen/` directory (containing `SKILL.md`) under your
skills tree, e.g. `~/.agents/skills/mugen` (skills.sh) or
`.claude/skills/mugen/` (Claude Code / Claude Platform), keeping
`references/` and `scripts/` alongside it.

## What it covers

- Migrating a WinMUGEN pack into MUGEN 1.1b1 (the old engine crashes on Win7+)
- Installing characters/stages from `.rar`/`.zip`, including flat-wrapped and
  case-colliding archives
- Rebuilding `select.def` from the folders actually on disk (not the pack's
  stale roster)
- Porting/re-gridding screenpacks; the lifebar-cropping fix (localcoord mismatch)
- The select-screen **cell** vs **face** portrait system, and fixing SFF v1.01
  chars whose auto-generated portraits overflow the cell or face

## Notes

- Scripts assume Windows (git-bash/MSYS) — that's where MUGEN 1.1b1 runs.
- `scripts/fix_cell_portraits.py` defaults `MUGEN` to a local install path;
  edit the `MUGEN` constant at the top if your install lives elsewhere.
- See `references/sff-v101-portraits.md` for the SFF v1.01 binary format and the
  full append procedure before modifying the scripts.

## License

MIT
