const { test } = require("node:test");
const assert = require("node:assert/strict");
const { JSDOM } = require("jsdom");
const { FeedPoller, mergeNews } = require("../public/live-feed.js");

const card = (id) =>
  `<article class="story" data-id="${id}"><button>Haber ${id}</button><details><summary>Puan</summary>Ayrıntı</details></article>`;
function page(cards) {
  return new JSDOM(
    `<main id="news-list" tabindex="-1">${cards}</main><textarea id="chat-input">Taslağım</textarea><div id="chat-messages">Yanıt</div><input id="q-input" value="yazılmakta olan filtre">`,
  ).window.document;
}

test("live insertion preserves existing card state, focus, draft and conversation", () => {
  const doc = page(card(1));
  const existing = doc.querySelector(".story");
  existing.querySelector("details").open = true;
  existing.querySelector("button").focus();
  let clicked = false;
  const result = mergeNews(doc, page(card(2) + card(1)), (el) =>
    el.querySelector("button").addEventListener("click", () => {
      clicked = true;
    }),
  );
  assert.deepEqual(
    [...doc.querySelectorAll(".story")].map((el) => el.dataset.id),
    ["2", "1"],
  );
  assert.equal(doc.querySelector('[data-id="1"]'), existing);
  assert.equal(existing.querySelector("details").open, true);
  assert.equal(doc.activeElement, existing.querySelector("button"));
  assert.equal(doc.querySelector("#chat-input").value, "Taslağım");
  assert.equal(doc.querySelector("#chat-messages").textContent, "Yanıt");
  assert.equal(doc.querySelector("#q-input").value, "yazılmakta olan filtre");
  doc.querySelector('[data-id="2"] button').click();
  assert.equal(clicked, true);
  assert.equal(result.added, 1);
  assert.equal(mergeNews(doc, page(card(2) + card(1)), () => {}).added, 0);
});

test("day rollover removes old cards and shows the new empty state without losing chat", () => {
  const doc = page(card(1));
  doc.querySelector(".story button").focus();
  mergeNews(
    doc,
    page('<div class="empty-state">Bugün henüz haber yok</div>'),
    () => {},
  );
  assert.equal(doc.querySelectorAll(".story").length, 0);
  assert.match(doc.querySelector("#news-list").textContent, /henüz haber yok/);
  assert.equal(doc.activeElement.id, "news-list");
  assert.equal(doc.querySelector("#chat-input").value, "Taslağım");
  mergeNews(doc, page(card(2)), () => {});
  assert.equal(doc.querySelector(".empty-state"), null);
  assert.equal(doc.querySelectorAll(".story").length, 1);
});

test("polling skips hidden/offline pages and prevents overlapping requests", async () => {
  let enabled = false,
    release,
    applied = 0;
  const poller = new FeedPoller({
    enabled: () => enabled,
    load: () =>
      new Promise((r) => {
        release = r;
      }),
    apply: () => {
      applied++;
    },
    error: () => {},
  });
  assert.equal(await poller.check(), false);
  enabled = true;
  const pending = poller.check();
  assert.equal(await poller.check(), false);
  release("fresh");
  assert.equal(await pending, true);
  assert.equal(applied, 1);
});

test("failed polling retains content and recovers on the next check", async () => {
  let fail = true,
    content = "existing",
    warning = false;
  const poller = new FeedPoller({
    enabled: () => true,
    load: async () => {
      if (fail) throw new Error("offline");
      return "fresh";
    },
    apply: (value) => {
      content = value;
    },
    error: () => {
      warning = true;
    },
  });
  assert.equal(await poller.check(), false);
  assert.equal(content, "existing");
  assert.equal(warning, true);
  fail = false;
  assert.equal(await poller.check(), true);
  assert.equal(content, "fresh");
});

test("unchanged empty feed retains keyboard focus on its archive link", () => {
  const empty =
    '<div class="empty-state"><a href="/?period=all">Eski haberler</a></div>';
  const doc = page(empty);
  const link = doc.querySelector("a");
  link.focus();
  mergeNews(doc, page(empty), () => {});
  assert.equal(doc.activeElement, link);
  assert.equal(doc.querySelector("a"), link);
});
