const { test } = require("node:test");
const assert = require("node:assert/strict");
const { ConversationStore } = require("../public/chat-state.js");

test("pending request locks only its story and late answers stay with that story", () => {
  const store = new ConversationStore();
  store.start("1", "İlk soru");
  assert.throws(() => store.start("1", "Çift gönderim"));
  store.start("2", "Başka haber");
  store.succeed("1", "İlk yanıt");
  assert.equal(store.get("2").pending, true);
  assert.deepEqual(store.history("1"), [
    { role: "user", content: "İlk soru" },
    { role: "assistant", content: "İlk yanıt" },
  ]);
  assert.deepEqual(store.history("2"), []);
});

test("failed turns are retryable without polluting model history or duplicating questions", () => {
  const store = new ConversationStore();
  store.start("1", "Soru");
  store.fail("1", "Bağlantı hatası");
  assert.deepEqual(store.history("1"), []);
  assert.equal(store.get("1").pending, false);
  store.retry("1");
  store.succeed("1", "Yanıt");
  assert.equal(store.get("1").turns.length, 1);
  assert.deepEqual(store.history("1"), [
    { role: "user", content: "Soru" },
    { role: "assistant", content: "Yanıt" },
  ]);
});

test("restoration retains drafts and completed answers, interrupted work becomes retryable", () => {
  const store = new ConversationStore();
  store.get("1").draft = "Yarım soru";
  store.start("2", "Bekleyen soru");
  const restored = new ConversationStore(store.serialize());
  assert.equal(restored.get("1").draft, "Yarım soru");
  assert.equal(restored.get("2").pending, false);
  assert.equal(restored.get("2").turns[0].status, "error");
  restored.retry("2");
  assert.equal(restored.get("2").pending, true);
});

test("malformed saved data is ignored and user content stays plain text", () => {
  const store = new ConversationStore("{bad");
  store.start("1", "<img src=x onerror=alert(1)>");
  store.succeed("1", "<script>bad()</script>");
  assert.equal(store.history("1")[1].content, "<script>bad()</script>");
  assert.deepEqual(
    new ConversationStore('{"1":{"turns":"broken"}}').history("1"),
    [],
  );
});

test("long conversations trim oldest complete exchanges to a byte budget", () => {
  const store = new ConversationStore();
  for (let i = 0; i < 12; i++) {
    store.start("1", `${i}:` + "😀".repeat(1998));
    store.succeed("1", "Yanıt ".repeat(500));
  }
  const history = store.history("1");
  assert.ok(Buffer.byteLength(JSON.stringify(history)) <= 48000);
  assert.equal(history.length % 2, 0);
  assert.ok(history.at(-2).content.startsWith("11:"));
});

test("an earlier failed turn remains retryable after a later successful question", () => {
  const store = new ConversationStore();
  store.start("1", "İlk soru");
  store.fail("1", "Hata");
  store.start("1", "İkinci soru");
  store.succeed("1", "İkinci yanıt");
  assert.deepEqual(store.history("1", 0), []);
  assert.equal(store.retry("1", 0), "İlk soru");
  store.succeed("1", "İlk yanıt");
  assert.equal(store.get("1").turns[0].answer, "İlk yanıt");
  assert.equal(store.get("1").turns[1].answer, "İkinci yanıt");
  assert.equal(store.get("1").turns.length, 2);
});
