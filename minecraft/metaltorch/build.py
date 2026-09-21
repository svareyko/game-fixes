#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Builds the Metal Torches mod for Minecraft 26.2 / Fabric - without Gradle and Loom.

Why without them: Minecraft 26.x ships UNobfuscated (Mojang stopped publishing
mappings as of 26.1, Yarn was never released for 26.2, and fabric-intermediary
for 26.2 is an empty stub). Loom's main job, remapping, is a no-op here, so
javac and a hand-written fabric.mod.json are enough. Everything needed is
already on disk; no network access is required.

    python build.py build        build the jar
    python build.py install      build and copy it into mods/ (with a backup)
    python build.py uninstall    remove it from mods/

Details are in README.md next to this file.
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

# The classpath directory: a couple of hundred jars, about 180 MB. It is rebuilt
# from the game files on every run, so it lives in the system temp folder and
# not in the project.
CP_DIR = Path(tempfile.gettempdir()) / "metaltorch-classpath"

MOD_ID = "metaltorch"


def mod_version():
    """The version comes from the manifest, so the jar name and the manifest cannot drift apart."""
    meta = HERE / "resources" / "fabric.mod.json"
    return json.loads(meta.read_text(encoding="utf-8"))["version"]


def jar_name():
    return "%s-%s.jar" % (MOD_ID, mod_version())

NO_PROFILE = r"""STOPPED: the Fabric profile folder is not set.

  The profile folder is the folder of ONE game installation. It contains
      <name>.jar     the Minecraft client
      <name>.json    its version manifest, listing every library the game starts with
      mods/          with Fabric API inside
  where <name> is the name of the folder itself. The mod is compiled against
  exactly that game, and "install" copies the finished jar into its mods/.

  Tell the script where it is, in either way:
    * the environment variable MC_PROFILE_DIR
          set MC_PROFILE_DIR=%APPDATA%\.minecraft\versions\<name>            (cmd)
          $env:MC_PROFILE_DIR = "$env:APPDATA\.minecraft\versions\<name>"    (PowerShell)
          export MC_PROFILE_DIR=~/.minecraft/versions/<name>                 (Linux)
    * a file build_local.py next to build.py with the line
          PROFILE_DIR = r"C:\path\to\.minecraft\versions\<name>"

  If the game directory is not %APPDATA%/.minecraft, set MC_GAME_DIR
  (or GAME_DIR in build_local.py) as well: libraries/ and runtime/ are taken from there.
"""

if build_local is not None and hasattr(build_local, "GAME_DIR"):
    GAME_DIR = Path(build_local.GAME_DIR)
elif os.environ.get("MC_GAME_DIR"):
    GAME_DIR = Path(os.environ["MC_GAME_DIR"])
else:
    GAME_DIR = Path(os.environ.get("APPDATA", str(Path.home()))) / ".minecraft"

if os.environ.get("MC_PROFILE_DIR"):
    PROFILE = Path(os.environ["MC_PROFILE_DIR"])
elif build_local is not None and hasattr(build_local, "PROFILE_DIR"):
    PROFILE = Path(build_local.PROFILE_DIR)
else:
    sys.stderr.write(NO_PROFILE)
    sys.exit(2)
CLIENT_JAR = PROFILE / (PROFILE.name + ".jar")
MODS = PROFILE / "mods"
FABRIC_API_GLOB = "fabric-api-*.jar"

VERSION_JSON = PROFILE / (PROFILE.name + ".json")


def die(msg, code=2):
    print("STOPPED: " + msg, file=sys.stderr)
    sys.exit(code)


def jdk_bin():
    """The JDK from the game's own runtime - the same Java 25 the mod is going to run on.

    If the game runtime has no compiler: JAVA_HOME, then javac on PATH.
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
    die("javac not found: not in %s, not in JAVA_HOME, not on PATH" % root)


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
    """Builds a flat directory of jars for -cp.

    The list comes from the PROFILE MANIFEST (<name>.json), not from walking the
    whole libraries folder. This matters: libraries also holds jars that belong
    to other profiles - three different authlib, two datafixerupper, four asm.
    Walk the folder and all of them land on the classpath, and which one wins is
    decided by file order. Compilation still succeeds, and then the self-test
    dies with NoSuchMethodError inside vanilla code. The manifest lists exactly
    the versions the game itself starts with.

    A directory and not one long string: a list of paths runs into the
    32767-character limit of the Windows command line.
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
            # Libraries with "rules" are filtered by operating system: the
            # manifest lists the natives for macOS and Linux as well, and only
            # the ones needed here get downloaded. Their absence is normal.
            # A missing library WITHOUT rules means a broken installation, and
            # building against that is not an option.
            (missing if lib.get("rules") else broken).append(coords)
            continue
        shutil.copy2(jar, CP_DIR / rel.as_posix().replace("/", "__"))
        taken += 1

    if broken:
        for coords in broken[:5]:
            print("    missing file: %s" % coords)
        die("%d required libraries of the profile are missing from libraries - the game installation is broken"
            % len(broken))
    if missing:
        print("  natives for other operating systems skipped: %d (as expected)" % len(missing))

    if not CLIENT_JAR.is_file():
        die("client jar not found: %s" % CLIENT_JAR)
    # AAA- in the name: with -cp dir/* the order is up to the file system, and
    # the game client has to come before libraries that carry the same packages.
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
    """Checks the result with a disassembler instead of trusting "the script ran fine".

    Pulls every reference to net/minecraft/** out of the compiled classes and
    makes sure each of those classes really exists in the 26.2 client jar.
    This catches a build against the wrong game version: the libraries folder
    may also hold the client of another version, and javac silently resolves
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

    # the entry point has to be inside the built jar
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
    """Runs fabric.mod.json through fabric-loader's own ModMetadataParser.

    Same idea as the disassembler check: the judge is not our own JSON parsing
    but the very code that is going to read the manifest when the game starts.
    Any warning fails the build.
    """
    tool_src = HERE / "tools" / "ValidateMod.java"
    if not tool_src.is_file():
        print("  manifest validator not found, skipping")
        return
    out = BUILD / "tools"
    out.mkdir(parents=True, exist_ok=True)
    javac = str(jdk_bin() / "javac")
    java = str(jdk_bin() / "java")
    compiled = subprocess.run([javac, "-nowarn", "-encoding", "UTF-8", "-cp", cp,
                               "-d", str(out), str(tool_src)],
                              capture_output=True, text=True, encoding="utf-8", errors="replace")
    if compiled.returncode != 0:
        die("the manifest validator did not compile: " + compiled.stderr.strip()[:400])
    run = subprocess.run([java, "-cp", str(out) + os.pathsep + cp, "ValidateMod", str(jar_path)],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    for line in (run.stdout or "").strip().splitlines():
        print("  " + line)
    if run.returncode != 0:
        print((run.stderr or "").strip()[:600], file=sys.stderr)
        die("fabric-loader rejected the manifest")


def self_test(cp):
    """Runs tools/SelfTest.java without starting the game: it checks, on live
    vanilla blocks, the rule that gives a block its loot table - the rule the
    wall torch depends on to drop anything at all."""
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
    """Checks the archive against the list of metals in MetalTorch.java.

    The list of metals lives in the enum, and every metal needs ten files.
    A forgotten file does not crash the game: the block silently turns into a
    purple cube, and the recipe simply does not work. So every file is checked
    by name.
    """
    src = (SRC / "metaltorch" / "MetalTorch.java").read_text(encoding="utf-8")
    metals = re.findall(r'[A-Z]+\("([a-z_]+)",\s*0x[0-9A-Fa-f]{6}', src)
    if not metals:
        die("could not read the list of metals from MetalTorch.java")

    problems = []
    with zipfile.ZipFile(jar_path) as z:
        names = set(z.namelist())
        for metal in metals:
            standing, wall = "%s_torch" % metal, "%s_wall_torch" % metal
            for entry in (
                    "assets/metaltorch/textures/block/%s.png" % standing,
                    "assets/metaltorch/models/block/%s.json" % standing,
                    "assets/metaltorch/models/block/%s.json" % wall,
                    "assets/metaltorch/blockstates/%s.json" % standing,
                    "assets/metaltorch/blockstates/%s.json" % wall,
                    "assets/metaltorch/models/item/%s.json" % standing,
                    "assets/metaltorch/items/%s.json" % standing,
                    "data/metaltorch/loot_table/blocks/%s.json" % standing,
                    "data/metaltorch/recipe/%s.json" % standing,
                    "data/metaltorch/advancement/recipes/decorations/%s.json" % standing):
                if entry not in names:
                    problems.append("missing " + entry)

        for name in names:
            if name.endswith(".json"):
                try:
                    json.loads(z.read(name).decode("utf-8"))
                except ValueError as exc:
                    problems.append("cannot parse %s: %s" % (name, exc))

        for lang in ("ru_ru", "en_us"):
            entry = "assets/metaltorch/lang/%s.json" % lang
            if entry not in names:
                problems.append("missing " + entry)
                continue
            keys = json.loads(z.read(entry).decode("utf-8"))
            for metal in metals:
                for block in ("%s_torch" % metal, "%s_wall_torch" % metal):
                    key = "block.metaltorch.%s" % block
                    if key not in keys:
                        problems.append("%s has no key %s" % (entry, key))

        # The wall torch has no loot table of its own - it points at the table
        # of the standing torch, exactly like vanilla wall_torch. An extra file
        # would mean that somebody did not understand the scheme.
        for metal in metals:
            stray = "data/metaltorch/loot_table/blocks/%s_wall_torch.json" % metal
            if stray in names:
                problems.append("stray loot table %s: the wall torch takes the drops of the standing one"
                                % stray)

    if problems:
        for text in problems:
            print("    - " + text)
        die("the mod's resources are incomplete")
    print("  VERIFIED: %d metals, 10 files each, both languages; every JSON parses"
          % len(metals))


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
        # the backup goes to build/, not to mods/: stray files in the mods
        # folder only cause confusion later
        backup = BUILD / (jar_name() + ".installed-before")
        shutil.copy2(target, backup)
        print("  previous version saved: build/%s" % backup.name)
    # Old versions have to go: otherwise Fabric sees two mods with the same id
    # and refuses to start the game.
    try:
        for old_jar in MODS.glob(MOD_ID + "-*.jar"):
            if old_jar.name != target.name:
                old_jar.unlink()
                print("  previous version removed: %s" % old_jar.name)
        shutil.copy2(jar_path, target)
    except PermissionError:
        die("the mod files are locked by another process - Minecraft is running.\n"
            "         Close the game and run install again. The built jar is ready:\n"
            "         %s" % jar_path)
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
