// ==UserScript==
// @name            MapGenie Tweaks: remember categories, remove ads
// @name:ru         MapGenie: помнить категории, убрать рекламу
// @namespace       https://github.com/svareyko/game-fixes
// @version         1.2.0
// @description     Two tweaks for every mapgenie.io map: (1) remembers which marker categories you switched on, separately for each map; (2) removes ads - stops the ad loaders before they start and removes their placeholders.
// @description:ru  Две правки для любых карт mapgenie.io: (1) запоминает, какие категории меток включены, отдельно для каждой карты; (2) убирает рекламу — не даёт запуститься рекламным загрузчикам и убирает их места в разметке.
// @author          bombuilder.by
// @license         MIT
// @homepageURL     https://github.com/svareyko/game-fixes/tree/HEAD/mapgenie
// @supportURL      https://github.com/svareyko/game-fixes/issues
// @updateURL       https://github.com/svareyko/game-fixes/raw/HEAD/mapgenie/mapgenie-tweaks.user.js
// @downloadURL     https://github.com/svareyko/game-fixes/raw/HEAD/mapgenie/mapgenie-tweaks.user.js
// @match           https://mapgenie.io/*/maps/*
// @run-at          document-start
// @noframes
// @grant           GM_getValue
// @grant           GM_setValue
// @grant           GM_deleteValue
// @grant           GM_registerMenuCommand
// @grant           GM_addStyle
// @grant           unsafeWindow
// ==/UserScript==

// How it works and why it is built this way: docs/how-it-works.md next to this file.

(function () {
  'use strict';

  // Switches for troubleshooting: if something on the site breaks, turn one half off and compare.
  const FEATURES = { removeAds: true, rememberCategories: true };

  // We need the page's own objects (mapData, store), not the userscript manager's sandbox.
  const page = typeof unsafeWindow !== 'undefined' ? unsafeWindow : window;

  const TAG = '[mapgenie-tweaks]';

  // ================================================================ ads
  //
  // Ads on the page come from three Ziff Davis loaders, all of them <script async> tags in <head>:
  //   cdn.ziffstatic.com/pg/mapgenie.js     "pogo": prebid, Google GPT, the video player, banners
  //   cdn.ziffstatic.com/jst/zdconsent.js   cookie consent; also carries the Admiral loader and ad-block tracking
  //   cdn.static.zdbb.net/js/....min.js     audience tracking; its feature list includes "AdBlock Proxy"
  // The map's own code (map.js) never references them, and the page creates the window.zdconsent
  // queues itself, so the site works as usual without these scripts.
  const AD_SCRIPT_HOSTS = ['cdn.ziffstatic.com', 'cdn.static.zdbb.net'];

  // Ad placeholders in the site's markup:
  //   #blobby-left             footer of the left panel: a banner and "Ad Blocker? Consider an upgrade" below it
  //   #nitro-floating-wrapper  the video player pogo puts over the bottom of the panel
  //   #blobby-overlay          sticky banner on phones
  //   div[data-pogo]           everything pogo marks up for ads by itself
  const AD_CONTAINERS = '#blobby-left, #blobby-overlay, #nitro-floating-wrapper, div[data-pogo]';

  // The site reserves 275-300 px at the bottom of the category list for that footer - give them back.
  const AD_CSS = `
    ${AD_CONTAINERS} { display: none !important; }
    #left-sidebar.footer-large #categories,
    #left-sidebar.footer-large #search-results-wrapper { padding-bottom: 20px !important; }
  `;

  function addStyle(css) {
    if (typeof GM_addStyle === 'function') {
      GM_addStyle(css);
      return;
    }
    const style = document.createElement('style');
    style.textContent = css;
    (document.head || document.documentElement).appendChild(style);
  }

  function setupAdRemoval() {
    if (page.__mapgenieNoAds) return;
    page.__mapgenieNoAds = true;

    addStyle(AD_CSS);

    const isAdScript = (node) => {
      if (!node || node.nodeName !== 'SCRIPT' || !node.src) return false;
      try {
        return AD_SCRIPT_HOSTS.includes(new URL(node.src, document.baseURI).hostname);
      } catch (error) {
        return false;
      }
    };

    // Ad tags already in the document mean the manager injected us late and they cannot be stopped.
    // Then only the styles and the removal of the placeholders do the work.
    const late = Array.from(document.scripts).some(isAdScript);
    const blocked = new Set();

    // The parser inserts a <script> into the document at its start tag and prepares it to run at
    // its end tag, and observers fire in between (HTML Standard, "prepare the script element").
    // An unknown type at that moment means the script never runs. This works only for tags that
    // come from the HTML: a script inserted from code has its type read at once, before observers.
    // That is enough here - everything else (prebid, GPT, Admiral) is pulled in by these three loaders.
    const observer = new MutationObserver((records) => {
      for (const record of records) {
        for (const node of record.addedNodes) {
          if (isAdScript(node)) {
            blocked.add(node.src);
            node.type = 'javascript/blocked';
            node.remove();
          }
        }
      }
    });
    observer.observe(document, { childList: true, subtree: true });

    // In Firefox changing the type does not always work, but the run can be cancelled with an event.
    // Chrome has no such event, so the handler simply never fires there.
    document.addEventListener(
      'beforescriptexecute',
      (event) => {
        if (isAdScript(event.target)) {
          blocked.add(event.target.src);
          event.preventDefault();
        }
      },
      true
    );

    const finish = () => {
      observer.disconnect();
      // A hidden video player would keep playing - so the placeholders are removed, not just hidden.
      document.querySelectorAll(AD_CONTAINERS).forEach((element) => element.remove());
      if (late) {
        console.info(TAG, 'ads: the ad loaders had started before this script - their placeholders are hidden and removed, but the loaders keep running in the background');
      } else {
        console.info(TAG, `ads: stopped ${blocked.size} ad loaders, removed the ad placeholders`);
      }
    };
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', finish, { once: true });
    else finish();
  }

  // ================================================================ categories
  //
  // Category visibility is the `visible` field of the objects in window.mapData.categories. The page
  // ships them inside the HTML, and map.js later builds the initial state of its Redux store
  // (window.store) from them. So the main path is to fix `visible` BEFORE map.js reads it: the map
  // is drawn with the right selection at once, without a flash and without touching site internals.
  // If the userscript manager injected us too late, the fallback path goes through dispatch.

  const SAVE_DELAY_MS = 400;
  const STORE_POLL_MS = 200;
  const STORE_TIMEOUT_MS = 120000;

  // The only name from the site's internals this script depends on, and only on the fallback path.
  // The site has renamed its actions before (it used to be HIVE:MAP:...). To find it again:
  //   grep -o '"MG:MAP:[A-Z_]*VISIBILITY"' map.js
  const SET_VISIBILITY_ACTION = 'MG:MAP:SET_CATEGORIES_VISIBILITY';

  // With these URL parameters the site shows a filtered view by itself (parseQueryParams in map.js)
  // and immediately strips them from the address via history.replaceState - so read the address now.
  const DEEP_LINK_PARAMS = ['locationIds', 'catIds', 'groups', 'regions', 'tags', 'route'];
  const openedByDeepLink = (() => {
    const params = new URLSearchParams(page.location.search);
    return DEEP_LINK_PARAMS.some((name) => params.get(name));
  })();

  // ---------------------------------------------------------------- storage

  // The userscript manager's storage survives "clear site data"; localStorage is the fallback.
  const useGM =
    typeof GM_getValue === 'function' &&
    typeof GM_setValue === 'function' &&
    typeof GM_deleteValue === 'function';

  // The prefix dates from version 1.0.0, when this was all the script did: changing it loses saved data.
  const storageKey = (mapId) => `mapgenie-remember:map_${mapId}`;

  function loadSaved(mapId) {
    try {
      const raw = useGM ? GM_getValue(storageKey(mapId), null) : localStorage.getItem(storageKey(mapId));
      const parsed = raw ? JSON.parse(raw) : null;
      return parsed && typeof parsed === 'object' ? parsed : null;
    } catch (error) {
      console.warn(TAG, 'could not read the saved selection', error);
      return null;
    }
  }

  function writeSaved(mapId, visibility) {
    try {
      const raw = JSON.stringify(visibility);
      if (useGM) GM_setValue(storageKey(mapId), raw);
      else localStorage.setItem(storageKey(mapId), raw);
    } catch (error) {
      console.warn(TAG, 'could not save the selection', error);
    }
  }

  function forgetSaved(mapId) {
    try {
      if (useGM) GM_deleteValue(storageKey(mapId));
      else localStorage.removeItem(storageKey(mapId));
    } catch (error) {
      console.warn(TAG, 'could not delete the saved selection', error);
    }
  }

  // ---------------------------------------------------------------- conditions

  // A link to specific markers / a region / a route, or to somebody's shared note: the site shows a
  // reduced view. That is not the user's choice - such a session is neither restored nor saved.
  function isFilteredView(mapData) {
    return (
      openedByDeepLink ||
      !!page.visibleLocations ||
      !!page.visibleCategories ||
      Object.keys((mapData && mapData.sharedNotes) || {}).length > 0
    );
  }

  // The site has the same feature of its own (the "Remember Selected Categories" checkbox, PRO only).
  // If it is on, two keepers of one state would fight - so we step aside.
  function siteRemembersItself() {
    try {
      return !!(page.game && localStorage.getItem(`mg:settings:game_${page.game.id}:remember_categories`));
    } catch (error) {
      return false;
    }
  }

  // ---------------------------------------------------------------- restoring

  // Main path: fix the data before map.js builds its state from it.
  function restoreIntoMapData(mapData) {
    if (!mapData || !mapData.map || !mapData.categories) return;
    if (isFilteredView(mapData)) return;
    const saved = loadSaved(mapData.map.id);
    if (!saved) return;

    let restored = 0;
    for (const id of Object.keys(mapData.categories)) {
      // Categories that did not exist when the selection was saved stay the way the site wants them.
      if (typeof saved[id] === 'boolean') {
        mapData.categories[id].visible = saved[id];
        restored += 1;
      }
    }
    console.info(TAG, `categories restored before the map loaded (${restored})`);
  }

  // Catch the assignment window.mapData = {...} made by the page's HTML. After the first assignment
  // the property becomes an ordinary one again, so the page lives on as if we were not here.
  function trapMapData() {
    let current;
    Object.defineProperty(page, 'mapData', {
      configurable: true,
      enumerable: true,
      get() {
        return current;
      },
      set(value) {
        current = value;
        Object.defineProperty(page, 'mapData', {
          configurable: true,
          enumerable: true,
          writable: true,
          value,
        });
        try {
          restoreIntoMapData(value);
        } catch (error) {
          console.warn(TAG, 'restoring failed, the map will load with the default selection', error);
        }
      },
    });
  }

  // Fallback path, and a safety net for the main one: the store exists, compare it with what is saved.
  // The site's own middleware recalculates the marker layer filter on this action (setLocationsFilter).
  function restoreViaDispatch(store, saved) {
    const categories = store.getState().map.categories;
    const diff = {};
    for (const id of Object.keys(categories)) {
      if (typeof saved[id] === 'boolean' && categories[id].visible !== saved[id]) diff[id] = saved[id];
    }
    const ids = Object.keys(diff);
    if (ids.length === 0) return;

    store.dispatch({ type: SET_VISIBILITY_ACTION, meta: { visibilities: diff } });

    const after = store.getState().map.categories;
    const failed = ids.filter((id) => after[id].visible !== diff[id]);
    if (failed.length > 0) {
      console.warn(
        TAG,
        `the site ignored the action ${SET_VISIBILITY_ACTION} - it has probably been renamed;`,
        'docs/how-it-works.md explains how to find the new name. Categories not restored:',
        failed
      );
    } else {
      console.info(TAG, `categories restored after the map loaded (${ids.length})`);
    }
  }

  // ---------------------------------------------------------------- saving

  function snapshot(state) {
    const result = {};
    for (const id of Object.keys(state.map.categories).sort()) {
      result[id] = !!state.map.categories[id].visible;
    }
    return result;
  }

  function watchStore(store, mapId) {
    let suspended = false;
    let timer = null;
    // Until the user changes something, nothing is written: the site's defaults must not freeze here.
    let lastWritten = JSON.stringify(snapshot(store.getState()));

    function saveNow() {
      timer = null;
      if (suspended) return;
      const state = store.getState();
      // Search hides every category and brings them back when the box is cleared. Do not store the in-between.
      if (state.search && state.search.query) return;
      const current = snapshot(state);
      const serialized = JSON.stringify(current);
      if (serialized === lastWritten) return;
      lastWritten = serialized;
      writeSaved(mapId, current);
    }

    // The delay is not about saving effort: the site changes categories in bursts of actions (search,
    // "Hide All" followed by a click), and what must be stored is where the burst ended.
    store.subscribe(() => {
      if (timer !== null) clearTimeout(timer);
      timer = setTimeout(saveNow, SAVE_DELAY_MS);
    });

    page.addEventListener('pagehide', () => {
      if (timer !== null) {
        clearTimeout(timer);
        saveNow();
      }
    });

    if (typeof GM_registerMenuCommand === 'function') {
      const russian = (page.navigator.language || '').toLowerCase().startsWith('ru');
      const label = russian ? 'Забыть выбор категорий для этой карты' : 'Forget the saved categories for this map';
      GM_registerMenuCommand(label, () => {
        suspended = true;
        forgetSaved(mapId);
        page.location.reload();
      });
    }
  }

  // ---------------------------------------------------------------- start

  function onStoreReady(store) {
    const mapData = page.mapData;
    if (!mapData || !mapData.map) {
      console.warn(TAG, 'window.mapData.map is missing - the page is built differently than expected; categories are not remembered');
      return;
    }
    if (siteRemembersItself()) {
      console.info(TAG, "the site's own \"Remember Selected Categories\" is on - categories are left to it");
      return;
    }
    if (isFilteredView(mapData)) {
      console.info(TAG, 'the map was opened by a link with a filter - the selection is neither restored nor saved');
      return;
    }
    const saved = loadSaved(mapData.map.id);
    if (saved) restoreViaDispatch(store, saved);
    watchStore(store, mapData.map.id);
  }

  function waitForStore() {
    const startedAt = Date.now();
    const poll = setInterval(() => {
      const store = page.store;
      if (store && typeof store.getState === 'function' && store.getState().map) {
        clearInterval(poll);
        try {
          onStoreReady(store);
        } catch (error) {
          console.warn(TAG, "could not attach to the site's store", error);
        }
      } else if (Date.now() - startedAt > STORE_TIMEOUT_MS) {
        clearInterval(poll);
        console.warn(TAG, 'window.store never appeared - the map did not load or the site was rebuilt');
      }
    }, STORE_POLL_MS);
  }

  function setupRememberCategories() {
    // The flag name is the one version 1.0.0 used: if an old copy is still installed next to this
    // one, only one of the two takes care of categories.
    if (page.__mapgenieRememberCategories) return;
    page.__mapgenieRememberCategories = true;

    if (!page.store) {
      if (page.mapData) restoreIntoMapData(page.mapData);
      else trapMapData();
    }
    waitForStore();
  }

  // The halves are independent: a failure in one must not switch the other off.
  function run(name, setup) {
    try {
      setup();
    } catch (error) {
      console.warn(TAG, `the "${name}" part failed, the rest keeps working`, error);
    }
  }

  // Ads first: there it is a race against the tags in <head>; categories are in no hurry.
  if (FEATURES.removeAds) run('ads', setupAdRemoval);
  if (FEATURES.rememberCategories) run('categories', setupRememberCategories);
})();
