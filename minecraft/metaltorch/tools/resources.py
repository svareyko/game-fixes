#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Resource generator for the metal torches.

    python tools/resources.py write     write everything into resources/
    python tools/resources.py preview   a picture of the textures in build/

Everything is uniform and differs only by the metal, so it is written by a
generator and not by hand: two metals give 2 textures, 4 block models,
4 blockstates, 2 item models, 2 item definitions, 2 loot tables, 2 recipes,
2 recipe-unlock advancements and two language files. Editing twenty-two files
by hand that differ in a single word is a good way to breed a typo.

The list of metals has to match the enum in MetalTorch.java; the write command
checks that and refuses to work when the two disagree.

The texture layout is taken from the vanilla template block/template_torch: the
model uses the strip x 7..9, y 6..16. Anything drawn outside of it shows up only
on the item icon, so we draw strictly inside the strip - as the game itself does.
"""

import json
import re
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow is required: python -m pip install pillow")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RES = ROOT / "resources"
JAVA_ENUM = ROOT / "src" / "metaltorch" / "MetalTorch.java"

# id: (colour of the sparks and the flame, ingredient, Russian name, English name)
# The Russian strings in this file are the content of lang/ru_ru.json, not
# messages of the script.
# Copper is deliberately absent: 26.2 has a vanilla Copper Torch, and one of our
# own would give two items with the same name. See MetalTorch.java.
METALS = {
    "iron":   (0xF0F4F8, "minecraft:iron_ingot",   "Железный факел", "Iron Torch"),
    "gold":   (0xFFD24A, "minecraft:gold_ingot",   "Золотой факел", "Gold Torch"),
}

# Mod Menu shows a translated description when the language file carries this
# key. The English text has a single home, fabric.mod.json, and is copied from
# there; the Russian text lives here, because ru_ru.json is generated and a
# hand-made edit in it would be lost on the next run.
DESCRIPTION_KEY = "modmenu.descriptionTranslation.metaltorch"
DESCRIPTION_RU = ("Факелы с металлом: железный светит почти белым, золотой тёплым жёлтым. "
                  "Оба дают уровень света 15 против 14 у обычного факела — это потолок движка. "
                  "Цвет виден в самом факеле и в искрах: свет в Minecraft бесцветный. "
                  "Медного нет намеренно — в 26.2 уже есть ванильный Copper Torch.")

STICK_DARK = (88, 62, 38)
STICK_LIGHT = (124, 90, 56)

TORCHES_PER_CRAFT = 4


def shade(colour, factor):
    r, g, b = (colour >> 16) & 0xFF, (colour >> 8) & 0xFF, colour & 0xFF
    return tuple(max(0, min(255, int(c * factor))) for c in (r, g, b))


def texture(colour):
    """A 16x16 torch: the stick, a metal ring and a flame of the given colour."""
    im = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    px = im.load()

    def row(y, left, right):
        px[7, y] = left + (255,)
        px[8, y] = right + (255,)

    for y in range(11, 16):                       # the stick
        row(y, STICK_DARK, STICK_LIGHT)
    row(10, shade(colour, 0.55), shade(colour, 0.75))    # the metal ring
    row(9,  shade(colour, 0.85), shade(colour, 1.00))    # the base of the flame
    row(8,  shade(colour, 1.00), shade(colour, 1.15))    # the flame
    row(7,  shade(colour, 1.20), shade(colour, 1.35))    # the core, the lightest part
    px[8, 6] = shade(colour, 1.45) + (255,)              # a tongue of flame on top
    return im


def check_enum_matches():
    """Checks the list of metals against MetalTorch.java: colour and ingredient."""
    if not JAVA_ENUM.is_file():
        return ["missing %s" % JAVA_ENUM]
    text = JAVA_ENUM.read_text(encoding="utf-8")
    found = {}
    for name, colour, ingredient in re.findall(
            r'[A-Z]+\("([a-z_]+)",\s*0x([0-9A-Fa-f]{6}),\s*"([^"]+)"\)', text):
        found[name] = (int(colour, 16), ingredient)

    problems = []
    for name, (colour, ingredient, _ru, _en) in METALS.items():
        if name not in found:
            problems.append("%s is not in MetalTorch.java" % name)
        elif found[name] != (colour, ingredient):
            problems.append("%s: here 0x%06X/%s, in Java 0x%06X/%s"
                            % (name, colour, ingredient, found[name][0], found[name][1]))
    for name in found:
        if name not in METALS:
            problems.append("%s is in MetalTorch.java but not here" % name)
    return problems


def write(rel, obj):
    path = RES / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(obj, Image.Image):
        obj.save(path)
    else:
        path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return rel


# Directories the generator owns completely: everything in them was written by
# it. So it is also the one that has to clear out stale files - otherwise a
# removed metal leaves its files behind, and they silently travel into the jar.
OWNED_DIRS = [
    "assets/metaltorch/textures/block",
    "assets/metaltorch/models/block",
    "assets/metaltorch/models/item",
    "assets/metaltorch/items",
    "assets/metaltorch/blockstates",
    "assets/metaltorch/lang",
    "data/metaltorch/loot_table/blocks",
    "data/metaltorch/recipe",
    "data/metaltorch/advancement/recipes/decorations",
]


def prune(written):
    keep = {(RES / rel).resolve() for rel in written}
    removed = []
    for owned in OWNED_DIRS:
        directory = RES / owned
        if not directory.is_dir():
            continue
        for path in sorted(directory.iterdir()):
            if path.is_file() and path.resolve() not in keep:
                path.unlink()
                removed.append(str(path.relative_to(RES)).replace("\\", "/"))
    return removed


def cmd_write():
    problems = check_enum_matches()
    if problems:
        for text in problems:
            print("    - " + text)
        sys.exit("STOPPED: the list of metals has drifted away from MetalTorch.java")

    written = []
    lang_ru, lang_en = {}, {}

    for name, (colour, ingredient, ru, en) in METALS.items():
        standing, wall = "%s_torch" % name, "%s_wall_torch" % name
        tex = "metaltorch:block/%s" % standing

        written.append(write("assets/metaltorch/textures/block/%s.png" % standing, texture(colour)))

        # Wrapper models over the vanilla templates: the torch has no geometry
        # of its own, only the texture changes.
        written.append(write("assets/metaltorch/models/block/%s.json" % standing,
                             {"parent": "minecraft:block/template_torch",
                              "textures": {"torch": tex}}))
        written.append(write("assets/metaltorch/models/block/%s.json" % wall,
                             {"parent": "minecraft:block/template_torch_wall",
                              "textures": {"torch": tex}}))

        written.append(write("assets/metaltorch/blockstates/%s.json" % standing,
                             {"variants": {"": {"model": "metaltorch:block/%s" % standing}}}))
        # The same rotations as vanilla wall_torch.
        written.append(write("assets/metaltorch/blockstates/%s.json" % wall,
                             {"variants": {
                                 "facing=east": {"model": "metaltorch:block/%s" % wall},
                                 "facing=south": {"model": "metaltorch:block/%s" % wall, "y": 90},
                                 "facing=west": {"model": "metaltorch:block/%s" % wall, "y": 180},
                                 "facing=north": {"model": "metaltorch:block/%s" % wall, "y": 270},
                             }}))

        written.append(write("assets/metaltorch/models/item/%s.json" % standing,
                             {"parent": "minecraft:item/generated",
                              "textures": {"layer0": tex}}))
        written.append(write("assets/metaltorch/items/%s.json" % standing,
                             {"model": {"type": "minecraft:model",
                                        "model": "metaltorch:item/%s" % standing}}))

        written.append(write("data/metaltorch/loot_table/blocks/%s.json" % standing,
                             {"type": "minecraft:block",
                              "random_sequence": "metaltorch:blocks/%s" % standing,
                              "pools": [{"rolls": 1.0,
                                         "conditions": [{"condition": "minecraft:survives_explosion"}],
                                         "entries": [{"type": "minecraft:item",
                                                      "name": "metaltorch:%s" % standing}]}]}))

        # A shapeless recipe: four ordinary torches and an ingot give four metal
        # torches. One for one would be ruinous for an ingot.
        # Without the unlock file the recipe WORKS, but the recipe book does not
        # show it: the book lists unlocked recipes only. Vanilla keeps exactly
        # such an advancement under advancement/recipes/ for each recipe of its
        # own. The first version of this mod got burnt on precisely that.
        written.append(write("data/metaltorch/advancement/recipes/decorations/%s.json" % standing,
                             {"parent": "minecraft:recipes/root",
                              "criteria": {
                                  "has_ingredient": {
                                      "trigger": "minecraft:inventory_changed",
                                      "conditions": {"items": [{"items": ingredient}]}},
                                  "has_the_recipe": {
                                      "trigger": "minecraft:recipe_unlocked",
                                      "conditions": {"recipe": "metaltorch:%s" % standing}}},
                              "requirements": [["has_the_recipe", "has_ingredient"]],
                              "rewards": {"recipes": ["metaltorch:%s" % standing]}}))

        written.append(write("data/metaltorch/recipe/%s.json" % standing,
                             {"type": "minecraft:crafting_shapeless",
                              "category": "misc",
                              "ingredients": ["minecraft:torch"] * TORCHES_PER_CRAFT + [ingredient],
                              "result": {"count": TORCHES_PER_CRAFT,
                                         "id": "metaltorch:%s" % standing}}))

        lang_ru["block.metaltorch.%s" % standing] = ru
        lang_ru["block.metaltorch.%s" % wall] = ru
        lang_en["block.metaltorch.%s" % standing] = en
        lang_en["block.metaltorch.%s" % wall] = en

    lang_ru[DESCRIPTION_KEY] = DESCRIPTION_RU
    lang_en[DESCRIPTION_KEY] = json.loads(
        (RES / "fabric.mod.json").read_text(encoding="utf-8"))["description"]

    written.append(write("assets/metaltorch/lang/ru_ru.json", lang_ru))
    written.append(write("assets/metaltorch/lang/en_us.json", lang_en))

    for rel in written:
        print("  " + rel)
    for rel in prune(written):
        print("  removed stale file: " + rel)
    print("  VERIFIED: %d metals checked against MetalTorch.java, %d files written"
          % (len(METALS), len(written)))


def cmd_preview():
    from PIL import ImageDraw, ImageFont
    import os
    k, pad, gap = 18, 34, 34
    tiles = [(n, texture(c).resize((16 * k, 16 * k), Image.NEAREST))
             for n, (c, _i, _ru, _en) in METALS.items()]
    w = pad * 2 + sum(t[1].width for t in tiles) + gap * (len(tiles) - 1)
    h = pad + 44 + tiles[0][1].height + 46
    img = Image.new("RGB", (w, h), (26, 26, 28))
    d = ImageDraw.Draw(img)

    def font(size, bold=False):
        path = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts",
                            "segoeuib.ttf" if bold else "segoeui.ttf")
        return ImageFont.truetype(path, size) if os.path.exists(path) else ImageFont.load_default()

    d.text((pad, 16), "Metal torches: textures", (245, 245, 245), font=font(24, True))
    x = pad
    for name, tile in tiles:
        img.paste(tile, (x, 62), tile)
        d.rectangle([x - 1, 61, x + tile.width, 62 + tile.height], outline=(70, 70, 76))
        d.text((x, 62 + tile.height + 12), name, (214, 214, 220), font=font(19))
        x += tile.width + gap
    out = ROOT / "build" / "torches.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    print("  %s" % out)


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "write"
    if command == "write":
        cmd_write()
    elif command == "preview":
        cmd_preview()
    else:
        sys.exit(__doc__)
