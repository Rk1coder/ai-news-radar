const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const ejs = require("ejs");
const { JSDOM } = require("jsdom");

const root = path.join(__dirname, "..");
const template = fs.readFileSync(path.join(root, "views/index.ejs"), "utf8");
const settingsMarkup = template.slice(template.indexOf('<dialog id="settings-modal"'), template.lastIndexOf("</dialog>") + 9);
const fixture = {
  scan: { interval_minutes: 15, auto_scan_enabled: true },
  sources: [{ name: "arxiv", enabled: true, builtin: true, source_type: "academic" }],
};
const flush = () => new Promise((resolve) => setImmediate(resolve));
const settle = () => new Promise((resolve) => setTimeout(resolve, 60));

function setup(t, { reduced = false, fetcher, animation = true } = {}) {
  const dom = new JSDOM(`<button id="open-settings">Ayarlar</button>${ejs.render(settingsMarkup, { icon: () => "" })}`, {
    url: "http://localhost:3000/", runScripts: "outside-only", pretendToBeVisual: true,
  });
  const w = dom.window;
  const d = w.document;
  w.matchMedia = () => ({ matches: reduced, addEventListener() {} });
  // jsdom does not implement native dialog methods. Preserve their open/close events.
  w.HTMLDialogElement.prototype.showModal = function () { this.setAttribute("open", ""); };
  w.HTMLDialogElement.prototype.close = function () {
    this.removeAttribute("open");
    w.setTimeout(() => this.dispatchEvent(new w.Event("close")), 0);
  };
  w.fetch = fetcher || (async () => ({ ok: true, json: async () => structuredClone(fixture) }));
  if (animation) {
    w.eval(fs.readFileSync(require.resolve("gsap/dist/gsap.min.js"), "utf8"));
    w.gsap.globalTimeline.timeScale(100);
  }
  const motionFile = path.join(root, "public/settings-motion.js");
  if (fs.existsSync(motionFile)) w.eval(fs.readFileSync(motionFile, "utf8"));
  const programFile = path.join(root, "public/scan-program.js");
  if (fs.existsSync(programFile)) w.eval(fs.readFileSync(programFile, "utf8"));
  w.eval(fs.readFileSync(path.join(root, "public/settings.js"), "utf8"));
  t.after(async () => { await flush(); w.gsap?.ticker.sleep(); dom.window.close(); });
  return { w, d, trigger: d.getElementById("open-settings"), modal: d.getElementById("settings-modal") };
}

test("settings keeps the modal open until its exit animation finishes and restores focus", async (t) => {
  const { d, trigger, modal } = setup(t);
  trigger.focus();
  trigger.click();
  await flush();
  await settle();
  assert.equal(trigger.getAttribute("aria-expanded"), "true");
  d.getElementById("close-settings").click();
  assert.equal(modal.open, true, "the close transition must finish before hiding the dialog");
  await settle();
  assert.equal(modal.open, false);
  assert.equal(trigger.getAttribute("aria-expanded"), "false");
  assert.equal(d.activeElement, trigger);
  assert.equal(d.body.classList.contains("settings-open"), false);
});

test("Escape follows the exit animation even while the opening is running", async (t) => {
  const { w, d, trigger, modal } = setup(t);
  trigger.click();
  const escape = new w.Event("cancel", { cancelable: true });
  modal.dispatchEvent(escape);
  assert.equal(escape.defaultPrevented, true);
  await settle();
  assert.equal(modal.open, false);
  assert.equal(d.activeElement, trigger);
  trigger.click();
  await settle();
  assert.equal(modal.open, true);
  assert.equal(trigger.getAttribute("aria-expanded"), "true");
});

test("category changes keep unsaved scan edits and save the same API payload", async (t) => {
  let saved;
  const { w, d, trigger } = setup(t, { reduced: true, fetcher: async (url, options) => {
    if (options?.method === "PUT") saved = JSON.parse(options.body);
    return { ok: true, json: async () => ({ ...fixture, scan: saved || fixture.scan }) };
  } });
  trigger.click();
  await flush();
  const interval = d.querySelector('[name="scan-interval"][value="30"]');
  interval.checked = true;
  interval.dispatchEvent(new w.Event("change", { bubbles: true }));
  d.querySelector('button[data-panel="appearance"]').click();
  assert.equal(d.querySelector('section[data-panel="appearance"]').hidden, false);
  assert.equal(d.querySelector('button[data-panel="appearance"]').getAttribute("aria-selected"), "true");
  d.querySelector('button[data-panel="scan"]').click();
  assert.equal(interval.checked, true);
  assert.equal(d.getElementById("settings-footer").hidden, false);
  d.getElementById("settings-save").click();
  await flush();
  assert.deepEqual(saved, { interval_minutes: 30, auto_scan_enabled: true });
  assert.equal(d.getElementById("settings-footer").hidden, true);
});

test("reduced motion and an unavailable GSAP runtime both dismiss without a delay", async (t) => {
  for (const options of [{ reduced: true }, { animation: false }]) {
    const { d, trigger, modal } = setup(t, options);
    trigger.click();
    await flush();
    assert.equal(modal.open, true);
    assert.equal(trigger.getAttribute("aria-expanded"), "true");
    d.getElementById("close-settings").click();
    assert.equal(modal.open, false);
    assert.equal(d.activeElement, trigger);
  }
});

test("a failed load leaves appearance usable and can be retried", async (t) => {
  let fail = true;
  const { d, trigger } = setup(t, { reduced: true, fetcher: async () => ({
    ok: !fail, json: async () => fail ? { error: "Bağlantı kurulamadı" } : structuredClone(fixture),
  }) });
  trigger.click();
  await flush();
  assert.match(d.getElementById("settings-load-status").textContent, /Bağlantı kurulamadı/);
  d.querySelector('button[data-panel="appearance"]').click();
  assert.equal(d.querySelector('section[data-panel="appearance"]').hidden, false);
  fail = false;
  d.getElementById("settings-retry").click();
  await flush();
  assert.equal(d.getElementById("settings-load-notice").hidden, true);
  assert.equal(d.getElementById("auto-scan-enabled").checked, true);
});

test("an earlier opening's late response cannot overwrite the current settings", async (t) => {
  let resolveFirst;
  let count = 0;
  const { d, trigger } = setup(t, { reduced: true, fetcher: async () => {
    count++;
    if (count === 1) return new Promise((resolve) => { resolveFirst = resolve; });
    return { ok: true, json: async () => ({ ...fixture, scan: { interval_minutes: 30, auto_scan_enabled: false } }) };
  } });
  trigger.click();
  d.getElementById("close-settings").click();
  trigger.click();
  await flush();
  resolveFirst({ ok: true, json: async () => structuredClone(fixture) });
  await flush();
  assert.equal(d.querySelector('[name="scan-interval"][value="30"]').checked, true);
  assert.equal(d.getElementById("auto-scan-enabled").checked, false);
});

test("the queued native close event does not reset a dialog reopened immediately", async (t) => {
  const { d, trigger, modal } = setup(t, { reduced: true });
  trigger.click();
  await flush();
  d.getElementById("close-settings").click();
  trigger.click();
  await settle();
  assert.equal(modal.open, true);
  assert.equal(trigger.getAttribute("aria-expanded"), "true");
  assert.equal(d.body.classList.contains("settings-open"), true);
  assert.equal(d.getElementById("settings-load-notice").hidden, true);
});

test("a late save from a closed dialog cannot discard newly edited values", async (t) => {
  let resolveSave;
  const { w, d, trigger } = setup(t, { reduced: true, fetcher: async (url, options) => {
    if (options?.method === "PUT") return new Promise((resolve) => { resolveSave = resolve; });
    return { ok: true, json: async () => structuredClone(fixture) };
  } });
  trigger.click();
  await flush();
  function select(minutes) {
    const radio = d.querySelector(`[name="scan-interval"][value="${minutes}"]`);
    radio.checked = true;
    radio.dispatchEvent(new w.Event("change", { bubbles: true }));
  }
  select(30);
  d.getElementById("settings-save").click();
  d.getElementById("close-settings").click();
  await settle();
  trigger.click();
  await flush();
  select(60);
  resolveSave({ ok: true, json: async () => ({ ...fixture, scan: { interval_minutes: 30, auto_scan_enabled: true } }) });
  await flush();
  assert.equal(d.querySelector('[name="scan-interval"][value="60"]').checked, true);
  assert.equal(d.getElementById("settings-footer").hidden, false);
});

test("closing after Save still completes all changes submitted together", async (t) => {
  let resolveScan;
  const writes = [];
  const { w, d, trigger } = setup(t, { reduced: true, fetcher: async (url, options) => {
    if (options?.method === "PUT") {
      writes.push([url, JSON.parse(options.body)]);
      if (url === "/settings-api/scan") return new Promise((resolve) => { resolveScan = resolve; });
    }
    return { ok: true, json: async () => structuredClone(fixture) };
  } });
  trigger.click();
  await flush();
  const interval = d.querySelector('[name="scan-interval"][value="30"]');
  interval.checked = true;
  interval.dispatchEvent(new w.Event("change", { bubbles: true }));
  const source = d.querySelector('[data-source="arxiv"]');
  source.checked = false;
  source.dispatchEvent(new w.Event("change", { bubbles: true }));
  d.getElementById("settings-save").click();
  d.getElementById("close-settings").click();
  resolveScan({ ok: true, json: async () => structuredClone(fixture) });
  await flush();
  assert.deepEqual(writes, [
    ["/settings-api/scan", { interval_minutes: 30, auto_scan_enabled: true }],
    ["/settings-api/sources/arxiv", { enabled: false }],
  ]);
});

test("Program combines added times and overnight windows in its saved payload", async (t) => {
  let saved;
  const { w, d, trigger } = setup(t, { reduced:true, fetcher:async (url, options) => {
    if (options?.method === 'PUT') saved = JSON.parse(options.body);
    return {ok:true,json:async()=>({...fixture,scan:{...fixture.scan,...saved}})};
  } });
  trigger.click();
  await flush();
  const mode = d.querySelector('[name="scan-interval"][value="0"]');
  mode.checked = true;
  mode.dispatchEvent(new w.Event('change',{bubbles:true}));
  assert.equal(d.getElementById('scan-program-editor').hidden, false);
  d.getElementById('program-time').value = '13:30';
  d.getElementById('program-add-time').click();
  d.getElementById('program-start').value = '22:00';
  d.getElementById('program-end').value = '02:00';
  d.getElementById('program-cadence').value = '30';
  d.getElementById('program-add-window').click();
  d.querySelector('button[data-panel="appearance"]').click();
  d.querySelector('button[data-panel="scan"]').click();
  assert.match(d.getElementById('program-time-list').textContent,/13:30/);
  assert.match(d.getElementById('program-window-list').textContent,/22:00/);
  d.getElementById('settings-save').click();
  await flush();
  assert.deepEqual(saved,{interval_minutes:0,auto_scan_enabled:true,program:{times:['13:30'],windows:[{start:'22:00',end:'02:00',interval_minutes:30}]}});
});

test("Program rejects an empty schedule and equal window endpoints without saving", async (t) => {
  let writes = 0;
  const { w, d, trigger } = setup(t, { reduced:true, fetcher:async (url, options) => {
    if (options?.method === 'PUT') writes++;
    return {ok:true,json:async()=>structuredClone(fixture)};
  } });
  trigger.click(); await flush();
  const mode = d.querySelector('[name="scan-interval"][value="0"]');
  mode.checked=true; mode.dispatchEvent(new w.Event('change',{bubbles:true}));
  d.querySelector('button[data-panel="sources"]').click();
  d.getElementById('settings-save').click(); await flush();
  assert.equal(writes,0);
  assert.equal(d.getElementById('settings-panel-scan').hidden,false);
  assert.equal(d.getElementById('program-error').hidden,false);
  assert.equal(d.activeElement.id,'program-time');
  d.getElementById('program-start').value='09:00';
  d.getElementById('program-end').value='09:00';
  d.getElementById('program-add-window').click();
  assert.match(d.getElementById('program-error').textContent,/aynı/);
  assert.equal(d.querySelectorAll('#program-window-list button').length,0);
});

test("Program removes rules, ignores duplicates and Cancel restores saved rules", async (t) => {
  const initial={times:['09:00','13:30'],windows:[{start:'09:00',end:'18:00',interval_minutes:15}]};
  const { d, trigger } = setup(t,{reduced:true,fetcher:async()=>({ok:true,json:async()=>({...fixture,scan:{...fixture.scan,interval_minutes:0,program:initial,timezone:'Europe/Istanbul'}})})});
  trigger.click(); await flush();
  d.getElementById('program-time').value='09:00';
  d.getElementById('program-add-time').click();
  assert.equal(d.querySelectorAll('#program-time-list button').length,2);
  d.querySelector('#program-time-list button').click();
  d.querySelector('#program-window-list button').click();
  assert.equal(d.getElementById('settings-footer').hidden,false);
  d.getElementById('settings-cancel').click();
  assert.equal(d.querySelectorAll('#program-time-list button').length,2);
  assert.equal(d.querySelectorAll('#program-window-list button').length,1);
  assert.equal(d.getElementById('settings-footer').hidden,true);
});
