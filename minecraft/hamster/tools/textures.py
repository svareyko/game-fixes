#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Texture generator for the hamster, plus a preview of the model.

    python tools/textures.py write      write the PNG files into resources/
    python tools/textures.py preview    render a picture to check by eye

IMPORTANT: the BOXES layout here has to match HamsterModel.createBodyLayer() in
src/hamster/client/HamsterModel.java - the same texOffs offsets and the same box
sizes. Change one - change the other too, or the texture slides across the faces.
The match is checked by the write command: it compares BOXES with the .java file
and refuses to work when they differ.

UV layout of a box (w,h,d) at offset (u,v) - exactly as the game does it:
    down   (u+d+w,   v,     w, d)      up     (u+d,     v,     w, d)
    north  (u+d,     v+d,   w, h)      south  (u+2d+w,  v+d,   w, h)
    west   (u,       v+d,   d, h)      east   (u+d+w,   v+d,   d, h)
"""

import re
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError:
    sys.exit("Pillow is required: python -m pip install pillow")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "resources" / "assets" / "hamster" / "textures"
JAVA_MODEL = ROOT / "src" / "hamster" / "client" / "HamsterModel.java"

TEX_W, TEX_H = 64, 32

# name: (uv, (w,h,d), (x0,y0,z0)) - model units, y points UP from the ground.
# Java has the same geometry with the Y axis pointing down: mc_y = -(y0 + h).
BOXES = [
    ("body",      (0, 0),   (7, 5, 7), (-3.5, 1.0, -1.0)),
    ("head",      (28, 0),  (6, 5, 5), (-3.0, 1.5, -6.0)),
    ("snout",     (50, 0),  (3, 2, 1), (-1.5, 2.0, -7.0)),
    ("ear_left",  (50, 4),  (2, 2, 1), (-2.5, 6.0, -4.6)),
    ("ear_right", (50, 4),  (2, 2, 1), (0.5, 6.0, -4.6)),
    ("leg_fl",    (0, 13),  (2, 1, 2), (-3.5, 0.0, -1.0)),
    ("leg_fr",    (0, 13),  (2, 1, 2), (1.5, 0.0, -1.0)),
    ("leg_bl",    (0, 13),  (2, 1, 2), (-3.5, 0.0, 4.0)),
    ("leg_br",    (0, 13),  (2, 1, 2), (1.5, 0.0, 4.0)),
    ("tail",      (10, 13), (1, 1, 1), (-0.5, 3.5, 6.0)),
]

PALETTES = {
    "golden": dict(fur=(216, 160, 94),  dark=(188, 132, 68),  belly=(246, 232, 205),
                   ear=(200, 134, 130), nose=(198, 120, 118), eye=(38, 28, 22), band=None),
    "grey":   dict(fur=(158, 154, 150), dark=(128, 124, 120), belly=(240, 238, 234),
                   ear=(188, 152, 150), nose=(176, 128, 126), eye=(38, 28, 22), band=None),
    "white":  dict(fur=(242, 240, 235), dark=(214, 210, 202), belly=(252, 251, 248),
                   ear=(226, 176, 174), nose=(212, 136, 134), eye=(152, 42, 42), band=None),
    "panda":  dict(fur=(246, 244, 240), dark=(58, 56, 54),    belly=(252, 251, 248),
                   ear=(58, 56, 54),    nose=(58, 56, 54),    eye=(30, 26, 22), band=(58, 56, 54)),
    "black":  dict(fur=(62, 58, 56),    dark=(42, 39, 38),    belly=(150, 142, 136),
                   ear=(120, 88, 88),   nose=(140, 96, 94),   eye=(232, 214, 190), band=None),
}


def rects(uv, size):
    u, v = uv
    w, h, d = size
    return {
        "down":  (u + d + w, v, w, d),
        "up":    (u + d, v, w, d),
        "north": (u + d, v + d, w, h),
        "south": (u + 2 * d + w, v + d, w, h),
        "west":  (u, v + d, d, h),
        "east":  (u + d + w, v + d, d, h),
    }


def draw(palette):
    """Whatever is not painted stays transparent: the base render type of entity
    models in 26.2 is RenderTypes.entityCutout, and it discards such pixels."""
    p = PALETTES[palette]
    im = Image.new("RGBA", (TEX_W, TEX_H), (0, 0, 0, 0))
    px = im.load()

    def fill(rect, colour):
        u, v, w, h = [int(t) for t in rect]
        for y in range(v, v + h):
            for x in range(u, u + w):
                px[x, y] = colour + (255,)

    for name, uv, size, _pos in BOXES:
        r = rects(uv, size)
        for face in r:
            fill(r[face], p["fur"])

        if name == "body":
            fill(r["down"], p["belly"])
            for side in ("west", "east"):
                u, v, w, h = [int(t) for t in r[side]]
                fill((u, v + h - 2, w, 2), p["belly"])
            if p["band"]:
                u, v, w, h = [int(t) for t in r["up"]]
                fill((u, v + 2, w, 3), p["band"])
                for side in ("west", "east"):
                    u, v, w, h = [int(t) for t in r[side]]
                    fill((u + 2, v, 3, h - 2), p["band"])

        elif name == "head":
            u, v, w, h = [int(t) for t in r["north"]]
            fill((u + 1, v + h - 2, w - 2, 2), p["belly"])
            for ex in (u + 1, u + w - 2):
                px[ex, v + 1] = p["eye"] + (255,)
                px[ex, v + 2] = p["eye"] + (255,)
            for side in ("west", "east"):
                u, v, w, h = [int(t) for t in r[side]]
                fill((u + 1, v + h - 2, w - 2, 2), p["belly"])

        elif name == "snout":
            fill(r["north"], p["belly"])
            u, v, w, h = [int(t) for t in r["north"]]
            px[u + w // 2, v] = p["nose"] + (255,)

        elif name.startswith("ear"):
            fill(r["north"], p["ear"])
            fill(r["up"], p["dark"])

        elif name.startswith("leg"):
            fill(r["down"], p["belly"])

    return im


def spawn_egg(palette="golden"):
    """The 16x16 spawn egg: a shape of its own, the vanilla texture is not touched."""
    p = PALETTES[palette]
    im = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([4, 1, 11, 14], fill=p["fur"] + (255,), outline=p["dark"] + (255,))
    d.ellipse([5, 3, 10, 13], fill=p["fur"] + (255,))
    for x, y in ((6, 5), (9, 7), (7, 9), (9, 11), (6, 12)):
        im.putpixel((x, y), p["dark"] + (255,))
    for x, y in ((7, 4), (8, 4)):
        im.putpixel((x, y), p["belly"] + (255,))
    return im



# --- the wheel -------------------------------------------------------------
# The UV layout of the rim has to match HamsterWheelModel.createLayer():
#   tread segment (5,2,5) -> texOffs(0,0),  spoke (1,6,1) -> texOffs(22,0)
WHEEL_BOXES = [
    ("segment", (0, 0), (5, 2, 5)),
    ("spoke",   (22, 0), (1, 6, 1)),
]
WHEEL_TEX = (32, 16)
WHEEL_COLOURS = dict(
    tread=(176, 133, 82),        # wood of the tread
    tread_lo=(138, 100, 58),     # shadow between the planks
    tread_hi=(206, 164, 112),    # highlight on a plank
    rim=(120, 86, 50),           # dark edging of the rim
    rivet=(198, 198, 206),       # rivet
    spoke=(128, 128, 138),       # metal of the spoke
    spoke_hi=(168, 168, 178),
    spoke_lo=(92, 92, 100),
    frame=(152, 112, 68),
    frame_lo=(112, 80, 46),
    frame_hi=(178, 138, 92),
    metal=(138, 138, 146),
    metal_hi=(176, 176, 184),
)


def draw_wheel():
    """Texture of the spinning rim.

    A face of the tread is only 5x5 pixels, as many as an ordinary 16x16 block
    has for that area. So the detail comes from pixel art, not from resolution:
    cross planks with a shadow and a highlight on the running track, a dark
    edging and rivets on the side faces, facets on the spoke.
    """
    c = WHEEL_COLOURS
    im = Image.new("RGBA", WHEEL_TEX, (0, 0, 0, 0))
    px = im.load()

    def fill(rect, colour):
        u, v, w, h = [int(t) for t in rect]
        for y in range(v, v + h):
            for x in range(u, u + w):
                px[x, y] = colour + (255,)

    def dot(x, y, colour):
        px[int(x), int(y)] = colour + (255,)

    seg = rects((0, 0), (5, 2, 5))
    # The running track and the outer edging: cross planks.
    for face in ("up", "down"):
        u, v, w, h = [int(t) for t in seg[face]]
        fill(seg[face], c["tread"])
        for row in range(h):
            if row % 2 == 1:
                fill((u, v + row, w, 1), c["tread_lo"])
            elif row == 0 or row == h - 1:
                fill((u, v + row, w, 1), c["rim"])
        for x in range(u, u + w, 2):
            dot(x, v + 2, c["tread_hi"])

    # Side faces of the rim: what is seen from the front. Edging plus rivets at the ends.
    for face in ("north", "south"):
        u, v, w, h = [int(t) for t in seg[face]]
        fill(seg[face], c["tread"])
        fill((u, v, w, 1), c["rim"])
        dot(u, v + 1, c["rivet"])
        dot(u + w - 1, v + 1, c["rivet"])
        dot(u + w // 2, v + 1, c["tread_hi"])

    # The end faces where segments meet: dark, they are hardly visible.
    for face in ("west", "east"):
        fill(seg[face], c["rim"])

    spoke = rects((22, 0), (1, 6, 1))
    for face in spoke:
        fill(spoke[face], c["spoke"])
    for face in ("north", "west"):
        u, v, w, h = [int(t) for t in spoke[face]]
        fill((u, v, w, 1), c["spoke_hi"])
        fill((u, v + h - 1, w, 1), c["spoke_lo"])
    return im


def draw_wheel_frame():
    """The 16x16 texture of the static frame: a board with grain, an axle and nails."""
    c = WHEEL_COLOURS
    im = Image.new("RGBA", (16, 16), c["frame"] + (255,))
    px = im.load()

    for y in range(16):
        for x in range(16):
            if y in (0, 15):
                px[x, y] = c["frame_lo"] + (255,)
            elif (x * 5 + y * 3) % 11 == 0:
                px[x, y] = c["frame_lo"] + (255,)
            elif (x * 7 + y) % 13 == 0:
                px[x, y] = c["frame_hi"] + (255,)

    for x in range(16):                       # metal strip for the axle
        px[x, 7] = c["metal"] + (255,)
        px[x, 8] = c["metal_hi"] + (255,) if x % 4 == 1 else c["metal"] + (255,)
    for x, y in ((1, 1), (14, 1), (1, 14), (14, 14)):   # nails in the corners
        px[x, y] = c["rivet"] + (255,)
    return im


def draw_wheel_item():
    """The 16x16 wheel icon - brown tones only, no metal.

    Deliberately dark and without grey: a light icon with metal spokes stood out
    in an inventory where almost everything is wood and stone.
    """
    dark = (58, 38, 22)       # almost black rim
    wood = (104, 68, 38)      # the main wood
    wood_hi = (132, 90, 52)   # highlight of the tread
    spoke = (82, 54, 30)      # spokes of the same wood, only darker
    hub = (140, 98, 58)       # hub

    im = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([0, 0, 15, 15], outline=dark + (255,), width=1)
    d.ellipse([1, 1, 14, 14], outline=wood + (255,), width=2)
    d.ellipse([3, 3, 12, 12], outline=dark + (255,))
    for x, y in ((8, 1), (8, 14), (1, 8), (14, 8),
                 (3, 3), (12, 3), (3, 12), (12, 12)):
        im.putpixel((x, y), wood_hi + (255,))
    for a, b in (((8, 4), (8, 11)), ((4, 8), (11, 8)),
                 ((5, 5), (10, 10)), ((10, 5), (5, 10))):
        d.line([a, b], fill=spoke + (255,))
    d.rectangle([7, 7, 8, 8], fill=hub + (255,))
    return im


def draw_hamster_item(palette="golden"):
    """The 16x16 icon of a hamster in the pocket: a curled-up little animal."""
    p = PALETTES[palette]
    im = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([2, 5, 13, 14], fill=p["fur"] + (255,), outline=p["dark"] + (255,))
    d.ellipse([4, 9, 11, 14], fill=p["belly"] + (255,))     # belly
    d.ellipse([8, 3, 14, 9], fill=p["fur"] + (255,), outline=p["dark"] + (255,))   # head
    d.rectangle([9, 2, 10, 3], fill=p["ear"] + (255,))      # ears
    d.rectangle([12, 2, 13, 3], fill=p["ear"] + (255,))
    im.putpixel((11, 6), p["eye"] + (255,))                 # eye
    im.putpixel((14, 7), p["nose"] + (255,))                # nose
    for x, y in ((3, 11), (2, 9)):                          # a stub of a tail
        im.putpixel((x, y), p["dark"] + (255,))
    return im


def check_wheel_matches():
    """The same comparison as for the hamster, but for the model of the rim."""
    java = ROOT / "src" / "hamster" / "client" / "HamsterWheelModel.java"
    if not java.is_file():
        return ["missing %s" % java]
    text = java.read_text(encoding="utf-8")
    problems = []
    for name, uv, (w, h, d) in WHEEL_BOXES:
        pattern = r"texOffs\(%d,\s*%d\)[\s\S]{0,120}?addBox\([^)]*?,\s*%d,\s*%d,\s*%d\)" % (
            uv[0], uv[1], w, h, d)
        if not re.search(pattern, text):
            problems.append("%s: texOffs(%d,%d) of size %dx%dx%d not found in HamsterWheelModel.java"
                            % (name, uv[0], uv[1], w, h, d))
    return problems


def check_java_matches():
    """Compares BOXES with the texOffs/addBox calls written in HamsterModel.java.

    Same idea as the disassembler check in build.py: a mismatch between the
    texture generator and the model does not crash the game, it quietly draws
    the hamster inside out. Better a failed build than guesswork in the game.
    """
    if not JAVA_MODEL.is_file():
        return ["missing %s" % JAVA_MODEL]
    text = JAVA_MODEL.read_text(encoding="utf-8")
    found = set()
    for u, v, x, y, z, w, h, dd in re.findall(
            r"texOffs\((\d+),\s*(\d+)\)\.addBox\("
            r"(-?[\d.]+)F,\s*(-?[\d.]+)F,\s*(-?[\d.]+)F,\s*(\d+),\s*(\d+),\s*(\d+)\)", text):
        found.add((int(u), int(v), float(x), float(y), float(z), int(w), int(h), int(dd)))

    problems = []
    for name, uv, (w, h, dd), (x0, y0, z0) in BOXES:
        # Java writes the geometry relative to the pivot of the part; only what does
        # not depend on the pivot is compared: the UV offset and the size of the box.
        same = [f for f in found if f[0] == uv[0] and f[1] == uv[1]
                and f[5] == w and f[6] == h and f[7] == dd]
        if not same:
            problems.append("%s: texOffs(%d,%d) of size %dx%dx%d not found in HamsterModel.java"
                            % (name, uv[0], uv[1], w, h, dd))
    return problems


def cmd_write():
    problems = check_java_matches() + check_wheel_matches()
    if problems:
        for p in problems:
            print("    - " + p)
        sys.exit("ERROR: the textures no longer match the model in HamsterModel.java")
    (OUT / "entity" / "hamster").mkdir(parents=True, exist_ok=True)
    (OUT / "item").mkdir(parents=True, exist_ok=True)
    for name in PALETTES:
        path = OUT / "entity" / "hamster" / ("%s.png" % name)
        draw(name).save(path)
        print("  %s" % path.relative_to(ROOT))
    egg = OUT / "item" / "hamster_spawn_egg.png"
    spawn_egg().save(egg)
    print("  %s" % egg.relative_to(ROOT))

    (OUT / "block").mkdir(parents=True, exist_ok=True)
    for path, image in (("entity/hamster_wheel.png", draw_wheel()),
                        ("block/hamster_wheel.png", draw_wheel_frame()),
                        ("item/hamster_wheel.png", draw_wheel_item()),
                        ("item/hamster.png", draw_hamster_item())):
        target = OUT / path
        image.save(target)
        print("  %s" % target.relative_to(ROOT))
    print("  VERIFIED: the UV layout matches the models for all %d boxes"
          % (len(BOXES) + len(WHEEL_BOXES)))


def cmd_preview():
    from preview import sheet
    out = ROOT / "build" / "preview.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet(draw, BOXES, rects, list(PALETTES)).save(out)
    print("  %s" % out)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "write"
    if cmd == "write":
        cmd_write()
    elif cmd == "preview":
        cmd_preview()
    else:
        sys.exit(__doc__)
