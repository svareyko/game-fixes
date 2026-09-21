#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Builds the Ore Map mod for Minecraft 26.2 / Fabric - without Gradle and Loom.

Why without them: Minecraft 26.x ships UNobfuscated (Mojang stopped publishing
mappings with 26.1, Yarn never came out for 26.2, fabric-intermediary for 26.2
is an empty stub). Loom's main job, remapping, is a no-op here, so javac and a
hand-written fabric.mod.json are enough. Everything needed is already on disk,
no network access is required.

    python build.py build        build the jar
    python build.py install      build it and put it into mods/ (with a backup)
    python build.py uninstall    remove it from mods/

The build has to be told where the installed game is - see "Building from
source" in README.md. The checks it runs are described in docs/how-it-works.md.
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

# The classpath folder - a couple of hundred jars, about 180 MB. It is rebuilt
# from the game files on every run, so it is kept in the temporary files of the
# system and not in the project folder.
CP_DIR = Path(tempfile.gettempdir()) / "oremap-classpath"

MOD_ID = "oremap"


def mod_version():
    """The version comes from the manifest, so that the jar name and the manifest cannot drift apart."""
    meta = HERE / "resources" / "fabric.mod.json"
    return json.loads(meta.read_text(encoding="utf-8"))["version"]


def jar_name():
    return "%s-%s.jar" % (MOD_ID, mod_version())

# The game directory: build_local.GAME_DIR, else the environment variable MC_GAME_DIR,
# else the default location.
if build_local is not None and hasattr(build_local, "GAME_DIR"):
    GAME_DIR = Path(build_local.GAME_DIR)
elif os.environ.get("MC_GAME_DIR"):
    GAME_DIR = Path(os.environ["MC_GAME_DIR"])
else:
    GAME_DIR = Path(os.environ.get("APPDATA", str(Path.home()))) / ".minecraft"

# The Fabric profile folder: the environment variable MC_PROFILE_DIR, else build_local.PROFILE_DIR.
if os.environ.get("MC_PROFILE_DIR"):
    PROFILE = Path(os.environ["MC_PROFILE_DIR"])
elif build_local is not None and hasattr(build_local, "PROFILE_DIR"):
    PROFILE = Path(build_local.PROFILE_DIR)
else:
    sys.exit(
        "STOP: the build does not know which installed game to compile against.\n"
        "\n"
        "It needs the Fabric profile folder - the folder of one installed game version.\n"
        "It contains <name>.jar (the Minecraft client), <name>.json and the mods/ folder,\n"
        "where <name> is the name of the folder itself; it usually lives in\n"
        "<game directory>/versions/<name>. The mod is compiled against that client jar\n"
        "and against Fabric API and Xaero's Minimap from its mods/ folder.\n"
        "\n"
        "Tell the build where it is, either way:\n"
        "  * set the environment variable MC_PROFILE_DIR to the full path of that folder, or\n"
        "  * create build_local.py next to build.py with the line\n"
        "        PROFILE_DIR = r\"<full path of that folder>\"\n"
        "\n"
        "If the game is not in %APPDATA%/.minecraft, set MC_GAME_DIR (or GAME_DIR in\n"
        "build_local.py) as well: the libraries and the Java runtime are taken from there."
    )
CLIENT_JAR = PROFILE / (PROFILE.name + ".jar")
MODS = PROFILE / "mods"
XAERO_JAR_GLOB = "xaerominimap-*.jar"
FABRIC_API_GLOB = "fabric-api-*.jar"

# Jars that must NOT get onto the classpath: a libraries folder shared with other
# installed versions can hold the client jars of an older Minecraft (1.21.11 is
# what was met) and of Forge, and javac silently resolves net.minecraft from them
# instead of 26.2 - the compilation passes and the mod crashes in the game.
BAD_MARKERS = ("1.21", "forge", "/v1/objects/")


def die(msg, code=2):
    print("STOP: " + msg, file=sys.stderr)
    sys.exit(code)


def jdk_bin():
    """The JDK from the runtime of the game itself - the same Java 25 the mod will run on.
    If the game runtime has none: JAVA_HOME, then javac on PATH."""
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
    die("javac not found in %s, in JAVA_HOME or on PATH" % root)


def one(glob_pattern):
    found = sorted(MODS.glob(glob_pattern))
    if not found:
        die("%s does not contain %s" % (MODS, glob_pattern))
    return found[-1]


def build_classpath():
    """Collects a flat folder of jars for -cp. A folder and not a long string:
    a list of paths runs into the 32767 character limit of the Windows command line."""
    if CP_DIR.exists():
        shutil.rmtree(CP_DIR)
    CP_DIR.mkdir(parents=True)

    skipped = 0
    libs = GAME_DIR / "libraries"
    for jar in libs.rglob("*.jar"):
        rel = jar.relative_to(libs).as_posix().lower()
        if any(bad in rel for bad in BAD_MARKERS) or rel.endswith("/client.jar"):
            skipped += 1
            continue
        shutil.copy2(jar, CP_DIR / jar.relative_to(libs).as_posix().replace("/", "__"))

    if not CLIENT_JAR.is_file():
        die("the client jar %s was not found" % CLIENT_JAR)
    shutil.copy2(CLIENT_JAR, CP_DIR / "AAA-minecraft.jar")

    xaero = one(XAERO_JAR_GLOB)
    shutil.copy2(xaero, CP_DIR / "xaerominimap.jar")

    nested = 0
    for src, prefix in ((one(FABRIC_API_GLOB), "fapi__"), (xaero, "xaero__")):
        with zipfile.ZipFile(src) as z:
            for entry in z.namelist():
                if entry.startswith("META-INF/jars/") and entry.endswith(".jar"):
                    (CP_DIR / (prefix + os.path.basename(entry))).write_bytes(z.read(entry))
                    nested += 1

    print("  classpath: %d jars (other versions skipped: %d, nested modules: %d)"
          % (len(list(CP_DIR.iterdir())), skipped, nested))
    print("  client   : %s" % CLIENT_JAR.name)
    print("  Xaero    : %s" % xaero.name)
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

    Pulls every reference to net/minecraft/** and xaero/** out of the compiled
    classes and makes sure that each such class really exists in the 26.2 client
    jar and in the installed minimap. This catches both a compilation against
    another version of the game and internal Xaero classes that moved.
    """
    javap = str(jdk_bin() / "javap")
    classes = sorted(str(p) for p in CLASSES.rglob("*.class"))
    names = [os.path.relpath(c, CLASSES).replace(os.sep, ".")[:-len(".class")] for c in classes]
    scan_cp = cp + os.pathsep + str(CLASSES)
    result = subprocess.run([javap, "-p", "-c", "-cp", scan_cp] + names,
                            capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        die("javap returned %d: %s" % (result.returncode, result.stderr.strip()[:400]))

    refs = set(re.findall(r"(net/minecraft/[\w/$]+|xaero/[\w/$]+)", result.stdout))
    with zipfile.ZipFile(CLIENT_JAR) as z:
        mc_entries = set(z.namelist())
    with zipfile.ZipFile(one(XAERO_JAR_GLOB)) as z:
        xaero_entries = set(z.namelist())
        for entry in list(z.namelist()):
            if entry.startswith("META-INF/jars/") and entry.endswith(".jar"):
                import io
                with zipfile.ZipFile(io.BytesIO(z.read(entry))) as inner:
                    xaero_entries |= set(inner.namelist())

    missing = []
    for ref in sorted(refs):
        entry = ref + ".class"
        pool = mc_entries if ref.startswith("net/minecraft/") else xaero_entries
        if entry not in pool:
            missing.append(ref)

    mc_refs = sum(1 for r in refs if r.startswith("net/minecraft/"))
    xa_refs = len(refs) - mc_refs
    print("  references checked: %d to Minecraft 26.2, %d to Xaero" % (mc_refs, xa_refs))
    if missing:
        for m in missing:
            print("    MISSING: " + m)
        die("the mod refers to classes that are absent from the installed game or minimap")
    print("  VERIFIED: every class the mod refers to is in place")


def package():
    meta = RES / "fabric.mod.json"
    if not meta.is_file():
        die("%s is missing" % meta)
    parsed = json.loads(meta.read_text(encoding="utf-8"))
    entry = parsed["entrypoints"]["client"][0]
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
    wanted = entry.replace(".", "/") + ".class"
    if wanted not in names:
        die("the entry point %s did not get into the jar" % entry)
    print("  built: %s (%d bytes, %d entries)"
          % (jar_path.name, jar_path.stat().st_size, len(names)))
    return jar_path


def validate_manifest(cp, jar_path):
    """Runs fabric.mod.json through the ModMetadataParser of fabric-loader itself.

    The point is the same as with the disassembler check: the judge is not our
    own reading of the JSON but the very code that will read the manifest when
    the game starts. Any warning counts as a failed build.
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
    """Runs the pure logic of the mod without starting the game: address classification
    (the border "local network / public server") and grouping blocks into veins."""
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


def cmd_build(args):
    print("=" * 74)
    cp = build_classpath()
    compile_sources(cp)
    verify_references(cp)
    self_test(cp)
    jar_path = package()
    validate_manifest(cp, jar_path)
    return jar_path


def cmd_install(args):
    jar_path = cmd_build(args)
    target = MODS / jar_name()
    if target.exists():
        # the backup goes into build/ and not into mods/: stray files in the mods
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
        die("the mod files are held by another process - Minecraft is running.\n"
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
