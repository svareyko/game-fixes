#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Isometric render of the hamster model - to look at it without starting the game.

Called from textures.py: `python tools/textures.py preview`.

The camera sits at (+x, +y, -z), so the hamster is seen from the front and the
side: the top, the north face (for mobs that is the "front") and the east face
are visible. There are exactly two horizontal axes and they are not parallel -
otherwise the top face collapses into a line.
"""

import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

SHADE = {"up": 1.00, "north": 0.82, "east": 0.63}
EX = np.array([1.0, 0.5])        # +x  right and down
EY = np.array([0.0, -1.0])       # +y  up
EZ = np.array([1.0, -0.5])       # +z  right and up, away from the camera


def _blit(dst, tex, rect, O, A, B, shade):
    u, v, w, h = [int(t) for t in rect]
    src = np.asarray(tex.crop((u, v, u + w, v + h)).convert("RGBA"), dtype=np.float32)
    M = np.linalg.inv(np.array([[A[0], B[0]], [A[1], B[1]]], dtype=np.float64))
    xs = [O[0], O[0] + A[0], O[0] + B[0], O[0] + A[0] + B[0]]
    ys = [O[1], O[1] + A[1], O[1] + B[1], O[1] + A[1] + B[1]]
    x0, y0 = max(int(min(xs)), 0), max(int(min(ys)), 0)
    x1, y1 = min(int(max(xs)) + 1, dst.width), min(int(max(ys)) + 1, dst.height)
    if x1 <= x0 or y1 <= y0:
        return
    gy, gx = np.mgrid[y0:y1, x0:x1]
    uv = np.stack([gx - O[0], gy - O[1]], axis=-1).astype(np.float64) @ M.T
    uu, vv = uv[..., 0], uv[..., 1]
    ok = (uu >= 0) & (uu < 1) & (vv >= 0) & (vv < 1)
    samp = src[np.clip((vv * h).astype(int), 0, h - 1), np.clip((uu * w).astype(int), 0, w - 1)]
    ok &= samp[..., 3] > 0                      # cutout: transparent pixels are not drawn
    patch = np.asarray(dst.crop((x0, y0, x1, y1)).convert("RGB"), dtype=np.float32)
    patch[ok] = np.clip(samp[..., :3][ok] * shade, 0, 255)
    dst.paste(Image.fromarray(patch.astype(np.uint8)), (x0, y0))


def render(tex, boxes, rects, size=(400, 360), K=22.0, centre=(0.46, 0.74)):
    img = Image.new("RGB", size, (26, 26, 28))
    off = np.array([size[0] * centre[0], size[1] * centre[1]])
    P = lambda x, y, z: off + x * EX * K + y * EY * K + z * EZ * K
    # closer to the camera = larger x, larger y, smaller z
    order = sorted(boxes, key=lambda b: (b[3][0] + b[2][0] / 2)
                                        + (b[3][1] + b[2][1] / 2)
                                        - (b[3][2] + b[2][2] / 2))
    for _name, uv, sz, pos in order:
        w, h, d = sz
        x0, y0, z0 = pos
        x1, y1, z1 = x0 + w, y0 + h, z0 + d
        r = rects(uv, sz)
        for face, O, A, B in (
                ("up",    P(x0, y1, z0), P(x1, y1, z0) - P(x0, y1, z0), P(x0, y1, z1) - P(x0, y1, z0)),
                ("north", P(x0, y1, z0), P(x1, y1, z0) - P(x0, y1, z0), P(x0, y0, z0) - P(x0, y1, z0)),
                ("east",  P(x1, y1, z1), P(x1, y1, z0) - P(x1, y1, z1), P(x1, y0, z1) - P(x1, y1, z1))):
            _blit(img, tex, r[face], O, A, B, SHADE[face])
    return img


def _font(size, bold=False):
    for name in (("segoeuib.ttf" if bold else "segoeui.ttf"), "arial.ttf"):
        path = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", name)
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def sheet(draw_fn, boxes, rects, names):
    tiles = [(n, render(draw_fn(n), boxes, rects)) for n in names]
    w = sum(t[1].width for t in tiles)
    h = tiles[0][1].height + 84
    img = Image.new("RGB", (w, h), (26, 26, 28))
    d = ImageDraw.Draw(img)
    d.text((22, 14), "Hamster: colour variants", (245, 245, 245), font=_font(28, True))
    x = 0
    for name, tile in tiles:
        img.paste(tile, (x, 52))
        d.text((x + 22, tile.height + 58), name, (222, 222, 228), font=_font(20))
        x += tile.width
    return img
