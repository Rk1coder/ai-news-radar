(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.RadarLiveFeed = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";
  class FeedPoller {
    constructor({ enabled, load, apply, error }) {
      Object.assign(this, { enabled, load, apply, error });
      this.busy = false;
    }
    async check() {
      if (this.busy || !this.enabled()) return false;
      this.busy = true;
      try {
        const value = await this.load();
        this.apply(value);
        return true;
      } catch (error) {
        this.error(error);
        return false;
      } finally {
        this.busy = false;
      }
    }
  }

  function mergeNews(document, incoming, onNew) {
    const list = document.getElementById("news-list");
    const fresh = incoming.getElementById("news-list");
    if (!fresh) throw new Error("Invalid feed");
    const existing = new Map(
      [...list.querySelectorAll(".story")].map((el) => [el.dataset.id, el]),
    );
    const incomingCards = [...fresh.querySelectorAll(".story")];
    if (
      !incomingCards.length &&
      !existing.size &&
      list.innerHTML === fresh.innerHTML
    ) {
      return { added: 0, stories: [] };
    }
    const ids = new Set(incomingCards.map((el) => el.dataset.id));
    let added = 0;
    let cursor = list.firstElementChild;
    incomingCards.forEach((source) => {
      let card = existing.get(source.dataset.id);
      if (!card) {
        card = document.importNode(source, true);
        card.classList.add("is-new");
        onNew(card);
        added++;
      }
      if (card !== cursor) list.insertBefore(card, cursor);
      cursor = card.nextElementSibling;
    });
    for (const child of [...list.children]) {
      if (!child.matches(".story") || !ids.has(child.dataset.id)) {
        if (child.contains(document.activeElement))
          list.focus({ preventScroll: true });
        child.remove();
      }
    }
    if (!incomingCards.length) {
      for (const child of fresh.children)
        list.append(document.importNode(child, true));
    }
    return { added, stories: [...list.querySelectorAll(".story")] };
  }
  return { FeedPoller, mergeNews };
});
