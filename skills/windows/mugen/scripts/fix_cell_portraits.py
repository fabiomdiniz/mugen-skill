import os, re, struct, subprocess
from PIL import Image

MUGEN = r"C:\Users\fabio\Downloads\MUGEN\fabio-test-mugen-1_1b1\mugen-1.1b1"
CHARS = os.path.join(MUGEN, "chars")
SCRATCH = r"C:\Users\fabio\AppData\Local\hermes\cache\scratch\cellfix_work"
SFF2PNG = os.path.join(MUGEN, "sff2png.exe")

SMALL = (50, 50)       # cell portrait canvas
FIT = (46, 46)         # content fit box (margin so art doesn't touch cell edges)
LARGE = (120, 140)
LARGE_FIT = (112, 132)


def make_pcx8(rgba_img, size):
    """8-bit PCX from an RGBA image. alpha<128 -> palette index 0 (transparent
    in MUGEN v1.01); the rest -> indices 1-255."""
    W, H = size
    px = rgba_img.load()
    q = rgba_img.convert("RGB").quantize(255)
    qpal = q.getpalette()[:255 * 3]
    qidx = list(q.getdata())
    pal = [255, 0, 255] + qpal  # index 0 = magenta (transparent)
    idx = []
    for i in range(H):
        for j in range(W):
            idx.append(0 if px[j, i][3] < 128 else qidx[i * W + j] + 1)
    bpl = W if W % 2 == 0 else W + 1
    hdr = bytearray(128)
    hdr[0] = 0x0A; hdr[1] = 5; hdr[2] = 1; hdr[3] = 8
    struct.pack_into('<H', hdr, 4, 0)
    struct.pack_into('<H', hdr, 6, 0)
    struct.pack_into('<H', hdr, 8, W - 1)
    struct.pack_into('<H', hdr, 10, H - 1)
    struct.pack_into('<H', hdr, 12, 300)
    struct.pack_into('<H', hdr, 14, 300)
    hdr[65] = 1
    struct.pack_into('<H', hdr, 66, bpl)
    struct.pack_into('<H', hdr, 68, 1)
    out = bytearray()
    for y in range(H):
        row = bytearray(idx[y * W:(y + 1) * W])
        if len(row) < bpl:
            row += b"\x00" * (bpl - len(row))
        i = 0; n = len(row)
        while i < n:
            b = row[i]; run = 1
            while i + run < n and run < 63 and row[i + run] == b:
                run += 1
            if run > 1 or (b & 0xC0) == 0xC0:
                out.append(0xC0 | run); out.append(b); i += run
            else:
                out.append(b); i += 1
    out.append(0x0C)
    out += bytes(pal[:768])
    return bytes(hdr) + bytes(out)


def append_v101_sprite(sff_path, group, image, pcx_bytes, axis=(0, 0)):
    """Append a sprite subfile to a v1.01 SFF linked list; rename any old
    (group,image) duplicate to 8999 so it can't shadow the new one."""
    with open(sff_path, "rb") as fh:
        d = bytearray(fh.read())
    if d[0:12] != b"ElecbyteSpr\x00" or d[15] != 1:
        return False, "not v1.01"
    num_groups = struct.unpack_from('<I', d, 16)[0]
    num_images = struct.unpack_from('<I', d, 20)[0]
    first = struct.unpack_from('<I', d, 24)[0]
    subhdr = 32  # NEVER read offset 28 (unreliable, some SFFs have 512)
    off = first; last_off = None; old_offs = []; groups = set(); count = 0
    while off and off + subhdr <= len(d) and count <= num_images:
        nxt = struct.unpack_from('<I', d, off)[0]
        g = struct.unpack_from('<H', d, off + 12)[0]
        img = struct.unpack_from('<H', d, off + 14)[0]
        groups.add(g)
        if g == group and img == image:
            old_offs.append(off)
        if nxt == 0:
            last_off = off
        count += 1
        off = nxt
    new_off = len(d)
    hdr = bytearray(32)
    struct.pack_into('<I', hdr, 0, 0)
    struct.pack_into('<I', hdr, 4, len(pcx_bytes))
    struct.pack_into('<hh', hdr, 8, axis[0], axis[1])
    struct.pack_into('<HH', hdr, 12, group, image)
    struct.pack_into('<H', hdr, 16, 0)
    hdr[18] = 0  # own palette
    d += hdr + pcx_bytes
    if last_off is not None:
        struct.pack_into('<I', d, last_off, new_off)
    for ooff in old_offs:
        struct.pack_into('<H', d, ooff + 12, 8999)
        groups.add(8999)
    groups.add(group)
    struct.pack_into('<I', d, 20, num_images + 1)
    struct.pack_into('<I', d, 16, len(groups))
    with open(sff_path, "wb") as fh:
        fh.write(bytes(d))
    return True, f"appended {group},{image}"


def find_def(folder):
    d = os.path.join(CHARS, folder)
    for f in os.listdir(d):
        if f.lower() == folder.lower() + ".def":
            return os.path.join(d, f)
    defs = [f for f in os.listdir(d) if f.lower().endswith(".def")
            and f.lower() not in ("ending.def", "intro.def")]
    return os.path.join(d, defs[0]) if len(defs) == 1 else None


def main_sff(folder):
    d = os.path.join(CHARS, folder)
    deff = find_def(folder)
    if deff:
        content = open(deff, encoding="utf-8", errors="replace").read()
        m = re.search(r"(?mi)^\s*sprite\s*=\s*([^\r\n;]+)", content)
        if m:
            sff = os.path.normpath(os.path.join(d, m.group(1).strip().replace("\\", "/")))
            if os.path.exists(sff):
                return sff
    sffs = sorted(f for f in os.listdir(d) if f.lower().endswith(".sff")
                  and not f.lower().endswith("_portrait.sff")
                  and not f.lower().startswith(("ending", "intro")))
    return os.path.join(d, sffs[0]) if sffs else None


def fix_char(folder):
    deff = find_def(folder)
    sfff = main_sff(folder)
    if not deff or not sfff:
        print(f"[skip] {folder}: no def/sff")
        return False
    with open(sfff, "rb") as fh:
        head = fh.read(16)
    if head[:12] != b"ElecbyteSpr\x00" or head[15] != 1:
        print(f"[skip] {folder}: not v1.01")
        return False
    workdir = os.path.join(SCRATCH, folder)
    os.makedirs(workdir, exist_ok=True)
    subprocess.run([SFF2PNG, sfff, os.path.join(workdir, "spr")],
                   cwd=workdir, capture_output=True)
    pngs = [os.path.join(workdir, f) for f in os.listdir(workdir)
            if f.lower().startswith("spr") and f.lower().endswith(".png")]
    if not pngs:
        print(f"[fail] {folder}: no sprites")
        return False
    src = max(pngs, key=lambda p: Image.open(p).size[0] * Image.open(p).size[1])
    with Image.open(src) as src_im:
        pal = src_im.getpalette()
        bg = tuple(pal[0:3]) if pal else None
        rgba = src_im.convert("RGBA")
        if bg:  # strip the source sprite's background (its palette index 0)
            px = rgba.load()
            for y in range(rgba.height):
                for x in range(rgba.width):
                    r, g, b, a = px[x, y]
                    if (r, g, b) == bg and a > 0:
                        px[x, y] = (r, g, b, 0)

        def fit(im, W, H, FW, FH):
            r = min(FW / im.width, FH / im.height)
            nw, nh = max(1, round(im.width * r)), max(1, round(im.height * r))
            small = im.resize((nw, nh), Image.LANCZOS)
            canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            canvas.paste(small, ((W - nw) // 2, (H - nh) // 2))
            return canvas

        small_img = fit(rgba, SMALL[0], SMALL[1], FIT[0], FIT[1])
        large_img = fit(rgba, LARGE[0], LARGE[1], LARGE_FIT[0], LARGE_FIT[1])
    ok1, m1 = append_v101_sprite(sfff, 9000, 0, make_pcx8(small_img, SMALL))
    ok2, m2 = append_v101_sprite(sfff, 9000, 1, make_pcx8(large_img, LARGE))
    if not ok1 or not ok2:
        print(f"[fail] {folder}: {m1} / {m2}")
        return False
    content = open(deff, encoding="utf-8", errors="replace").read()
    if re.search(r"(?m)^portrait\s*=", content):
        content = re.sub(r"(?m)^portrait\s*=.*(?:\r?\n|$)", "", content)
        open(deff, "w", encoding="utf-8").write(content)
    print(f"[ok] {folder}")
    return True


if __name__ == "__main__":
    import sys
    for t in sys.argv[1:] or ["BARRIGA"]:
        try:
            fix_char(t)
        except Exception as e:
            print(f"[error] {t}: {e!r}")
