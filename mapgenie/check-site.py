#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Checks that the MapGenie site is still built the way mapgenie-tweaks.user.js expects
(both halves of it: categories and ads). Run it when the userscript stops working.

Changes nothing and writes nothing: it downloads the map page, its map.js and app.css into
memory and looks for the signatures the userscript relies on. What every check means and what
to do when one fails: docs/how-it-works.md next to this file, section "When it stops working".

    python check-site.py
    python check-site.py https://mapgenie.io/<game>/maps/<map>

Downloads with curl rather than urllib: the site sits behind Cloudflare, which lets curl with a
browser User-Agent through (checked 2026-09-20).

Author: bombuilder.by  (https://bombuilder.by)
"""

import json
import re
import shutil
import subprocess
import sys
from urllib.parse import urlparse

DEFAULT_PAGE = "https://mapgenie.io/stalker-2-heart-of-chornobyl/maps/the-zone"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
)

# URL parameters that make the site show a filtered view.
# Must match DEEP_LINK_PARAMS in the userscript.
DEEP_LINK_PARAMS = ["locationIds", "catIds", "groups", "regions", "tags", "route"]

# Hosts of the ad loaders. Must match AD_SCRIPT_HOSTS in the userscript.
AD_SCRIPT_HOSTS = {"cdn.ziffstatic.com", "cdn.static.zdbb.net"}
# The other hosts the page loads scripts from with tags: the site itself, libraries, Google Analytics.
KNOWN_SCRIPT_HOSTS = {
    "cdn.mapgenie.io",
    "cdn.jsdelivr.net",
    "ajax.googleapis.com",
    "cdnjs.cloudflare.com",
    "www.googletagmanager.com",
}
# Ad placeholders in the markup. Must match AD_CONTAINERS in the userscript.
AD_CONTAINER_IDS = ["blobby-left", "nitro-floating-wrapper", "blobby-overlay"]


def fetch(url):
    curl = shutil.which("curl")
    if not curl:
        sys.exit("curl is needed in PATH (Windows 10 and later ship it: C:\\Windows\\System32\\curl.exe)")
    result = subprocess.run(
        [curl, "-sS", "-L", "--fail", "-A", USER_AGENT, url],
        capture_output=True,
    )
    if result.returncode != 0:
        sys.exit(f"could not download {url}: {result.stderr.decode('utf-8', 'replace').strip()}")
    return result.stdout.decode("utf-8", "replace")


def main():
    # A Windows console may not be UTF-8: let unusual characters become "?" instead of an exception.
    sys.stdout.reconfigure(errors="replace")
    page_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PAGE
    results = []

    # detail is always printed, hint only when the check fails
    def check(name, ok, detail="", hint=""):
        results.append((name, bool(ok), detail, hint))

    html = fetch(page_url)

    # --- the main path of the script: category data sits right in the HTML
    marker = "window.mapData = "
    start = html.find(marker)
    check("the HTML assigns window.mapData", start >= 0)
    map_data = None
    if start >= 0:
        try:
            map_data, _ = json.JSONDecoder().raw_decode(html, start + len(marker))
        except ValueError as error:
            check("window.mapData parses as JSON", False, hint=str(error))
    if map_data is not None:
        categories = map_data.get("categories")
        check(
            "mapData.categories is an object keyed by category id",
            isinstance(categories, dict) and categories and all(k.isdigit() for k in categories),
            f"{len(categories)} categories" if isinstance(categories, dict) else type(categories).__name__,
        )
        if isinstance(categories, dict) and categories:
            check(
                "every category has a boolean field visible",
                all(isinstance(c.get("visible"), bool) for c in categories.values()),
            )
        check(
            "mapData.map.id is there (the script's storage key)",
            isinstance(map_data.get("map"), dict) and "id" in map_data["map"],
            str((map_data.get("map") or {}).get("id")),
        )

    # window.game is assigned in the same block but AFTER mapData - which is why the script checks
    # the site's own checkbox when the store appears, not inside the trap.
    game_at = html.find("window.game = ")
    check("window.game is assigned after window.mapData", 0 <= start < game_at)

    bundle = re.search(r'<script src="(https://cdn\.mapgenie\.io/js/map\.js\?id=[0-9a-f]+)"', html)
    check("the HTML links map.js", bundle is not None)
    if bundle is None:
        return report(results, None)
    js = fetch(bundle.group(1))

    # --- the fallback path: the Redux action and its shape
    check(
        'the action "MG:MAP:SET_CATEGORIES_VISIBILITY" exists',
        '"MG:MAP:SET_CATEGORIES_VISIBILITY"' in js,
        hint="look for its replacement: grep -o '\"MG:MAP:[A-Z_]*\"' map.js | sort -u",
    )
    check("its payload is meta.visibilities", "meta:{visibilities:" in js and "t.meta.visibilities" in js)
    check("the store is put into window.store", re.search(r"window\.store\s*=", js) is not None)
    check(
        "the marker layer filter is computed from the store state",
        'key:"getVisibleCategoriesFilter"' in js and 'key:"setLocationsFilter"' in js,
    )

    # --- the conditions under which the script deliberately stays silent
    check(
        "the filtered-link parameters are the same",
        all(f'get("{name}")' in js for name in DEEP_LINK_PARAMS),
        hint="gone: " + ", ".join(name for name in DEEP_LINK_PARAMS if f'get("{name}")' not in js),
    )
    check("search keeps its text in state.search.query", "getState().search.query" in js)
    check(
        "the key of the site's own checkbox is the same",
        '"mg:settings:game_".concat(window.game.id,":remember_categories")' in js,
    )

    # --- ads: what the script stops and what it hides
    script_hosts = {urlparse(src).hostname for src in re.findall(r'<script\b[^>]*\bsrc="([^"]+)"', html)}
    # Guard against an empty set: without it "no unknown hosts" would pass vacuously.
    check("<script src> tags are extracted from the HTML", "cdn.mapgenie.io" in script_hosts)
    found_ad_hosts = script_hosts & AD_SCRIPT_HOSTS
    check(
        "the ad loaders are tags in the HTML",
        found_ad_hosts == AD_SCRIPT_HOSTS,
        ", ".join(sorted(found_ad_hosts)),
        hint="only a tag that comes from the HTML can be stopped; if ads are now loaded from code another way is needed",
    )
    unknown_hosts = script_hosts - AD_SCRIPT_HOSTS - KNOWN_SCRIPT_HOSTS
    check(
        "no scripts from unknown hosts in the HTML",
        not unknown_hosts,
        hint="check whether these are ads: " + ", ".join(sorted(unknown_hosts)),
    )
    missing_ids = [name for name in AD_CONTAINER_IDS if f'id="{name}"' not in html]
    check("the ad placeholders in the markup are the same", not missing_ids, hint="gone: " + ", ".join(missing_ids))
    check(
        "map.js does not reference the ad stack",
        re.search(r"(?i)pogo|blobby|nitro-floating|zdconsent|googletag", js) is None,
        hint="the site now depends on the ad scripts - stopping them may break it",
    )
    check("the page creates the window.zdconsent queues itself", "window.zdconsent = window.zdconsent ||" in html)
    check("window.gtag is defined in the HTML, not by an ad script", "window.gtag = gtag" in html)
    app_css = re.search(r'href="(https://cdn\.mapgenie\.io/css/app\.css\?id=[0-9a-f]+)"', html)
    check("the HTML links app.css", app_css is not None)
    if app_css is not None:
        check(
            "the space reserved for ads is set by the same selector",
            "#left-sidebar.footer-large #categories" in fetch(app_css.group(1)),
            hint="the script gives the category list its 275-300 px back through exactly this selector",
        )

    # --- for information: not a condition for the script to work, but the reason it exists
    pro_only = "hasPro" in js and "renderRememberSelectionCheckbox" in js and "renderNeedsUpgrade" in js
    results.append(('INFO: "Remember Selected Categories" is still a PRO-only feature', pro_only, "", ""))

    return report(results, bundle.group(1))


def report(results, bundle_url):
    if bundle_url:
        print(f"bundle: {bundle_url}\n")
    failed = 0
    for name, ok, detail, hint in results:
        informational = name.startswith("INFO")
        if not ok and not informational:
            failed += 1
        mark = "OK  " if ok else ("NO  " if informational else "FAIL")
        notes = [text for text in (detail, "" if ok else hint) if text]
        print(f"{mark}  {name}" + (f"  [{'; '.join(notes)}]" if notes else ""))
    print()
    if failed:
        print(f"checks failed: {failed} - the site has changed, see docs/how-it-works.md, \"When it stops working\"")
        return 1
    print("the site is built the way the userscript expects")
    return 0


if __name__ == "__main__":
    sys.exit(main())
