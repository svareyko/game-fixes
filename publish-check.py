#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pre-publication check: what is inside the files that git would publish.

.gitignore decides WHICH files leave this machine. It cannot see a home-directory
path, a LAN address or a machine name sitting inside a README that is allowed
through. This script lists exactly those, for the files git would track.

    python publish-check.py            report, exit code 1 on personal markers
    python publish-check.py --staged   the same, but only for what is already in the index
                                       (the gate right before "git commit")
    python publish-check.py --list     only print the files git would track

Works before the repository exists: without a .git here it evaluates the ignore
rules through a throw-away git directory in the system temp folder and removes it.

Personal markers are not written into this file - it is published too. The
account and machine names come from the environment of whoever runs it. Words
that are private to one owner go, one regular expression per line, into
.publish-check.local (ignored by git).
"""

import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
from urllib.parse import unquote

ROOT = os.path.dirname(os.path.abspath(__file__))
LOCAL_PATTERNS_FILE = os.path.join(ROOT, ".publish-check.local")
BINARY_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".jar", ".zip", ".class", ".dmp", ".exe", ".dll"}

BS = re.escape("\\")
PATH_TAIL = r"[^\s`\"'|)<>,;]*"

# "hard" findings fail the check; "soft" ones are listed for a human to judge
# (a documented default install path is fine, the owner's Steam library is not).
GENERIC = [
    ("home directory", True, r"(?i)\b[A-Z]:[" + BS + r"/]+Users[" + BS + r"/]+(?!Public\b|<)" + PATH_TAIL),
    ("home directory", True, r"(?<![\w.])/(?:home|Users)/(?!<)[\w.-]+" + PATH_TAIL),
    ("agent transcript path", True, r"(?i)[" + BS + r"/]\.claude[" + BS + r"/]" + PATH_TAIL),
    ("LAN address", False, r"(?<![\d.])(?:192\.168|10\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}(?::\d+)?(?![\d.])"),
    ("absolute drive path", False, r"(?<![A-Za-z])[D-Zd-z]:" + BS + PATH_TAIL),
    ("e-mail", False, r"[\w.+-]+@[\w-]+\.[a-z]{2,}\b"),
    ("hardware description", False, r"(?i)\b(?:Core Ultra \d|Core i\d|Ryzen \d|RTX ?\d{4}|GTX ?\d{3,4}|Radeon RX ?\d{3,4})[\w ]*"),
]


MARKDOWN_LINK = re.compile(r"\]\(\s*<?([^)\s>#]+)[^)]*\)")


def link_findings(rel, text, published):
    """Relative Markdown links that point outside the repository or at a file that stays local."""
    outside, unpublished = set(), set()
    for target in MARKDOWN_LINK.findall(text):
        if re.match(r"(?i)[a-z][a-z0-9+.-]*:", target):  # http:, https:, mailto:
            continue
        resolved = os.path.normpath(os.path.join(os.path.dirname(rel), unquote(target))).replace(os.sep, "/")
        if resolved == ".." or resolved.startswith("../"):
            outside.add(target)
        elif resolved != "." and resolved not in published and not any(p.startswith(resolved.rstrip("/") + "/") for p in published):
            unpublished.add(target)
    return outside, unpublished


CYRILLIC = re.compile("[\u0400-\u04FF]")
GITHUB_LINK = re.compile(r"github\.com[/:]([\w.-]+)/([\w.-]+?)(?:\.git)?(?=[/\s\"')>#?]|$)", re.M)


def is_russian_file(rel):
    """English is the primary language; Russian lives in *.ru.md and in ru_ru.json language packs."""
    name = os.path.basename(rel).lower()
    return name.endswith(".ru.md") or name == "ru_ru.json"


def origin_repository():
    """(owner, repo) of the origin remote, or None when there is no repository or no remote yet."""
    if not os.path.exists(os.path.join(ROOT, ".git")):
        return None
    result = subprocess.run(["git", "-C", ROOT, "remote", "get-url", "origin"], capture_output=True, text=True)
    match = GITHUB_LINK.search(result.stdout.strip()) if result.returncode == 0 else None
    return (match.group(1).lower(), match.group(2).lower()) if match else None


def environment_markers():
    names = {os.environ.get("USERNAME"), os.environ.get("USER"), os.environ.get("COMPUTERNAME"), socket.gethostname()}
    # Short or generic names would match ordinary words; the match is case-insensitive, so fold duplicates.
    names = {n.lower() for n in names if n and len(n) >= 4 and n.lower() not in {"user", "admin", "root", "home"}}
    return [("account or machine name", True, r"(?i)[\w.@-]*" + re.escape(n) + r"[\w.@:-]*") for n in sorted(names)]


def local_markers():
    if not os.path.exists(LOCAL_PATTERNS_FILE):
        return []
    markers = []
    for line in open(LOCAL_PATTERNS_FILE, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#"):
            markers.append(("owner's private word", True, line))
    return markers


def tracked_files(staged_only=False):
    """Paths git would publish: already tracked plus untracked-but-not-ignored (or the index only)."""
    command = ["ls-files", "-z", "--cached"] + ([] if staged_only else ["--others", "--exclude-standard"])
    if os.path.exists(os.path.join(ROOT, ".git")):
        output = subprocess.run(["git", "-C", ROOT] + command, capture_output=True, check=True).stdout
    else:
        scratch = tempfile.mkdtemp(prefix="publish-check-")
        try:
            subprocess.run(["git", "init", "-q", scratch], check=True)
            git_dir = os.path.join(scratch, ".git")
            output = subprocess.run(
                ["git", "--git-dir=" + git_dir, "--work-tree=" + ROOT] + command,
                capture_output=True, check=True, cwd=ROOT,
            ).stdout
        finally:
            shutil.rmtree(scratch, ignore_errors=True)
    return sorted(p for p in output.decode("utf-8").split("\0") if p)


def main():
    # newline="\n": on Windows the default "\r\n" breaks `--list | while read` in a POSIX shell.
    sys.stdout.reconfigure(errors="replace", newline="\n")
    files = tracked_files(staged_only="--staged" in sys.argv)
    if "--list" in sys.argv:
        print("\n".join(files))
        return 0

    markers = [(name, hard, re.compile(rx)) for name, hard, rx in environment_markers() + local_markers() + GENERIC]
    published = set(files)
    origin = origin_repository()
    hard_files = soft_files = 0
    for rel in files:
        if os.path.splitext(rel)[1].lower() in BINARY_EXTENSIONS or rel == os.path.basename(__file__):
            continue
        data = open(os.path.join(ROOT, rel), "rb").read()
        if b"\0" in data[:4096]:
            continue
        text = data.decode("utf-8", "replace")
        lines, is_hard = [], False
        for name, hard, pattern in markers:
            found = sorted({m.group(0).strip(" .,;:()*`") for m in pattern.finditer(text)})
            if found:
                is_hard = is_hard or hard
                shown = " | ".join(s[:60] for s in found[:5]) + (f" (+{len(found) - 5})" if len(found) > 5 else "")
                lines.append(f"    {'FAIL' if hard else 'look'}  {name}: {shown}")
        if not is_russian_file(rel):
            cyrillic_lines = sum(1 for line in text.split("\n") if CYRILLIC.search(line))
            if cyrillic_lines:
                lines.append(f"    look  Russian text outside *.ru.md / ru_ru.json: {cyrillic_lines} line(s)")
        if origin is not None:
            foreign = sorted({f"{o}/{r}" for o, r in GITHUB_LINK.findall(text)
                              if o.lower() == origin[0] and r.lower() != origin[1]})
            if foreign:
                lines.append("    look  link to another repository of the same owner: " + " | ".join(foreign[:5]))
        if rel.lower().endswith(".md"):
            outside, unpublished = link_findings(rel, text, published)
            if outside:
                is_hard = True
                lines.append("    FAIL  link leaving the repository: " + " | ".join(sorted(outside)[:5]))
            if unpublished:
                lines.append("    look  link to a file that is not published: " + " | ".join(sorted(unpublished)[:5]))
        if lines:
            hard_files += is_hard
            soft_files += not is_hard
            print(rel)
            print("\n".join(lines))

    print()
    print(f"{len(files)} files would be published; personal markers in {hard_files}, worth a look: {soft_files}")
    if hard_files:
        print("FAIL: clean the files marked FAIL, or keep them out via .gitignore, before pushing")
        return 1
    print("OK: no personal markers")
    return 0


if __name__ == "__main__":
    sys.exit(main())
