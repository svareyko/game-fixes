# MapGenie Tweaks — how it works

**Read this when:** you want to know why the map forgets categories, how the script restores them
and stops ads, or the script stopped working after a site update.
**Not this, for:** installing and using the script → [README](../README.md).
**Sections:** 1 Why the map forgets · 2 Categories · 3 Ads · 4 When it stops working ·
5 What the script deliberately does not do · 6 How it was verified

[Русская версия](how-it-works.ru.md)

Analysed on 2026-09-20 against `https://cdn.mapgenie.io/js/map.js?id=1f211aff87252400d31386494f0c40a2`
(1 201 123 bytes) and the S.T.A.L.K.E.R. 2 map (game id 203, map id 726, 40 categories). Every
MapGenie map uses the same page template and the same bundle.

## 1. Why the map forgets

Category selection is reset on **every** page load, not only after a browser restart. It is not
a bug: remembering is a paid feature.

| Fact | Where it shows |
|---|---|
| The "Remember Selected Categories" checkbox in *Settings* is rendered only when `window.user.hasPro` | `map.js`: `t=e&&e.hasPro … t?this.renderRememberSelectionCheckbox():this.renderNeedsUpgrade()` |
| Everybody else gets a locked checkbox with a PRO badge that links to the upgrade page | `renderNeedsUpgrade`, `pointerEvents:"none"`, `<sup class="pro-sup">PRO</sup>` |
| A free account offers something else: "Mark locations as found", "Track your collectibles", "Add custom locations" | right-hand panel, *Features* / *PRO Features* |
| The site keeps its own memory in the page's `localStorage` | keys `mg:settings:game_<id>:remember_categories` and `…:visible_categories:id_<catId>` |
| For a free visitor the site writes nothing about categories | a live page has no `mg:` keys in `localStorage` at all |

Visibility of a category is the `visible` field of the objects in `window.mapData.categories[<id>]`.
They arrive inside the page's HTML, and `map.js` later builds the initial state of its Redux store
`window.store` (`state.map.categories`) from them. The objects are **the very same ones**, not copies.

## 2. Categories

Three ways to restore, depending on how early the userscript manager injected the script. They are
tried in this order.

| Path | Condition | What happens | Depends on |
|---|---|---|---|
| main | `window.mapData` does not exist yet | a trap (`defineProperty` with a setter) on `window.mapData`; when the HTML assigns it, the script fixes `categories[id].visible` and removes the trap | only the shape of the data in the HTML |
| early fallback | `mapData` exists, `window.store` does not | fixes `visible` directly | the same |
| late fallback | `window.store` exists | `dispatch({type:"MG:MAP:SET_CATEGORIES_VISIBILITY", meta:{visibilities}})` for the differences only; then compares the state and warns in the console if the site ignored the action | the action name |

The window for the first two paths is wide: `map.js` creates the store only after the markers have
arrived over the network (`Promise.all` → `window.store=…`), hundreds of milliseconds after the HTML.

The late path always runs as a safety net: once the store is ready its state is compared with the
saved selection. After the main path there is no difference and nothing is dispatched. The site's
own middleware reacts to that action by recalculating the marker layer filter (`setLocationsFilter`),
so the map follows the state.

**Saving.** `store.subscribe` → after 400 ms of silence a snapshot `{id: visible}` of all categories
→ written if it differs from the last one written. The delay is essential, not an optimisation:
the site changes categories in bursts of actions, and what must be stored is where the burst
ended. Until the user changes something nothing is written, so the site's defaults never freeze
in the script's storage.

**Storage.** `GM_setValue` (the userscript manager's storage survives "clear site data"); without
GM functions, `localStorage`. Key `mapgenie-remember:map_<map id>`, value JSON. Categories that did
not exist when the selection was saved stay the way the site wants them.

**When this half deliberately stays silent:**

| Case | Behaviour | Why |
|---|---|---|
| A link with `locationIds`, `catIds`, `groups`, `regions`, `tags`, `route`, or a shared note | the whole session is neither restored nor saved | the site shows a reduced view itself; it is not the user's choice. The parameters are read at once — the site strips them from the address with `history.replaceState` |
| A search is active (`state.search.query` is not empty) | nothing is saved | search hides every category and brings them back when the box is cleared |
| The site's own checkbox is on (PRO) | nothing at all | two keepers of one state would fight. Checked when the store is ready: in the HTML `window.game` is assigned later than `mapData` |
| Parameters `x`, `y`, `zoom` | works as usual | that is only the camera position |

## 3. Ads

**What the ads consist of.** Everything ad-related on the page comes from Ziff Davis, the site's owner:

| What | Where | Role |
|---|---|---|
| `cdn.ziffstatic.com/pg/mapgenie.js` | `<script id="pogo" async>` in `<head>` | the "pogo" loader: pulls `mapgenie.prebid.js`, Google GPT, the video player (outstream/Primis), fills every `div[data-pogo]` |
| `cdn.ziffstatic.com/jst/zdconsent.js` | `<script id="zdconsent" async>` in `<head>` | cookie consent (OneTrust); also carries the Admiral loader (`_ZDCABADML`) and ad-block tracking: the `_pgabp` cookie and an `adblock` event to GA |
| `cdn.static.zdbb.net/js/<id>.min.js` | `<script async>` in `<head>` | audience tracking; its feature list includes "Ad Block Tracking", "AdBlock Proxy", "Header Bidding" |
| `#blobby-left` › `#blobby-left-inner[data-pogo="sidebar"]` | bottom of the left panel, `position:absolute; height:250px` | a 300×250 banner, below it the text "Ad Blocker? Consider an upgrade to PRO" and an upgrade button |
| `#nitro-floating-wrapper` | over the bottom of the left panel, 404×250, `z-index:10` | the video player; pogo itself tags it `data-pogo="outstream"` |
| `#blobby-overlay[data-pogo="sticky"]` | bottom of the screen, phones only | a sticky 320×50 banner |

**Why the loaders can be stopped.** The site does not depend on them, checked in the sources:
`map.js` contains no reference to `pogo`, `blobby`, `nitro`, `zdconsent` or `googletag`; the page
creates the queues `window.zdconsent = window.zdconsent || {run:[], cmd:[], …}` itself with an inline
script, so `zdconsent.analytics.push(…)` does not throw, it just never runs; `window.gtag` is defined
inline as well. The only thing that falls off is the Clarity analytics, which was waiting for consent.

**Two layers.**

| Layer | What it does | When it works |
|---|---|---|
| stopping the loaders | a `MutationObserver` on `document`; a `<script>` whose host is in `AD_SCRIPT_HOSTS` gets `type="javascript/blocked"` and is removed | only if the script was injected before the parser reached the tags in `<head>` (`@run-at document-start`) |
| styles and removal | `display:none !important` on `#blobby-left`, `#blobby-overlay`, `#nitro-floating-wrapper`, `div[data-pogo]`; on `DOMContentLoaded` those nodes are removed; the category list gets its padding back | always |

Why stopping works: the parser inserts a `<script>` into the document at its start tag and prepares
it to run at its end tag, and observers fire in between (HTML Standard, "prepare the script element" —
an unknown `type` means "do not run"). The trick works **only for tags that come from the HTML**: a
script inserted from code has its `type` read at once, before observers. That is enough here —
prebid, GPT and Admiral are pulled in by the three loaders, and without them nobody pulls.

Removal and not just `display:none`, because a hidden video player would keep playing.

Padding: the site reserves room for the footer with
`#left-sidebar.footer-large #categories { padding-bottom:275px }` and
`body.map.pogo #left-sidebar.footer-large #categories { padding-bottom:300px }` (`app.css`).
The script sets 20 px, which is what `#categories` has without the footer.

**What stays, and why.**

| What | Why it is left alone |
|---|---|
| 5 downloads that never run: the three loaders, `mapgenie.prebid.js`, `gpt.js` | the HTML has `<link rel="preload">` for them; a userscript cannot cancel a network download, only the execution |
| Google Analytics, Chartbeat, Comscore, the Google Ads conversion pixel | counters, not ads: they show nothing on the page |
| the "PRO Features" block in the right panel, PRO badges in the settings | the site's own offer, not an ad |
| the "Upgrade To Pro" button disappears together with `#blobby-left` | it is part of the ad footer; the PRO offer stays in the right panel |

**Firefox.** Changing `type` does not always work there, so a handler for the non-standard
`beforescriptexecute` event calls `preventDefault()`. Chrome has no such event. **Not tested.**

## 4. When it stops working

First the page console (F12), lines starting with `[mapgenie-tweaks]`, then:

```bash
python check-site.py
```

It downloads the map page, its `map.js` and `app.css` and checks every signature the script relies
on. It changes nothing.

| What you see | What it means | What to do |
|---|---|---|
| no `[mapgenie-tweaks]` lines at all | the script does not run | README, install step 2; is the script enabled; does the address match `@match` |
| "the ad loaders had started before this script" | the manager injects the script late | a real ad blocker (uBlock Origin / Lite): a userscript cannot replace network-level blocking |
| ads are back, the console says "stopped 0 ad loaders" | the site changed the loaders' hosts or now loads them from code | `check-site.py` shows it; new hosts go into `AD_SCRIPT_HOSTS` (in the script and in `check-site.py`) |
| ads are back in a new place | a new placeholder | find its `id` in the HTML, add it to `AD_CONTAINERS` (script) and `AD_CONTAINER_IDS` (`check-site.py`) |
| the map is broken, and works without the script | the site started to depend on the ad scripts | set `FEATURES.removeAds` to `false` to confirm; `check-site.py`: "map.js does not reference the ad stack" |
| "the site ignored the action …" | the site renamed the action (it has happened before: `HIVE:MAP:…` → `MG:MAP:…`) | `grep -o '"MG:MAP:[A-Z_]*"' map.js \| sort -u`, fix `SET_VISIBILITY_ACTION`. The main path does not depend on the name |
| "window.store never appeared" | the site no longer puts its store into `window.store` | look for `createStore` in the bundle and see where it goes now |
| `check-site.py`: no `window.mapData` or no `visible` | the shape of the data in the HTML changed | the main path is dead; work out again how the site builds its initial state (`initializeMapState` in the bundle) |
| categories are restored but the selection is not saved | the session was recognised as a filtered link, or a search is active | section 2, "when this half stays silent" |

To get the page for a manual look:

```bash
curl -sS -L -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36" -o page.html "https://mapgenie.io/stalker-2-heart-of-chornobyl/maps/the-zone"
```

The addresses of the bundle and the stylesheet are in `page.html`
(`<script src="https://cdn.mapgenie.io/js/map.js?id=…">`, `<link href="https://cdn.mapgenie.io/css/app.css?id=…">`);
the ad loaders download with the same `curl` plus `-e "https://mapgenie.io/"`. Everything is
minified into one line: read it with `grep -o '.\{300\}NEEDLE.\{400\}'`, not as a whole.

## 5. What the script deliberately does not do

**It does not pretend to be PRO.** The easiest way would have been to write the flag
`mg:settings:game_<id>:remember_categories=true` into `localStorage` — on load the site's code looks
only at that flag, not at `hasPro`, and would have done the rest itself. The script does not do
that: it would be faking a sign of payment to run somebody else's paid code. Both halves are
independent work on the browser's side: the script stores and restores categories by itself, and it
removes ads the way any ad blocker does — by not running third-party scripts and by hiding page
nodes. It never talks to the server or the account and receives nothing beyond what a free visitor
is already given. There are practical reasons too: that flag lives in `localStorage`, which is
wiped together with the site's data, and the settings checkbox would still show "locked".

The rest of PRO (profiles, unlimited progress tracking, shared markers) is not touched.

Ads are what MapGenie lives on, and "No more ads" plus "Remember Selected Categories" is what it
sells. Supporting the site means buying PRO; the category half then steps aside for the site's own
checkbox by itself.

## 6. How it was verified

On the live site in a Chromium browser, without an account, 2026-09-20. "Fresh load" means the
same map loaded in a same-origin frame into which the script was injected at `readyState=loading`,
when the document held a single `<script>` and no ad tag yet — equivalent to `document-start`.

| What | How | Result |
|---|---|---|
| Saving categories | script injected into a loaded page, clicks on "Hide All" plus three categories, storage read back | exactly those three were written |
| Categories, main path | fresh load | the trap fired; the store started with the three categories, no dispatch needed; the filter of the layers `locations` and `location-circles` was `["in",["get","category_id"],["literal",[11895,11904,11920]]]` |
| Categories, early fallback | injected after `mapData`, before `store` | store and sidebar started with the three categories, no dispatch needed |
| Categories, late fallback | injected into a fully loaded page | a dispatch for the differences; layer filter and sidebar updated |
| Category logic as a whole | Node: the script in a `vm` against the page's real inline script and a fake store — filtered links, search, the site's checkbox, a renamed action | 28 checks pass |
| Stopping the loaders | fresh load | exactly three stopped: `zdconsent.js`, `pg/mapgenie.js`, `zdbb…min.js`; none of the globals `Pogo`, `googletag`, `pbjs`, `apstag`, `admiral`, `OneTrust`, `__ZD_USEG_`; `window.zdconsent` is an untouched queue; 0 frames against 24 on an ordinary page; 79 requests a minute after load, of which only the 5 preloads went to ad hosts |
| The site without the loaders | the same run | store ready, categories restored before load, layer filter = three categories, **584 markers rendered**, sidebar at full height |
| Layout | the same run | 0 ad placeholders in the document; `padding-bottom` of the list 20 px (275 px on an ordinary page) |
| Ads, late injection | script injected into a page where ads were already running | placeholders 4 → 0, `<video>` 4 → 0, padding 275 → 20 px, map alive (584 markers); the console honestly says the loaders had started; frames 23 → 19, the rest being invisible service frames |
| Independence of the halves | Node without a DOM: the ad half throws | a console warning, the category trap is installed anyway |

An ordinary page that had been open for some tens of minutes showed 2994 requests, 2771 of them to
43 ad and tracking hosts — ads keep refreshing; that number is not directly comparable with the 79.

Not verified: Firefox, Violentmonkey, phones.
