# MapGenie Tweaks — remember your categories, no ads

A userscript for the interactive maps on **mapgenie.io**. It does two things, on every map of
every game:

1. **Remembers which marker categories you switched on** — separately for each map. Reload the
   page, restart the browser: the map opens the way you left it.
2. **Removes the ads** — the video player and the banner that cover the bottom of the category
   list are gone, and the list gets its full height back.

*MapGenie · mapgenie.io · interactive map · remember selected categories · categories reset after
reload · map forgets filters · remove ads · video player over the sidebar · Tampermonkey ·
userscript · S.T.A.L.K.E.R. 2 map · Elden Ring map · any MapGenie map*

[Русская версия](README.ru.md) · [How it works](docs/how-it-works.md)

## **[➜ Install MapGenie Tweaks](https://github.com/svareyko/game-fixes/raw/HEAD/mapgenie/mapgenie-tweaks.user.js)**

The link works once Tampermonkey is installed — three steps, see [Install](#install).

---

## Is this what annoys you?

- [ ] You hide the categories you do not need, reload the page — and **everything is visible again**.
- [ ] You registered on the site hoping it would remember your choice — **it did not help**.
- [ ] A **video player and a banner sit on top of the category list**, so you scroll a tiny window.

Registration was never going to help: on MapGenie "Remember Selected Categories" is a checkbox
in *Settings* that exists only for PRO accounts. A free account saves found markers, not filters.

## What you get

| | Without the script | With it |
|---|---|---|
| Categories after a reload | reset to the site's defaults | exactly as you left them, per map |
| Bottom of the left panel | video player + 300×250 banner | your category list, full height |
| Requests to ad networks | hundreds, and they keep refreshing | none of the ad loaders start |
| The map itself | — | untouched: markers, search, progress tracking work as before |

The category memory is smart about what *not* to remember:

- You opened a **shared link** to specific markers, a region or a route — the site shows a reduced
  view on purpose. The script neither restores over it nor saves it.
- You are **searching** — the site hides all categories while a search is active. That is not saved either.
- You have **PRO and the site's own checkbox is on** — the script steps aside and leaves categories to the site.

## What you need

- A desktop browser: Chrome, Edge, Firefox or anything else that runs Tampermonkey.
- The [Tampermonkey](https://www.tampermonkey.net/) extension (free). Violentmonkey works too.

## Install

1. **Install Tampermonkey.** Open <https://www.tampermonkey.net/>, pick your browser, press the
   install button of your browser's extension store.
2. **Chrome, Edge and other Chromium browsers only — allow user scripts.** Right-click the
   Tampermonkey icon, choose **Manage extension** and switch on **Allow User Scripts**. In browser
   versions older than 138 there is no such switch: open `chrome://extensions` (or
   `edge://extensions`) and turn on **Developer mode** in the top right corner instead. Without
   this Tampermonkey installs fine but never runs any script — the number one reason for
   "I installed it and nothing happens"
   ([Tampermonkey FAQ, Q209](https://www.tampermonkey.net/faq.php?q=Q209), with pictures).
3. **Click [➜ Install MapGenie Tweaks](https://github.com/svareyko/game-fixes/raw/HEAD/mapgenie/mapgenie-tweaks.user.js).**
   Tampermonkey opens a page with the script's name and a big **Install** button. Press it.
4. Open any MapGenie map, choose your categories, press **F5**. They stay. The ads are gone.

Updates arrive by themselves: Tampermonkey checks this repository for a newer version.

### How to be sure it works

Normally you just see it: categories survive a reload and the left panel has no video. If you want
proof, press **F12**, open the **Console** tab and reload the map. Lines that start with
`[mapgenie-tweaks]`:

| Line | Meaning |
|---|---|
| `ads: stopped 3 ad loaders, removed the ad placeholders` | normal |
| `categories restored before the map loaded (N)` | normal |
| `ads: the ad loaders had started before this script…` | Tampermonkey injected the script late. You still see no ads, but their code runs in the background — see the [FAQ](#faq) |
| `categories restored after the map loaded (N)` | same late injection: the result is identical, all markers just flash for a moment first |
| no `[mapgenie-tweaks]` lines at all | the script is not running — go back to step 2 |

## Reset, switch off, uninstall

- **Forget the saved categories of one map:** open that map, click the Tampermonkey icon, choose
  *Forget the saved categories for this map*. The page reloads with the site's defaults.
- **Switch off one half:** open the script in the Tampermonkey editor and change `removeAds` or
  `rememberCategories` to `false` in the `FEATURES` line near the top.
- **Uninstall:** Tampermonkey icon → *Dashboard* → the trash can next to the script. Nothing is left
  behind: the script writes nothing to the site, to your MapGenie account or to disk — its few
  bytes of settings live inside Tampermonkey and go away with it.

## What it deliberately does not do

**It does not pretend to be PRO.** The easy way would have been to flip the site's own
"remember" flag in the browser's storage and let the site's paid code do the work. This script
does not touch it: it keeps its own copy of your selection and applies it itself, and it removes
ads the way any ad blocker does — by not running third-party scripts and by hiding page elements.
It never talks to MapGenie's servers or your account, and it gets no data a free visitor does not
already receive. Everything else PRO offers (profiles, unlimited progress tracking, shared
markers) is left alone.

It also leaves the site's visitor counters (Google Analytics, Chartbeat, Comscore) and its own
"upgrade to PRO" texts in place — those are not ads.

Ads are what keeps MapGenie free, and "no ads" plus "remember categories" is what PRO sells.
**If you like the site, buying PRO is the way to support it** — and then you do not need this script.

## FAQ

**Does it work for my game?** Yes. Every map under `mapgenie.io/<game>/maps/<map>` is built the
same way. It was developed on the S.T.A.L.K.E.R. 2 map.

**I already use an ad blocker.** Fine — then the ad half has nothing left to do, and the category
half is why you are here. They do not conflict.

**The console says the ad loaders had started before the script.** Tampermonkey was too slow to
inject the script before the page's `<head>`. Usually a one-off on the very first load after the
browser starts. If it happens every time, add a real ad blocker (uBlock Origin / uBlock Origin
Lite): a userscript cannot block network requests, it can only win or lose that race.

**Firefox?** The category half does not care about the browser. The ad half uses a second
mechanism in Firefox (`beforescriptexecute`) that has **not been tested** — please
[report](https://github.com/svareyko/game-fixes/issues) how it goes.

**Phones?** Only where a userscript manager exists (Firefox for Android, Kiwi). Not tested.

**The site was updated and the script stopped working.** Run `python check-site.py` from this
folder — it downloads the map page and tells you in plain words what changed — and open an
[issue](https://github.com/svareyko/game-fixes/issues) with its output.
[How it works](docs/how-it-works.md#when-it-stops-working) has the table of symptoms.

**Is anything sent anywhere?** No. No network requests, no analytics. Read the source: it is one
file with comments.

## Status

| What | State |
|---|---|
| Category memory, all three restore paths | verified on the live site, 2026-09-20; the marker layer filter equals the saved selection |
| Ad removal, injected early | verified on the live site, 2026-09-20: exactly three loaders stopped, 0 ad frames instead of 24, map fully working |
| Ad removal, injected late | verified on the live site, 2026-09-20: placeholders and video elements removed, map fully working |
| Daily use in Tampermonkey | in use since 2026-09-21 |
| Firefox, Violentmonkey, phones | **not tested** |

## Author

Made by **[bombuilder.by](https://bombuilder.by)**. MIT licensed — see [LICENSE](../LICENSE).

## Disclaimer

This is an unofficial, fan-made script. It is not affiliated with, endorsed by or connected to
MapGenie or Ziff Davis. "MapGenie" and all game titles are trademarks of their respective
owners. Use it at your own risk; a site's terms of service may not welcome userscripts.
