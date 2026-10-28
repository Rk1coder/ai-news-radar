const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const ejs = require("ejs");
const { JSDOM } = require("jsdom");
const root = path.join(__dirname, "..");
function html(ids, scan = {}) {
  return ejs.render(
    fs.readFileSync(path.join(root, "views/index.ejs"), "utf8"),
    {
      developments: ids.map((id) => ({
        id,
        title_tr: `Haber ${id}`,
        summary_tr: "Özet",
        sector_tags: [],
        verified: false,
        raw_item: {
          title: `Story ${id}`,
          summary: "",
          url: `https://example.com/${id}`,
          source: { name: "Kaynak" },
          published_at: null,
        },
      })),
      total_count: ids.length,
      scanLabels: {
        running: false,
        status: "Kontrol edildi",
        schedule: "15 dakikada bir tarama",
        id: 1, outcome: "succeeded", newCount: 0, ...scan,
      },
      refreshBusy: false,
      refreshError: false,
      refreshed: null,
      weekly_digest: { content: "Güncel özet", story_count: 1 },
      digestLabel: "az önce",
      period: "today",
      sort: "recent",
      q: "",
      sector: "",
      source_type: "",
      min_priority: 0,
      show_unverified: false,
      all_sectors: [],
      source_type_labels: {},
      qs: () => "?period=today",
      icon: () => "",
      sourceLabel: (s) => s,
      sectorLabel: (s) => s,
      formatDate: () => "26 Ekim 2026",
      safeUrl: (s) => s,
    },
  );
}

test("full page polling wires new chat cards and survives history restore without resetting a draft", async (t) => {
  const dom = new JSDOM(html([1]), {
    url: "http://localhost:3000/",
    runScripts: "outside-only",
    pretendToBeVisual: true,
  });
  t.after(() => dom.window.close());
  const w = dom.window;
  let tick,
    stopped = false,
    latest = html([1]);
  w.matchMedia = () => ({ matches: false, addEventListener() {} });
  w.IntersectionObserver = class {
    observe() {}
    unobserve() {}
  };
  w.requestAnimationFrame = (fn) => fn();
  w.setInterval = (fn) => {
    tick = fn;
    return 1;
  };
  w.clearInterval = () => {
    stopped = true;
  };
  w.fetch = async () => ({ ok: true, text: async () => latest });
  for (const file of ["chat-state.js", "live-feed.js", "app.js"])
    w.eval(fs.readFileSync(path.join(root, "public", file), "utf8"));
  await new Promise((resolve) => setImmediate(resolve));
  const input = w.document.getElementById("chat-input");
  input.value = "Kaybolmaması gereken soru";
  input.dispatchEvent(new w.Event("input"));
  input.focus();
  const digestSummary = w.document.querySelector("#digest-region summary");
  digestSummary.focus();
  await tick();
  assert.equal(w.document.activeElement, digestSummary);
  input.focus();
  latest = html([2, 1]);
  await tick();
  assert.equal(input.value, "Kaybolmaması gereken soru");
  assert.equal(w.document.activeElement, input);
  assert.equal(w.document.getElementById("chat-title").textContent, "Haber 1");
  assert.equal(w.document.querySelectorAll(".story").length, 2);
  assert.equal(
    w.document.querySelector("#feed-heading span")?.textContent,
    "2",
    "live refresh keeps the updated count as a separate typographic label",
  );
  w.document.querySelector('[data-id="2"] [data-action="chat"]').click();
  assert.equal(w.document.getElementById("chat-title").textContent, "Haber 2");
  w.document.querySelector('[data-id="1"] [data-action="chat"]').click();
  assert.equal(input.value, "Kaybolmaması gereken soru");
  w.dispatchEvent(new w.PageTransitionEvent("pagehide", { persisted: true }));
  w.dispatchEvent(new w.PageTransitionEvent("pageshow", { persisted: true }));
  assert.equal(
    stopped,
    false,
    "poll timer must continue after BFCache history restore",
  );
  await new Promise((resolve) => setImmediate(resolve));
});


test("manual scan stays on the page, preserves a draft, and reports completion and errors", async (t) => {
  const dom = new JSDOM(html([1]), {url:"http://localhost:3000/?period=all", runScripts:"outside-only", pretendToBeVisual:true});
  t.after(() => dom.window.close());
  const w = dom.window;
  let tick, latest = html([1]), fail = false;
  w.matchMedia = () => ({ matches: false, addEventListener() {} });
  w.IntersectionObserver = class { observe() {} unobserve() {} };
  w.requestAnimationFrame = (fn) => fn();
  w.setInterval = (fn) => {tick = fn; return 1;};
  w.fetch = async (url) => {
    if (url === '/refresh') {
      latest = html([1], {id: 2, running: true, outcome:'running'});
      return {status:fail ? 503 : 202, json:async()=>({started:true,scan:{id:2,status:'running'}})};
    }
    return {ok:true,text:async()=>latest};
  };
  for (const file of ["chat-state.js", "live-feed.js", "app.js"])
    w.eval(fs.readFileSync(path.join(root, "public", file), "utf8"));
  await new Promise(r => setImmediate(r));
  const input = w.document.getElementById('chat-input');
  input.value = 'Taslak soru'; input.dispatchEvent(new w.Event('input'));
  const submit = new w.Event('submit', {cancelable:true});
  w.document.getElementById('refresh-form').dispatchEvent(submit);
  await new Promise(r => setImmediate(r));
  assert.equal(submit.defaultPrevented, true);
  assert.equal(w.location.search, '?period=all');
  assert.equal(w.document.querySelector('#refresh-form button').disabled, true);
  latest = html([2,1], {id:2,outcome:'succeeded',newCount:1});
  await tick();
  assert.equal(input.value, 'Taslak soru');
  assert.match(w.document.getElementById('refresh-message').textContent, /1 yeni haber/);
  assert.equal(w.document.querySelector('#refresh-form button').disabled, false);
  fail = true;
  w.document.getElementById('refresh-form').dispatchEvent(new w.Event('submit',{cancelable:true}));
  await new Promise(r => setImmediate(r));
  assert.match(w.document.getElementById('refresh-message').textContent, /doğrulanamadı/);
  assert.equal(w.document.querySelectorAll('.story').length, 2);
});

function assistantSetup(t, { mobile = true, reduced = false, gsap = true } = {}) {
  const dom = new JSDOM(html([1, 2]), { url: "http://localhost:3001/", runScripts: "outside-only", pretendToBeVisual: true });
  const w = dom.window;
  w.matchMedia = (query) => ({ matches: query.includes("reduced-motion") ? reduced : mobile, addEventListener() {} });
  w.IntersectionObserver = class { observe() {} unobserve() {} };
  w.setInterval = () => 1;
  w.fetch = async () => ({ ok: true, json: async () => ({ image: null }), text: async () => html([1, 2]) });
  if (gsap) {
    w.eval(fs.readFileSync(require.resolve("gsap/dist/gsap.min.js"), "utf8"));
    w.gsap.globalTimeline.timeScale(100);
  }
  for (const file of ["chat-state.js", "live-feed.js", "assistant-motion.js", "app.js"]) {
    const full = path.join(root, "public", file);
    if (fs.existsSync(full)) w.eval(fs.readFileSync(full, "utf8"));
  }
  t.after(() => { w.gsap?.ticker.sleep(); w.close(); });
  const d = w.document;
  return { w, d, panel: d.getElementById("assistant"), trigger: d.getElementById("assistant-launcher") };
}
const motionSettled = () => new Promise((resolve) => setTimeout(resolve, 80));

test("assistant retains modal semantics until the exit finishes, then restores focus", async (t) => {
  const { d, panel, trigger } = assistantSetup(t);
  trigger.click();
  await motionSettled();
  d.getElementById("close-chat").click();
  assert.equal(panel.hidden, false, "closing must finish its animation before hiding the panel");
  assert.equal(d.getElementById("page-content").inert, true);
  await motionSettled();
  assert.equal(panel.hidden, true);
  assert.equal(d.body.classList.contains("chat-open"), false);
  assert.equal(d.getElementById("page-content").inert, false);
  assert.equal(d.activeElement, trigger);
});

test("reopening the assistant during exit cancels dismissal and preserves the draft", async (t) => {
  const { w, d, panel, trigger } = assistantSetup(t);
  trigger.click();
  await motionSettled();
  const input = d.getElementById("chat-input");
  input.value = "Kaybolmayan taslak";
  input.dispatchEvent(new w.Event("input"));
  d.getElementById("close-chat").click();
  trigger.click();
  await motionSettled();
  assert.equal(panel.hidden, false);
  assert.equal(input.value, "Kaybolmayan taslak");
  assert.equal(d.body.classList.contains("chat-open"), true);
  assert.equal(trigger.getAttribute("aria-expanded"), "true");
});

test("Escape during entrance closes smoothly and keeps each story's draft", async (t) => {
  const { w, d, panel } = assistantSetup(t);
  const first = d.querySelector('[data-id="1"] [data-action="chat"]');
  first.click();
  const input = d.getElementById("chat-input");
  input.value = "İlk haberin sorusu";
  input.dispatchEvent(new w.Event("input"));
  panel.dispatchEvent(new w.KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
  assert.equal(panel.hidden, false);
  await motionSettled();
  assert.equal(d.activeElement, first);
  d.querySelector('[data-id="2"] [data-action="chat"]').click();
  assert.equal(input.value, "");
  first.click();
  assert.equal(input.value, "İlk haberin sorusu");
  assert.equal(d.getElementById("chat-title").textContent, "Haber 1");
});

test("assistant reduced-motion and missing GSAP paths close immediately", async (t) => {
  for (const options of [{ reduced: true }, { gsap: false }]) {
    const { d, panel, trigger } = assistantSetup(t, options);
    trigger.click();
    assert.equal(trigger.getAttribute("aria-expanded"), "true");
    d.getElementById("close-chat").click();
    assert.equal(panel.hidden, true);
    assert.equal(trigger.getAttribute("aria-expanded"), "false");
  }
});

test("the single global assistant control lives in the header and toggles chat", async (t) => {
  const { d, trigger, panel } = assistantSetup(t, { reduced: true });
  assert.ok(d.querySelector('.topbar-actions').contains(trigger));
  assert.equal(d.querySelectorAll('.open-assistant').length, 1);
  trigger.click();
  assert.equal(panel.hidden, false);
  assert.equal(d.getElementById('page-header').inert, true);
  trigger.click();
  assert.equal(panel.hidden, true);
  assert.equal(d.getElementById('page-header').inert, false);
  assert.equal(d.activeElement, trigger);
});

test("story actions animate from the shared top-right control rather than the card", async (t) => {
  const { w, d, trigger, panel } = assistantSetup(t);
  trigger.getBoundingClientRect = () => ({left:900,top:36,right:1020,bottom:80,width:120,height:44});
  panel.getBoundingClientRect = () => ({left:640,top:100,right:1020,bottom:700,width:380,height:600});
  const header = panel.querySelector('.assistant-header');
  header.getBoundingClientRect = () => ({left:640,top:100,right:1020,bottom:156,width:380,height:56});
  const cardButton = d.querySelector('[data-id="1"] [data-action="chat"]');
  cardButton.getBoundingClientRect = () => ({left:100,top:400,right:200,bottom:444,width:100,height:44});
  cardButton.click();
  assert.equal(w.gsap.getProperty(header, 'x'), 260);
  assert.equal(w.gsap.getProperty(header, 'y'), -64);
  assert.equal(d.getElementById('chat-title').textContent, 'Haber 1');
});
