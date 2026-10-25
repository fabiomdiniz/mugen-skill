#!/usr/bin/env python3
"""Scan a MUGEN 1.1b1 chars/ tree and report which characters' select-screen
CELL portraits (sprite 9000,0 in the MAIN SFF) are missing, tiny, or too big
for the cell. v2 SFFs are skipped (they carry their own 9000 sprites).

Usage: python scan_portraits.py [chars_dir] [cell_w] [cell_h]
Defaults: chars_dir=chars, cell=50x50. Tiny threshold: <20px either side.

Stdlib only (reads the SFF v1.01 linked list + PCX headers directly).
"""
import os, re, struct, sys

CHARS = sys.argv[1] if len(sys.argv) > 1 else "chars"
LIMIT_W = int(sys.argv[2]) if len(sys.argv) > 2 else 50
LIMIT_H = int(sys.argv[3]) if len(sys.argv) > 3 else 50
TINY = 20


def main_sff(folder):
    """Resolve the character's main SFF via the .def `sprite =` field
    (case-insensitive; handles SFFs in subdirs)."""
    d = os.path.join(CHARS, folder)
    defs = [f for f in os.listdir(d) if f.lower().endswith(".def")]
    deff = None
    for f in defs:
        if f.lower() == folder.lower() + ".def":
            deff = os.path.join(d, f)
            break
    if deff is None:
        for f in defs:
            if f.lower() not in ("ending.def", "intro.def"):
                deff = os.path.join(d, f)
                break
    if deff is None:
        return None
    content = open(deff, encoding="utf-8", errors="replace").read()
    m = re.search(r"(?mi)^\s*sprite\s*=\s*([^\r\n;]+)", content)
    if m:
        sff = os.path.normpath(os.path.join(d, m.group(1).strip().replace("\\", "/")))
        if os.path.exists(sff):
            return sff
    # fallback: first non-storyboard, non-portrait SFF in the folder
    sffs = sorted(f for f in os.listdir(d) if f.lower().endswith(".sff")
                  and not f.lower().endswith("_portrait.sff")
                  and not f.lower().startswith(("ending", "intro")))
    return os.path.join(d, sffs[0]) if sffs else None


def read_pcx_size(data, off):
    """PCX width/height from the data at off; None if not a PCX start."""
    if off + 12 > len(data) or data[off] != 0x0A:
        return None
    xmin, ymin = struct.unpack_from("<HH", data, off + 4)
    xmax, ymax = struct.unpack_from("<HH", data, off + 8)
    return (xmax - xmin + 1, ymax - ymin + 1)


def cell_portrait_size(sff_path):
    """Return (version, 9000_0_size_or_None) for the SFF. version: 'v1' | 'v2' | None."""
    data = open(sff_path, "rb").read()
    if data[:12] != b"ElecbyteSpr\x00":
        return None, None
    if data[15] == 2:
        return "v2", None
    if data[15] != 1:
        return None, None
    first = struct.unpack_from("<I", data, 24)[0]
    num_images = struct.unpack_from("<I", data, 20)[0]
    off = first
    count = 0
    p0 = None
    while off and off + 32 <= len(data) and count <= num_images:
        nxt = struct.unpack_from("<I", data, off)[0]
        length = struct.unpack_from("<I", data, off + 4)[0]
        g = struct.unpack_from("<H", data, off + 12)[0]
        img = struct.unpack_from("<H", data, off + 14)[0]
        if g == 9000 and img == 0 and length > 0:
            p0 = read_pcx_size(data, off + 32)
        count += 1
        off = nxt
        if off == 0:
            break
    return "v1", p0


def main():
    missing, tiny, big = [], [], []
    n_v1 = n_v2 = n_other = 0
    for folder in sorted(os.listdir(CHARS)):
        if not os.path.isdir(os.path.join(CHARS, folder)):
            continue
        sff = main_sff(folder)
        if not sff:
            n_other += 1
            continue
        ver, p0 = cell_portrait_size(sff)
        if ver == "v2":
            n_v2 += 1
            continue
        if ver != "v1":
            n_other += 1
            continue
        n_v1 += 1
        if p0 is None:
            missing.append(folder)
        elif p0[0] < TINY or p0[1] < TINY:
            tiny.append((folder, p0))
        elif p0[0] > LIMIT_W or p0[1] > LIMIT_H:
            big.append((folder, p0))

    print(f"v1.01: {n_v1}, v2: {n_v2}, other/no-sff: {n_other}")
    print(f"MISSING 9000,0 ({len(missing)}):")
    for f in missing:
        print(f"  {f}")
    print(f"TINY <{TINY}px 9000,0 ({len(tiny)}):")
    for f, p in tiny:
        print(f"  {f}: {p[0]}x{p[1]}")
    print(f"OVERSIZED >{LIMIT_W}x{LIMIT_H} 9000,0 ({len(big)}):")
    for f, p in big:
        print(f"  {f}: {p[0]}x{p[1]}")
    print(f"action: run scripts/fix_cell_portraits.py for every listed folder")


if __name__ == "__main__":
    main()
