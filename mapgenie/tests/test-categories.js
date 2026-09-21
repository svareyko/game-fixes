// Logic test for the category half of mapgenie-tweaks.user.js.
//
//     node tests/test-categories.js [path/to/saved-map-page.html]
//
// Runs the userscript in a vm against the REAL inline <script> of a MapGenie map page (downloaded
// with curl unless a saved page is given) and a fake Redux-like store that shares
// mapData.categories the way map.js does. The ad half needs a real DOM and is not covered here.
const fs = require('fs');
const os = require('os');
const vm = require('vm');
const path = require('path');
const { execFileSync } = require('child_process');

const PAGE_URL = 'https://mapgenie.io/stalker-2-heart-of-chornobyl/maps/the-zone';
const USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36';

const USERSCRIPT = fs.readFileSync(path.join(__dirname, '..', 'mapgenie-tweaks.user.js'), 'utf8')
  .replace('removeAds: true', 'removeAds: false');
if (!USERSCRIPT.includes('removeAds: false')) throw new Error('feature switch not found');

function loadPage() {
  if (process.argv[2]) return fs.readFileSync(process.argv[2], 'utf8');
  const target = path.join(os.tmpdir(), 'mapgenie-test-page.html');
  execFileSync('curl', ['-sS', '-L', '--fail', '-A', USER_AGENT, '-o', target, PAGE_URL]);
  return fs.readFileSync(target, 'utf8');
}
const html = loadPage();

// the inline block that assigns window.mapData / window.game / window.config
const inline = [...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)]
  .map((m) => m[1])
  .find((code) => code.includes('window.mapData = '));
if (!inline) throw new Error('inline mapData script not found');

const KEY = 'mapgenie-remember:map_726';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let failures = 0;
function check(name, cond, extra) {
  if (!cond) failures += 1;
  console.log(`${cond ? 'PASS' : 'FAIL'}  ${name}${extra !== undefined ? '  -> ' + JSON.stringify(extra) : ''}`);
}

function makePage({ search = '', storage = {} } = {}) {
  const data = new Map(Object.entries(storage));
  const listeners = {};
  const logs = [];
  const sandbox = {
    console: {
      info: (...a) => logs.push(['info', a.join(' ')]),
      warn: (...a) => logs.push(['warn', a.map(String).join(' ')]),
      log: () => {},
      error: (...a) => logs.push(['error', a.map(String).join(' ')]),
    },
    URLSearchParams,
    setTimeout, clearTimeout, setInterval, clearInterval,
    JSON, Object, Date,
    location: { search, reload() { sandbox.__reloaded = true; } },
    localStorage: {
      getItem: (k) => (data.has(k) ? data.get(k) : null),
      setItem: (k, v) => data.set(k, String(v)),
      removeItem: (k) => data.delete(k),
    },
    addEventListener: (type, fn) => { (listeners[type] = listeners[type] || []).push(fn); },
    document: { getElementById: () => null, addEventListener() {}, createElement: () => ({ style: {} }), cookie: '' },
    navigator: { userAgent: 'node' },
  };
  sandbox.window = sandbox;
  sandbox.self = sandbox;
  const ctx = vm.createContext(sandbox);
  return { ctx, sandbox, data, listeners, logs };
}

// Mirrors what map.js does: state.map.categories IS window.mapData.categories (same objects),
// reducers mutate category objects in place and replace the container.
function installFakeStore(sandbox) {
  const subs = [];
  const dispatched = [];
  let state = { map: { categories: sandbox.mapData.categories }, search: { query: null } };
  const store = {
    getState: () => state,
    subscribe: (fn) => { subs.push(fn); },
    dispatch(action) {
      dispatched.push(action);
      const cats = state.map.categories;
      if (action.type === 'MG:MAP:SET_CATEGORIES_VISIBILITY') {
        for (const [id, v] of Object.entries(action.meta.visibilities)) if (cats[id]) cats[id].visible = v;
      } else if (action.type === 'MG:MAP:TOGGLE_CATEGORY') {
        cats[action.meta.categoryId].visible = !cats[action.meta.categoryId].visible;
      } else if (action.type === 'MG:MAP:TOGGLE_CATEGORIES') {
        for (const id of action.meta.categoryIds) cats[id].visible = !cats[id].visible;
      } else if (action.type === 'MG:MAP:HIDE_ALL_CATEGORIES') {
        for (const c of Object.values(cats)) c.visible = false;
      } else if (action.type === 'MG:SEARCH:SET_QUERY') {
        state = { ...state, search: { query: action.meta.query } };
      }
      state = { ...state, map: { ...state.map, categories: { ...cats } } };
      subs.forEach((fn) => fn());
      return action;
    },
  };
  sandbox.store = store;
  return { store, dispatched };
}

const visibleIds = (sandbox) =>
  Object.values(sandbox.mapData.categories).filter((c) => c.visible).map((c) => c.id).sort();

(async () => {
  // ---------- A: primary path, script runs before the inline script
  {
    const saved = { 11897: false, 11896: false, 11902: false, 999999: true };
    const { ctx, sandbox, data, logs } = makePage({ storage: { [KEY]: JSON.stringify(saved) } });
    vm.runInContext(USERSCRIPT, ctx);
    const trap = Object.getOwnPropertyDescriptor(sandbox, 'mapData');
    check('A1 trap installed as accessor', !!(trap && trap.set && trap.get));
    vm.runInContext(inline, ctx);
    const desc = Object.getOwnPropertyDescriptor(sandbox, 'mapData');
    check('A2 trap removed after first assignment', !!(desc && 'value' in desc && desc.writable));
    const cats = sandbox.mapData.categories;
    check('A3 categories is an object keyed by id', !Array.isArray(cats) && !!cats[11897]);
    check('A4 saved hidden categories are hidden', !cats[11897].visible && !cats[11896].visible && !cats[11902].visible);
    check('A5 everything else untouched', visibleIds(sandbox).length === Object.keys(cats).length - 3, visibleIds(sandbox).length);
    check('A6 window.game assigned by the same inline block', sandbox.game && sandbox.game.id === 203);

    const { store, dispatched } = installFakeStore(sandbox);
    await sleep(350);
    check('A7 no dispatch needed when state already matches', dispatched.length === 0);
    const before = data.get(KEY);
    await sleep(500);
    check('A8 nothing rewritten while user has not changed anything', data.get(KEY) === before);

    store.dispatch({ type: 'MG:MAP:TOGGLE_CATEGORY', meta: { categoryId: 11893 } });
    await sleep(600);
    const afterToggle = JSON.parse(data.get(KEY));
    check('A9 user toggle is saved', afterToggle[11893] === false && afterToggle[11897] === false && afterToggle[11895] === true);
    check('A10 snapshot covers all categories', Object.keys(afterToggle).length === Object.keys(cats).length, Object.keys(afterToggle).length);

    // search: previous categories remembered by the site, hide all, query set; later restored
    const prev = visibleIds(sandbox);
    store.dispatch({ type: 'MG:MAP:HIDE_ALL_CATEGORIES' });
    store.dispatch({ type: 'MG:SEARCH:SET_QUERY', meta: { query: 'stash' } });
    await sleep(600);
    check('A11 search does not overwrite the saved choice', data.get(KEY) === JSON.stringify(afterToggle));
    store.dispatch({ type: 'MG:SEARCH:SET_QUERY', meta: { query: null } });
    store.dispatch({ type: 'MG:MAP:TOGGLE_CATEGORIES', meta: { categoryIds: prev } });
    await sleep(600);
    check('A12 state after search equals saved choice', data.get(KEY) === JSON.stringify(afterToggle));
    check('A13 no warnings', logs.filter((l) => l[0] !== 'info').length === 0, logs);
  }

  // ---------- B: late path, store already exists when the script starts
  {
    const { ctx, sandbox, data, logs } = makePage();
    vm.runInContext(inline, ctx);
    const all = Object.keys(sandbox.mapData.categories);
    const saved = Object.fromEntries(all.map((id) => [id, id === '11895' || id === '11904']));
    data.set(KEY, JSON.stringify(saved));
    const { dispatched } = installFakeStore(sandbox);
    vm.runInContext(USERSCRIPT, ctx);
    check('B1 no trap when store already exists', 'value' in Object.getOwnPropertyDescriptor(sandbox, 'mapData'));
    await sleep(350);
    check('B2 exactly one restore dispatch', dispatched.length === 1 && dispatched[0].type === 'MG:MAP:SET_CATEGORIES_VISIBILITY');
    check('B3 diff only, 38 of 40 categories', Object.keys(dispatched[0].meta.visibilities).length === all.length - 2);
    check('B4 state matches saved', JSON.stringify(visibleIds(sandbox)) === JSON.stringify([11895, 11904]), visibleIds(sandbox));
    await sleep(600);
    check('B5 restore itself is not re-saved differently', data.get(KEY) === JSON.stringify(saved));
    check('B6 no warnings', logs.filter((l) => l[0] !== 'info').length === 0, logs);
  }

  // ---------- B': mapData exists, store does not yet (injected between inline script and bundle)
  {
    const { ctx, sandbox, data } = makePage({ storage: { [KEY]: JSON.stringify({ 11897: false }) } });
    vm.runInContext(inline, ctx);
    vm.runInContext(USERSCRIPT, ctx);
    check("B'1 direct patch without trap", sandbox.mapData.categories[11897].visible === false);
    const { dispatched } = installFakeStore(sandbox);
    await sleep(350);
    check("B'2 no dispatch needed", dispatched.length === 0);
  }

  // ---------- C: deep link -> neither restore nor save
  {
    const { ctx, sandbox, data, logs } = makePage({
      search: '?locationIds=1,2',
      storage: { [KEY]: JSON.stringify({ 11897: false }) },
    });
    vm.runInContext(USERSCRIPT, ctx);
    vm.runInContext(inline, ctx);
    check('C1 deep link: saved choice not applied', sandbox.mapData.categories[11897].visible === true);
    const { store, dispatched } = installFakeStore(sandbox);
    await sleep(350);
    store.dispatch({ type: 'MG:MAP:HIDE_ALL_CATEGORIES' });
    await sleep(600);
    check('C2 deep link: nothing saved', data.get(KEY) === JSON.stringify({ 11897: false }));
    check('C3 deep link: only user dispatch seen', dispatched.length === 1);
    check('C4 position-only params are not a deep link', (() => {
      const p = makePage({ search: '?x=1&y=2&zoom=13', storage: { [KEY]: JSON.stringify({ 11897: false }) } });
      vm.runInContext(USERSCRIPT, p.ctx);
      vm.runInContext(inline, p.ctx);
      return p.sandbox.mapData.categories[11897].visible === false;
    })());
  }

  // ---------- D: site's own PRO feature enabled -> stand by
  {
    const { ctx, sandbox, data, logs } = makePage({
      storage: { 'mg:settings:game_203:remember_categories': 'true' },
    });
    vm.runInContext(USERSCRIPT, ctx);
    vm.runInContext(inline, ctx);
    const { store } = installFakeStore(sandbox);
    await sleep(350);
    store.dispatch({ type: 'MG:MAP:HIDE_ALL_CATEGORIES' });
    await sleep(600);
    check('D1 passive when site remembers by itself', !data.has(KEY));
    check('D2 says so', logs.some((l) => l[1].includes('Remember Selected Categories')));
  }

  // ---------- E: renamed action -> loud warning, no crash
  {
    const { ctx, sandbox, data, logs } = makePage();
    vm.runInContext(inline, ctx);
    data.set(KEY, JSON.stringify({ 11897: false }));
    const { store } = installFakeStore(sandbox);
    const real = store.dispatch;
    store.dispatch = (a) => real({ ...a, type: 'RENAMED:' + a.type });
    vm.runInContext(USERSCRIPT, ctx);
    await sleep(350);
    check('E1 warns when the site ignores the action', logs.some((l) => l[0] === 'warn' && l[1].includes('renamed')));
  }

  console.log(failures === 0 ? '\nALL PASSED' : `\n${failures} FAILED`);
  process.exit(failures === 0 ? 0 : 1);
})();
