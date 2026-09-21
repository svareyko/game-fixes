#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Builds the Hamsters mod for Minecraft 26.2 / Fabric - without Gradle and Loom.

Why without them: Minecraft 26.x ships UNobfuscated (Mojang stopped publishing
mappings with 26.1, Yarn was never released for 26.2, fabric-intermediary for
26.2 is an empty stub). Loom's main job, remapping, is a no-op here, so javac
and a hand-written fabric.mod.json are enough. Everything needed is already on
disk, no network access is required.

    python build.py build        build the jar
    python build.py install      build and copy into mods/ (with a backup)
    python build.py uninstall    remove from mods/

How to tell the script where the game is: "Building from source" in README.md.
The reasoning behind the checks: docs/how-it-works.md.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

# Machine-local settings are not published. An optional build_local.py next to this file may define
#   PROFILE_DIR             the Fabric profile folder to build against and to install into
#   GAME_DIR                the game directory, if it is not %APPDATA%/.minecraft
#   after_mods_changed(mods_dir, mod_id)   called after install/uninstall
try:
    import build_local
except ImportError:
    build_local = None

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
SRC = HERE / "src"
RES = HERE / "resources"
BUILD = HERE / "build"
CLASSES = BUILD / "classes"

# The classpath folder - about 140 jars, around 130 MB. It is rebuilt from the
# game files on every run, so it lives in the temporary files of the system, not
# in the project folder.
CP_DIR = Path(tempfile.gettempdir()) / "hamster-classpath"

MOD_ID = "hamster"


def mod_version():
    """The version is read from the mod metadata, so the jar name and fabric.mod.json cannot drift apart."""
    meta = HERE / "resources" / "fabric.mod.json"
    return json.loads(meta.read_text(encoding="utf-8"))["version"]


def jar_name():
    return "%s-%s.jar" % (MOD_ID, mod_version())

NO_PROFILE = """ERROR: the Fabric profile folder is not set.

A profile folder is the folder one Fabric installation of the game runs from.
It contains
    <name>.jar     the Minecraft 26.2 client, named after the folder
    <name>.json    the version manifest that lists the libraries of the profile
    mods/          the mods of the profile, Fabric API among them

Point build.py at it in either way:
    set the environment variable MC_PROFILE_DIR to that folder, or
    create a file build_local.py next to build.py with the line
        PROFILE_DIR = r"<path to the profile folder>"

If the game directory (the one with libraries/ and runtime/) is not
%APPDATA%/.minecraft, set GAME_DIR in build_local.py or the environment
variable MC_GAME_DIR as well."""

GAME_DIR = Path(getattr(build_local, "GAME_DIR", None)
                or os.environ.get("MC_GAME_DIR")
                or Path(os.environ.get("APPDATA", str(Path.home()))) / ".minecraft")
PROFILE = os.environ.get("MC_PROFILE_DIR") or getattr(build_local, "PROFILE_DIR", None)
if not PROFILE:
    print(NO_PROFILE, file=sys.stderr)
    sys.exit(2)
PROFILE = Path(PROFILE)
CLIENT_JAR = PROFILE / (PROFILE.name + ".jar")
MODS = PROFILE / "mods"
FABRIC_API_GLOB = "fabric-api-*.jar"

VERSION_JSON = PROFILE / (PROFILE.name + ".json")


def die(msg, code=2):
    print("ERROR: " + msg, file=sys.stderr)
    sys.exit(code)


def jdk_bin():
    """The JDK from the runtime of the game itself - the same Java 25 the mod will run on.

    If the game runtime has no compiler, JAVA_HOME is tried next and then javac on PATH.
    """
    root = GAME_DIR / "runtime" / "java-runtime-epsilon"
    for path in root.rglob("bin/javac.exe"):
        return path.parent
    for path in root.rglob("bin/javac"):
        return path.parent
    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        for name in ("javac.exe", "javac"):
            if (Path(java_home) / "bin" / name).is_file():
                return Path(java_home) / "bin"
    on_path = shutil.which("javac")
    if on_path:
        return Path(on_path).resolve().parent
    die("javac (JDK 25 or newer) not found: not in %s, not in JAVA_HOME and not on PATH" % root)


def one(glob_pattern):
    found = sorted(MODS.glob(glob_pattern))
    if not found:
        die("%s does not contain %s" % (MODS, glob_pattern))
    return found[-1]


def maven_path(coords):
    """org.ow2.asm:asm:9.10.1 -> org/ow2/asm/asm/9.10.1/asm-9.10.1.jar"""
    parts = coords.split(":")
    group, artifact, version = parts[0], parts[1], parts[2]
    name = "%s-%s" % (artifact, version)
    if len(parts) > 3:
        name += "-" + parts[3]
    return Path(group.replace(".", "/")) / artifact / version / (name + ".jar")


def build_classpath():
    """Assembles a flat folder of jars for -cp.

    The list comes from the PROFILE MANIFEST (<profile>.json), not from walking
    the whole libraries folder. That matters: libraries also holds the libraries
    of other profiles - three different authlib, two datafixerupper, four asm.
    Walking the folder puts all of them on the classpath, and file order decides
    which one wins. Compilation still passes, and then the self-test dies with a
    NoSuchMethodError inside vanilla code. The manifest lists exactly the
    versions the game itself starts with.

    A folder, not a long string: a list of paths runs into the Windows command
    line limit of 32767 characters.
    """
    if CP_DIR.exists():
        shutil.rmtree(CP_DIR)
    CP_DIR.mkdir(parents=True)

    if not VERSION_JSON.is_file():
        die("profile manifest not found: %s" % VERSION_JSON)
    manifest = json.loads(VERSION_JSON.read_text(encoding="utf-8"))
    libs_root = GAME_DIR / "libraries"

    taken, missing, broken = 0, [], []
    for lib in manifest.get("libraries") or []:
        coords = lib.get("name")
        if not coords:
            continue
        rel = maven_path(coords)
        jar = libs_root / rel
        if not jar.is_file():
            # Libraries with rules are filtered by OS: the manifest carries the
            # natives for macOS and for Linux too, only the needed ones are
            # downloaded. Their absence is normal. A missing library WITHOUT
            # rules means a broken installation, and building against it is wrong.
            (missing if lib.get("rules") else broken).append(coords)
            continue
        shutil.copy2(jar, CP_DIR / rel.as_posix().replace("/", "__"))
        taken += 1

    if broken:
        for coords in broken[:5]:
            print("    file missing: %s" % coords)
        die("libraries lacks %d required libraries of the profile - the game installation is broken"
            % len(broken))
    if missing:
        print("  natives for other operating systems skipped: %d (as expected)" % len(missing))

    if not CLIENT_JAR.is_file():
        die("client jar not found: %s" % CLIENT_JAR)
    # AAA- in the name: with -cp folder/* the order is up to the file system,
    # and the game client has to come before libraries with the same packages.
    shutil.copy2(CLIENT_JAR, CP_DIR / "AAA-minecraft.jar")

    nested = 0
    with zipfile.ZipFile(one(FABRIC_API_GLOB)) as z:
        for entry in z.namelist():
            if entry.startswith("META-INF/jars/") and entry.endswith(".jar"):
                (CP_DIR / ("fapi__" + os.path.basename(entry))).write_bytes(z.read(entry))
                nested += 1

    print("  classpath: %d from the profile manifest + the client + %d Fabric API modules"
          % (taken, nested))
    print("  client   : %s" % CLIENT_JAR.name)
    return str(CP_DIR / "*")


def compile_sources(cp):
    if CLASSES.exists():
        shutil.rmtree(CLASSES)
    CLASSES.mkdir(parents=True)
    sources = sorted(str(p) for p in SRC.rglob("*.java"))
    if not sources:
        die("no sources in %s" % SRC)
    cmd = [str(jdk_bin() / "javac"), "-nowarn", "-encoding", "UTF-8",
           "-cp", cp, "-d", str(CLASSES), "--release", "25", "-proc:none"] + sources
    print("  compiling: %d files" % len(sources))
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.returncode != 0:
        print(result.stderr.strip(), file=sys.stderr)
        die("javac returned %d" % result.returncode)
    if result.stderr.strip():
        print(result.stderr.strip())


def verify_references(cp):
    """Checks the result with a disassembler instead of trusting "the script ran".

    Pulls every reference to net/minecraft/** out of the compiled classes and
    makes sure each of those classes really exists in the 26.2 client jar. This
    catches a build against the wrong game version: the libraries folder can
    hold the client of another version too, and javac silently resolves
    net.minecraft from there.
    """
    javap = str(jdk_bin() / "javap")
    classes = sorted(str(p) for p in CLASSES.rglob("*.class"))
    names = [os.path.relpath(c, CLASSES).replace(os.sep, ".")[:-len(".class")] for c in classes]
    scan_cp = cp + os.pathsep + str(CLASSES)
    result = subprocess.run([javap, "-p", "-c", "-cp", scan_cp] + names,
                            capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        die("javap returned %d: %s" % (result.returncode, result.stderr.strip()[:400]))

    refs = set(re.findall(r"(net/minecraft/[\w/$]+)", result.stdout))
    with zipfile.ZipFile(CLIENT_JAR) as z:
        mc_entries = set(z.namelist())

    missing = [ref for ref in sorted(refs) if (ref + ".class") not in mc_entries]
    print("  references checked: %d against Minecraft 26.2" % len(refs))
    if missing:
        for m in missing:
            print("    MISSING: " + m)
        die("the mod refers to classes that the installed game does not have")
    print("  VERIFIED: every class the mod refers to is present")


def package():
    meta = RES / "fabric.mod.json"
    if not meta.is_file():
        die("missing %s" % meta)
    parsed = json.loads(meta.read_text(encoding="utf-8"))
    entries = [e for kind in ("main", "client") for e in parsed["entrypoints"].get(kind, [])]
    BUILD.mkdir(parents=True, exist_ok=True)
    jar_path = BUILD / jar_name()
    with zipfile.ZipFile(jar_path, "w", zipfile.ZIP_DEFLATED) as z:
        for res in sorted(RES.rglob("*")):
            if res.is_file():
                z.write(res, res.relative_to(RES).as_posix())
        for cls in sorted(CLASSES.rglob("*.class")):
            z.write(cls, cls.relative_to(CLASSES).as_posix())

    # an entry point has to be inside the jar that was built
    with zipfile.ZipFile(jar_path) as z:
        names = set(z.namelist())
    for entry in entries:
        wanted = entry.replace(".", "/") + ".class"
        if wanted not in names:
            die("entry point %s did not make it into the jar" % entry)
    print("  built: %s (%d bytes, %d entries)"
          % (jar_path.name, jar_path.stat().st_size, len(names)))
    return jar_path


def validate_manifest(cp, jar_path):
    """Runs fabric.mod.json through the ModMetadataParser of fabric-loader itself.

    Same idea as the disassembler check: the judge is not our own reading of the
    JSON but the very code that will read the metadata when the game starts.
    Any warning counts as a failed build.
    """
    tool_src = HERE / "tools" / "ValidateMod.java"
    if not tool_src.is_file():
        print("  metadata validator not found, skipping")
        return
    out = BUILD / "tools"
    out.mkdir(parents=True, exist_ok=True)
    javac = str(jdk_bin() / "javac")
    java = str(jdk_bin() / "java")
    compiled = subprocess.run([javac, "-nowarn", "-encoding", "UTF-8", "-cp", cp,
                               "-d", str(out), str(tool_src)],
                              capture_output=True, text=True, encoding="utf-8", errors="replace")
    if compiled.returncode != 0:
        die("the metadata validator did not compile: " + compiled.stderr.strip()[:400])
    run = subprocess.run([java, "-cp", str(out) + os.pathsep + cp, "ValidateMod", str(jar_path)],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    for line in (run.stdout or "").strip().splitlines():
        print("  " + line)
    if run.returncode != 0:
        print((run.stderr or "").strip()[:600], file=sys.stderr)
        die("fabric-loader rejected the mod metadata")


def self_test(cp):
    """Exercises the models without starting the game (tools/SelfTest.java): bakes the
    hamster and the wheel, looks up every model part by name and runs setupAnim."""
    src = HERE / "tools" / "SelfTest.java"
    if not src.is_file():
        print("  self-test not found, skipping")
        return
    out = BUILD / "tools"
    out.mkdir(parents=True, exist_ok=True)
    test_cp = cp + os.pathsep + str(CLASSES)
    compiled = subprocess.run([str(jdk_bin() / "javac"), "-nowarn", "-encoding", "UTF-8",
                               "-cp", test_cp, "-d", str(out), str(src)],
                              capture_output=True, text=True, encoding="utf-8", errors="replace")
    if compiled.returncode != 0:
        die("the self-test did not compile: " + compiled.stderr.strip()[:400])
    run = subprocess.run([str(jdk_bin() / "java"), "-cp", str(out) + os.pathsep + test_cp, "SelfTest"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    for line in (run.stdout or "").strip().splitlines():
        print("  " + line)
    if run.returncode != 0:
        die("the self-test failed")


def verify_resources(jar_path):
    """Checks that the jar holds exactly what the mod refers to by name.

    Texture paths are put together as strings in HamsterVariant, and a typo
    there does not break the build - in the game it gives a purple-and-black
    checkerboard instead of a hamster. So the list of colour variants is read
    from the enum itself, and the files are looked up in the finished archive.
    """
    src = (SRC / "hamster" / "HamsterVariant.java").read_text(encoding="utf-8")
    variants = re.findall(r'^\s*[A-Z_]+\("([a-z_]+)"\)', src, re.M)
    if not variants:
        die("could not read the list of colour variants from HamsterVariant.java")

    problems = []
    with zipfile.ZipFile(jar_path) as z:
        names = set(z.namelist())
        for v in variants:
            entry = "assets/hamster/textures/entity/hamster/%s.png" % v
            if entry not in names:
                problems.append("no texture for the variant %s (%s)" % (v, entry))
            elif len(z.read(entry)) == 0:
                problems.append("empty texture %s" % entry)
        for must in ("assets/hamster/textures/item/hamster_spawn_egg.png",
                     "assets/hamster/items/hamster_spawn_egg.json",
                     "assets/hamster/models/item/hamster_spawn_egg.json",
                     "assets/hamster/lang/ru_ru.json",
                     "assets/hamster/lang/en_us.json",
                     "assets/hamster/blockstates/hamster_wheel.json",
                     "assets/hamster/models/block/hamster_wheel.json",
                     "assets/hamster/models/item/hamster_wheel.json",
                     "assets/hamster/items/hamster_wheel.json",
                     "assets/hamster/textures/block/hamster_wheel.png",
                     "assets/hamster/textures/entity/hamster_wheel.png",
                     "assets/hamster/textures/item/hamster_wheel.png",
                     "data/hamster/loot_table/blocks/hamster_wheel.json",
                     "data/hamster/recipe/hamster_wheel.json",
                     "assets/hamster/items/hamster.json",
                     "assets/hamster/models/item/hamster.json",
                     "assets/hamster/textures/item/hamster.png"):
            if must not in names:
                problems.append("missing " + must)

        # Every JSON has to parse: the game swallows a broken file silently,
        # and the block turns into a purple cube.
        for name in names:
            if name.endswith(".json"):
                try:
                    json.loads(z.read(name).decode("utf-8"))
                except ValueError as exc:
                    problems.append("cannot parse %s: %s" % (name, exc))

        # The blockstate has to cover ALL combinations of the block properties: a
        # missing combination means "model not found" in the log and a purple cube.
        entry = "assets/hamster/blockstates/hamster_wheel.json"
        if entry in names:
            declared = json.loads(z.read(entry).decode("utf-8")).get("variants", {})
            want = {"facing=%s,occupied=%s" % (f, o)
                    for f in ("north", "south", "east", "west")
                    for o in ("false", "true")}
            missing_states = sorted(want - set(declared))
            if missing_states:
                problems.append("the blockstate lacks the combinations: %s" % ", ".join(missing_states[:4]))
        for lang in ("ru_ru", "en_us"):
            entry = "assets/hamster/lang/%s.json" % lang
            if entry in names:
                keys = json.loads(z.read(entry).decode("utf-8"))
                for key in ("entity.hamster.hamster", "entity.hamster.thrown_hamster",
                            "item.hamster.hamster", "item.hamster.hamster_spawn_egg",
                            "block.hamster.hamster_wheel",
                            "message.hamster.tame_first", "message.hamster.not_yours"):
                    if key not in keys:
                        problems.append("%s lacks the key %s" % (entry, key))

    if problems:
        for text in problems:
            print("    - " + text)
        die("the resources of the mod are incomplete")
    print("  VERIFIED: %d colour variants, the whole wheel, both languages; every JSON parses"
          % len(variants))


def cmd_build(args):
    print("=" * 74)
    cp = build_classpath()
    compile_sources(cp)
    verify_references(cp)
    self_test(cp)
    jar_path = package()
    verify_resources(jar_path)
    validate_manifest(cp, jar_path)
    return jar_path


def cmd_install(args):
    jar_path = cmd_build(args)
    target = MODS / jar_name()
    if target.exists():
        # the backup goes into build/, not into mods/: stray files in the mods
        # folder only cause confusion later
        backup = BUILD / (jar_name() + ".installed-before")
        shutil.copy2(target, backup)
        print("  previous version saved: build/%s" % backup.name)
    # Older versions have to go: a mods folder should hold one jar per mod id,
    # otherwise it is the loader, not you, that decides which version runs.
    try:
        for old_jar in MODS.glob(MOD_ID + "-*.jar"):
            if old_jar.name != target.name:
                old_jar.unlink()
                print("  previous version removed: %s" % old_jar.name)
        shutil.copy2(jar_path, target)
    except PermissionError:
        die("the mod files are in use by another process - Minecraft is running.\n"
            "       Close the game and run install again. The built jar is ready:\n"
            "       %s" % jar_path)
    print("  installed: %s" % target)
    if build_local is not None and hasattr(build_local, "after_mods_changed"):
        build_local.after_mods_changed(MODS, MOD_ID)
    print("\nMods in the profile:")
    for m in sorted(MODS.glob("*.jar")):
        print("  %-50s %d" % (m.name, m.stat().st_size))
    return 0


def cmd_uninstall(args):
    removed = 0
    for jar in sorted(MODS.glob(MOD_ID + "-*.jar")):
        jar.unlink()
        print("  removed: %s" % jar)
        removed += 1
    if not removed:
        print("  %s is not installed" % MOD_ID)
    if build_local is not None and hasattr(build_local, "after_mods_changed"):
        build_local.after_mods_changed(MODS, MOD_ID)
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["build", "install", "uninstall"])
    args = ap.parse_args()
    handlers = {"build": cmd_build, "install": cmd_install, "uninstall": cmd_uninstall}
    result = handlers[args.command](args)
    return 0 if not isinstance(result, int) else result


if __name__ == "__main__":
    sys.exit(main())
