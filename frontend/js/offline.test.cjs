/**
 * offline.test.cjs — Tests for offline.js banner states, not-saved cards,
 * and dismissNotSaved().
 *
 * Run with: node frontend/js/offline.test.cjs
 */
"use strict";
const fs = require("fs");
const path = require("path");

// ─── Minimal browser stubs ────────────────────────────────────────────────────
let _onlineValue = true;
let _lastBannerText = "";
let _lastBannerClass = "";
let _queue = [];

// Fake banner element
const _fakeBanner = {
  style: { display: "" },
  get className() { return _lastBannerClass; },
  set className(v) { _lastBannerClass = v; },
  get textContent() { return _lastBannerText; },
  set textContent(v) { _lastBannerText = v; },
};

const _fakeContainer = {
  querySelector(sel) {
    if (sel === ".bk-conn-banner") return _fakeBanner;
    if (sel === ".page-header")    return null;
    return null;
  },
  insertBefore() {},
  firstChild: null,
};

// Inject globals into the eval scope
const globalStubs = {
  navigator:    { get onLine() { return _onlineValue; } },
  window:       { addEventListener() {}, dispatchEvent() {}, setTimeout(fn, ms) { /* no-op in tests */ } },
  localStorage: (() => {
    let store = {};
    return {
      getItem:    (k) => store[k] || null,
      setItem:    (k, v) => { store[k] = String(v); },
      removeItem: (k) => { delete store[k]; },
    };
  })(),
  document: {
    readyState: "complete",
    addEventListener() {},
    querySelectorAll(sel) {
      if (sel === ".app-container")       return [_fakeContainer];
      if (sel.includes("nav-mic-btn"))    return [];
      return [];
    },
    getElementById: () => null,
    createElement(tag) {
      return {
        tag, className: "", style: {}, textContent: "", dataset: {},
        children: [],
        querySelector:    () => null,
        querySelectorAll: () => [],
        appendChild(c)   { this.children.push(c); return c; },
        insertBefore(c)  { this.children.unshift(c); return c; },
        getAttribute:    () => null,
        addEventListener() {},
      };
    },
  },
  module: { exports: {} },
  // Queue stubs
  getOfflineQueue: () => [..._queue],
  setOfflineQueue: (q) => { _queue = [...q]; },
  // Toast stub
  showToast: () => {},
  createTransaction: null,
};

// Evaluate offline.js inside the stub context
const src = fs.readFileSync(path.join(__dirname, "offline.js"), "utf8");
const fn  = new Function(...Object.keys(globalStubs), src);
fn(...Object.values(globalStubs));

const lib = globalStubs.module.exports;

// ─── Tiny test runner ─────────────────────────────────────────────────────────
let _assertions = 0;
let _failures   = 0;

function assert(cond, msg) {
  _assertions++;
  if (cond) {
    console.log("  ✓", msg);
  } else {
    _failures++;
    console.error("  ✗ FAIL:", msg);
  }
}

function describe(name, fn) {
  console.log("\n" + name);
  fn();
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("Banner: offline state with queued entries (count = 2)", () => {
  _queue = [{ id: 1 }, { id: 2 }];
  lib._setBannerState("offline");
  assert(_fakeBanner.textContent.includes("2"), "shows queue count '2'");
  assert(_fakeBanner.textContent.includes("wait kar rahi"), "shows wait message");
  assert(_lastBannerClass.includes("bk-conn-banner--offline"), "has offline CSS class");
});

describe("Banner: offline state with queuedCount = 0", () => {
  _queue = [];
  lib._setBannerState("offline");
  assert(_fakeBanner.textContent.includes("bolte rahiye"), "shows no-queue message");
  assert(!_fakeBanner.textContent.includes("wait kar rahi"), "no queue-count in message");
});

describe("Banner: offline state with queuedCount = 1", () => {
  _queue = [{ id: "x" }];
  lib._setBannerState("offline");
  assert(_fakeBanner.textContent.includes("1"), "shows count '1'");
  assert(_fakeBanner.textContent.includes("wait kar rahi"), "wait message present");
});

describe("Banner: reconnecting state", () => {
  lib._setBannerState("reconnecting");
  assert(_fakeBanner.textContent.includes("Dobara jud raha"), "shows reconnecting text");
  assert(_lastBannerClass.includes("bk-conn-banner--reconnecting"), "has reconnecting CSS class");
});

describe("Banner: syncing state", () => {
  lib._setBannerState("syncing");
  assert(_fakeBanner.textContent.includes("sync ho rahi"), "shows syncing text");
  assert(_lastBannerClass.includes("bk-conn-banner--syncing"), "has syncing CSS class");
});

describe("Banner: synced state (all queued = 0)", () => {
  _queue = [];
  lib._setBannerState("synced");
  assert(_fakeBanner.textContent.includes("Sab entry jud gayi"), "shows synced text");
  assert(_lastBannerClass.includes("bk-conn-banner--synced"), "has synced CSS class");
});

describe("Banner: hide state", () => {
  lib._setBannerState("hide");
  assert(_fakeBanner.style.display === "none", "banner display set to none");
  assert(_fakeBanner.textContent === "", "banner textContent cleared");
});

describe("queuedCount helper", () => {
  _queue = [1, 2, 3];
  assert(lib._queuedCount() === 3, "_queuedCount() returns 3");
  _queue = [];
  assert(lib._queuedCount() === 0, "_queuedCount() returns 0 on empty queue");
});

describe("notSaved: addNotSaved stores entries, no duplicates", () => {
  const { addNotSaved, _getState } = lib;
  // Reset by dismissing all
  _getState().notSaved.forEach(e => lib.dismissNotSaved(e.turn_id));

  addNotSaved({ turn_id: "t1", text: "Ramesh ne 500 diye" });
  addNotSaved({ turn_id: "t2", text: "Suresh 300 udhar" });
  assert(_getState().notSaved.length === 2, "two distinct entries stored");

  addNotSaved({ turn_id: "t1", text: "Ramesh ne 500 diye" });   // duplicate
  assert(_getState().notSaved.length === 2, "duplicate turn_id not added twice");
});

describe("notSaved: dismissNotSaved removes the correct entry", () => {
  const { dismissNotSaved, _getState } = lib;

  dismissNotSaved("t1");
  assert(_getState().notSaved.length === 1, "one entry remains");
  assert(_getState().notSaved[0].turn_id === "t2", "correct entry ('t2') remains");
});

describe("notSaved: close button (dismissNotSaved) empties the list", () => {
  const { addNotSaved, dismissNotSaved, _getState } = lib;

  addNotSaved({ turn_id: "close-test", text: "some offline entry" });
  assert(_getState().notSaved.find(e => e.turn_id === "close-test"), "close-test entry present");

  // Simulate user clicking close button → calls dismissNotSaved
  dismissNotSaved("close-test");
  dismissNotSaved("t2");  // also clear t2 from previous describe
  assert(_getState().notSaved.length === 0, "close button clears all dismissed entries");
});

// ─── Summary ──────────────────────────────────────────────────────────────────
console.log(`\n${"─".repeat(52)}`);
if (_failures === 0) {
  console.log(`✅  All ${_assertions} assertions passed.`);
} else {
  console.error(`❌  ${_failures} of ${_assertions} assertions FAILED.`);
  process.exit(1);
}
