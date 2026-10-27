(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  let stories = [...document.querySelectorAll(".story")];
  const developments = new Map(
    stories.map((el) => {
      const d = JSON.parse(el.dataset.dev);
      return [String(d.id), d];
    }),
  );
  const cacheKey = "radar-conversations-v1";
  let cached;
  try {
    cached = sessionStorage.getItem(cacheKey);
  } catch (_) {}
  const store = new ConversationStore(cached);
  const panel = $("assistant"),
    page = $("page-content"),
    input = $("chat-input"),
    messages = $("chat-messages"),
    scroll = $("chat-scroll");
  const mobile = matchMedia("(max-width: 900px)");
  let activeId = null,
    returnFocus = null,
    visibleCount = 15;
  function persist() {
    try {
      sessionStorage.setItem(cacheKey, store.serialize());
    } catch (_) {
      /* Conversation remains usable in memory. */
    }
  }
  function safeUrl(raw) {
    try {
      const u = new URL(raw);
      return ["http:", "https:"].includes(u.protocol) ? u.href : "";
    } catch {
      return "";
    }
  }
  function setLink(el, url) {
    const safe = safeUrl(url);
    el.hidden = !safe;
    if (safe) el.href = safe;
    else el.removeAttribute("href");
  }
  function sizeInput() {
    input.style.height = "auto";
    input.style.height = `${Math.min(140, Math.max(48, input.scrollHeight))}px`;
  }
  function setPanelSemantics() {
    const modal = !panel.hidden && mobile.matches;
    document.body.classList.toggle("chat-open", modal);
    page.inert = modal;
    if (modal) {
      panel.setAttribute("role", "dialog");
      panel.setAttribute("aria-modal", "true");
    } else {
      panel.removeAttribute("role");
      panel.removeAttribute("aria-modal");
    }
    if (modal && window.visualViewport) {
      panel.style.setProperty(
        "--chat-height",
        `${window.visualViewport.height}px`,
      );
      panel.style.setProperty(
        "--chat-top",
        `${window.visualViewport.offsetTop}px`,
      );
    } else {
      panel.style.removeProperty("--chat-height");
      panel.style.removeProperty("--chat-top");
    }
  }
  function openChat(dev, trigger, focus = true) {
    if (dev) activeId = String(dev.id);
    if (trigger) returnFocus = trigger;
    panel.hidden = false;
    document.body.classList.add("has-assistant");
    setPanelSemantics();
    stories.forEach((el) =>
      el.classList.toggle("is-active", el.dataset.id === activeId),
    );
    renderConversation();
    if (focus)
      requestAnimationFrame(() =>
        (activeId ? input : $("close-chat")).focus({ preventScroll: true }),
      );
  }
  function closeChat() {
    panel.hidden = true;
    document.body.classList.remove("has-assistant");
    setPanelSemantics();
    (returnFocus?.isConnected ? returnFocus : $("assistant-launcher")).focus({
      preventScroll: true,
    });
  }
  $("close-chat").addEventListener("click", closeChat);
  document
    .querySelectorAll(".open-assistant")
    .forEach((button) =>
      button.addEventListener("click", () =>
        openChat(
          developments.get(activeId) || developments.values().next().value,
          button,
        ),
      ),
    );
  mobile.addEventListener("change", setPanelSemantics);
  window.visualViewport?.addEventListener("resize", setPanelSemantics);
  window.visualViewport?.addEventListener("scroll", setPanelSemantics);
  panel.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      event.preventDefault();
      closeChat();
      return;
    }
    if (event.key === "Tab" && mobile.matches) {
      const focusables = [
        ...panel.querySelectorAll(
          'button:not(:disabled),a[href],textarea:not(:disabled),[tabindex="0"]',
        ),
      ].filter((el) => el.getClientRects().length);
      const first = focusables[0],
        last = focusables.at(-1);
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
  });
  function answerContent(el, text) {
    const chunks = text.split(/(\*\*[^*\n]+\*\*)/g);
    chunks.forEach((chunk) => {
      if (chunk.startsWith("**") && chunk.endsWith("**")) {
        const strong = document.createElement("strong");
        strong.textContent = chunk.slice(2, -2);
        el.append(strong);
      } else el.append(document.createTextNode(chunk));
    });
  }
  function element(tag, className, text) {
    const el = document.createElement(tag);
    el.className = className;
    if (text !== undefined) el.textContent = text;
    return el;
  }
  function formatTime(ts) {
    return typeof ts === "number"
      ? new Date(ts).toLocaleTimeString("tr-TR", {
          hour: "2-digit",
          minute: "2-digit",
        })
      : "";
  }
  const scrollBottomBtn = $("scroll-bottom-btn");
  function nearBottom() {
    return scroll.scrollHeight - scroll.scrollTop - scroll.clientHeight < 80;
  }
  function updateScrollBottomBtn() {
    scrollBottomBtn.hidden = nearBottom();
  }
  scroll.addEventListener("scroll", updateScrollBottomBtn);
  scrollBottomBtn.addEventListener("click", () => {
    scroll.scrollTo({ top: scroll.scrollHeight, behavior: "smooth" });
  });
  function renderConversation() {
    const dev = developments.get(activeId),
      session = activeId ? store.get(activeId) : null;
    $("chat-context").hidden = !dev;
    if (dev) {
      $("chat-title").textContent = dev.title;
      $("chat-source").textContent = `${dev.source} · ${dev.date}`;
      setLink($("chat-link"), dev.url);
    }
    $("chat-welcome").hidden = !!session?.turns.length;
    $("welcome-tip").textContent = dev
      ? "Aşağıdaki sorulardan birini seç veya kendi sorunu yaz."
      : "Başlamak için bir haberin “Soru sor” düğmesine dokun.";
    messages.replaceChildren();
    (session?.turns || []).forEach((turn, index) => {
      const row = element("div", "chat-turn");
      const userRow = element("div", "msg-row user-row");
      const userBubble = element("p", "user-message", turn.question);
      userBubble.append(element("span", "msg-time", formatTime(turn.ts)));
      userRow.append(userBubble, element("span", "avatar avatar-user", "Sen"));
      row.append(userRow);
      const botRow = element("div", "msg-row bot-row");
      const avatarBot = element("span", "avatar avatar-bot");
      const logo = document.createElement("img");
      logo.src = "/radar.svg";
      logo.alt = "";
      avatarBot.append(logo);
      const botCol = element("div", "bot-col");
      const label = element("div", "answer-label");
      label.append(
        document.createTextNode("Radar Asistanı"),
        element("span", "msg-time", formatTime(turn.ts)),
      );
      botCol.append(label);
      botRow.append(avatarBot, botCol);
      row.append(botRow);
      if (turn.status === "pending") {
        const loading = element(
          "div",
          "thinking",
          "Haberin bağlamı inceleniyor…",
        );
        loading.setAttribute("role", "status");
        botCol.append(loading);
      } else if (turn.status === "error") {
        const error = element("div", "chat-error", turn.error);
        error.setAttribute("role", "alert");
        {
          const retry = element("button", "retry-button", "Yeniden dene");
          retry.type = "button";
          retry.disabled = session.pending;
          retry.addEventListener("click", () => sendQuestion(null, index));
          error.append(document.createElement("br"), retry);
        }
        botCol.append(error);
      } else {
        const answer = element("div", "assistant-message");
        answerContent(answer, turn.answer);
        botCol.append(answer);
      }
      messages.append(row);
    });
    input.disabled = !dev;
    input.value = session?.draft || "";
    input.placeholder = session?.pending
      ? "Yanıt hazırlanıyor; sonraki sorunu yazabilirsin…"
      : "Bu haber hakkında bir soru sor…";
    $("send-chat").disabled = !dev || !!session?.pending || !input.value.trim();
    $("send-chat").setAttribute(
      "aria-label",
      session?.pending ? "Yanıt bekleniyor" : "Soruyu gönder",
    );
    document
      .querySelectorAll("[data-question]")
      .forEach((el) => (el.disabled = !dev || !!session?.pending));
    $("suggestions").querySelector("span").textContent = session?.turns.length
      ? "Biraz daha derine in"
      : "Bir soruyla başla";
    messages.setAttribute("aria-busy", String(!!session?.pending));
    sizeInput();
    requestAnimationFrame(() => {
      scroll.scrollTop = scroll.scrollHeight;
      updateScrollBottomBtn();
    });
  }
  async function sendQuestion(question, retryIndex = null) {
    if (!activeId || store.get(activeId).pending) return;
    const id = activeId;
    const history = store.history(id, retryIndex ?? Infinity);
    const text =
      retryIndex !== null
        ? store.retry(id, retryIndex)
        : (question || input.value).trim();
    if (!text) return;
    if (retryIndex === null) store.start(id, text);
    persist();
    renderConversation();
    try {
      const response = await fetch(
        `/developments/${encodeURIComponent(id)}/chat`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question: text, history }),
          signal: AbortSignal.timeout(95000),
        },
      );
      const data = await response.json().catch(() => ({}));
      if (
        !response.ok ||
        typeof data.answer !== "string" ||
        !data.answer.trim()
      )
        throw new Error(
          data.error || "Yanıt alınamadı. Yeniden deneyebilirsin.",
        );
      store.succeed(id, data.answer);
    } catch (error) {
      store.fail(
        id,
        error.name === "TimeoutError"
          ? "Yanıt beklenenden uzun sürdü. Yeniden deneyebilirsin."
          : error.message === "Failed to fetch"
            ? "Bağlantı kesildi. Yeniden deneyebilirsin."
            : error.message,
      );
    }
    persist();
    if (activeId === id) renderConversation();
  }
  $("chat-form").addEventListener("submit", (e) => {
    e.preventDefault();
    sendQuestion();
  });
  input.addEventListener("input", () => {
    if (!activeId) return;
    store.get(activeId).draft = input.value;
    persist();
    $("send-chat").disabled =
      store.get(activeId).pending || !input.value.trim();
    sizeInput();
  });
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey && !e.isComposing && !mobile.matches) {
      e.preventDefault();
      sendQuestion();
    }
  });
  document
    .querySelectorAll("[data-question]")
    .forEach((el) =>
      el.addEventListener("click", () => sendQuestion(el.dataset.question)),
    );

  const previewCache = new Map();
  function getPreview(id) {
    if (!previewCache.has(id))
      previewCache.set(
        id,
        fetch(`/developments/${encodeURIComponent(id)}/preview`)
          .then((r) => (r.ok ? r.json() : null))
          .catch(() => null),
      );
    return previewCache.get(id);
  }
  const modal = $("preview-modal");
  let previewId = null,
    previewTrigger = null;
  function closePreview() {
    modal.close();
    previewTrigger?.focus({ preventScroll: true });
  }
  document
    .querySelector(".preview-close")
    .addEventListener("click", closePreview);
  modal.addEventListener("click", (e) => {
    if (e.target === modal) {
      const r = modal.getBoundingClientRect();
      if (
        e.clientX < r.left ||
        e.clientX > r.right ||
        e.clientY < r.top ||
        e.clientY > r.bottom
      )
        closePreview();
    }
  });
  async function showPreview(dev, trigger) {
    previewId = String(dev.id);
    previewTrigger = trigger;
    $("preview-title").textContent = dev.title;
    $("preview-summary").textContent = dev.summary;
    $("preview-meta").textContent = `${dev.source} · ${dev.date}`;
    setLink($("preview-link"), dev.url);
    const img = $("preview-image");
    img.hidden = true;
    img.removeAttribute("src");
    modal.showModal();
    const data = await getPreview(previewId);
    if (previewId !== String(dev.id) || !modal.open) return;
    if (data?.image && safeUrl(data.image)) {
      img.onload = () => {
        img.hidden = false;
      };
      img.onerror = () => {
        img.hidden = true;
      };
      img.loading = "eager";
      img.src = data.image;
    }
  }
  $("preview-ask").addEventListener("click", () => {
    const dev = developments.get(previewId);
    modal.close();
    openChat(dev, previewTrigger);
  });
  function bindStory(el) {
    const dev = JSON.parse(el.dataset.dev);
    developments.set(String(dev.id), dev);
    el.querySelector('[data-action="chat"]').addEventListener("click", (e) =>
      openChat(dev, e.currentTarget),
    );
    el.querySelector('[data-action="preview"]').addEventListener("click", (e) =>
      showPreview(dev, e.currentTarget),
    );
  }
  stories.forEach(bindStory);
  let previewInFlight = 0;
  const previewQueue = [];
  async function drainPreviews() {
    while (previewInFlight < 3 && previewQueue.length) {
      const el = previewQueue.shift();
      previewInFlight++;
      getPreview(el.dataset.id)
        .then((data) => {
          const img = el.querySelector(".story-image");
          if (data?.image && safeUrl(data.image)) {
            img.onload = () => {
              img.hidden = false;
            };
            img.onerror = () => {
              img.hidden = true;
            };
            img.loading = "eager";
            img.src = data.image;
          }
        })
        .finally(() => {
          previewInFlight--;
          drainPreviews();
        });
    }
  }
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          observer.unobserve(entry.target);
          previewQueue.push(entry.target);
        }
      });
      drainPreviews();
    },
    { rootMargin: "150px" },
  );
  function updateList() {
    stories.forEach((el, index) => {
      el.hidden = index >= visibleCount;
      if (!el.hidden) observer.observe(el);
    });
    const more = document.querySelector(".load-more");
    more.hidden = stories.length <= 15;
    $("load-more").hidden = visibleCount >= stories.length;
    $("visible-count").textContent =
      `${Math.min(visibleCount, stories.length)} / ${stories.length} haber gösteriliyor`;
  }
  $("load-more").addEventListener("click", () => {
    const next = stories[visibleCount];
    visibleCount += 15;
    updateList();
    next?.querySelector(".title-button").focus({ preventScroll: true });
  });
  updateList();
  $("filter-toggle").addEventListener("click", () => {
    const fields = $("filter-fields");
    fields.hidden = !fields.hidden;
    $("filter-toggle").setAttribute("aria-expanded", String(!fields.hidden));
  });
  $("sort-select").addEventListener("change", () =>
    $("filters-form").requestSubmit(),
  );
  $("orig-toggle").addEventListener("change", (e) => {
    document
      .querySelectorAll(".original")
      .forEach((el) => (el.hidden = !e.target.checked));
    try {
      sessionStorage.setItem("radar-original", String(e.target.checked));
    } catch (_) {}
  });
  try {
    if (sessionStorage.getItem("radar-original") === "true") {
      $("orig-toggle").checked = true;
      document
        .querySelectorAll(".original")
        .forEach((el) => (el.hidden = false));
    }
  } catch (_) {}
  let manualRequestPending = false;
  let watchingManualScan = false;
  $("refresh-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    if (manualRequestPending) return;
    manualRequestPending = true;
    updateScanButton();
    const message = $("refresh-message");
    message.hidden = false;
    message.classList.remove("error");
    message.textContent = "Tarama başlatılıyor…";
    try {
      const response = await fetch("/refresh", {
        method: "POST", headers: { Accept: "application/json" },
        signal: AbortSignal.timeout(20000),
      });
      if (response.status !== 202 && response.status !== 409) throw new Error("Scan unavailable");
      watchingManualScan = true;
      $("scan-status").dataset.running = "true";
      message.textContent = response.status === 409
        ? "Tarama zaten devam ediyor. Yeni haberler hazır olduğunda görünecek."
        : "Tarama başladı. Haberler geldikçe akışa eklenecek; bu sayfada kalabilirsin.";
      await poller.check();
    } catch {
      message.classList.add("error");
      message.textContent = "Tarama isteği doğrulanamadı. Bağlantını kontrol edip yeniden deneyebilirsin.";
    } finally {
      manualRequestPending = false;
      updateScanButton();
    }
  });
  function updateScanButton() {
    const busy = manualRequestPending || $("scan-status").dataset.running === "true";
    const button = $("refresh-form").querySelector("button");
    button.disabled = busy;
    button.dataset.running = String(busy);
    button.querySelector("span").textContent = busy ? "Taranıyor…" : "Güncelle";
    button.setAttribute(
      "aria-label",
      busy ? "Haberler taranıyor" : "Haberleri güncelle",
    );
  }
  updateScanButton();
  const poller = new RadarLiveFeed.FeedPoller({
    enabled: () => !document.hidden && navigator.onLine,
    load: async () => {
      const response = await fetch(location.pathname + location.search, {
        cache: "no-store",
        signal: AbortSignal.timeout(20000),
      });
      if (!response.ok) throw new Error("Feed unavailable");
      const fresh = new DOMParser().parseFromString(
        await response.text(),
        "text/html",
      );
      if (
        !fresh.getElementById("news-list") ||
        !fresh.getElementById("scan-status")
      )
        throw new Error("Invalid feed");
      return fresh;
    },
    apply: (fresh) => {
      const anchor =
        window.scrollY > 100
          ? stories.find(
              (el) => !el.hidden && el.getBoundingClientRect().bottom > 0,
            )
          : null;
      const top = anchor?.getBoundingClientRect().top;
      const result = RadarLiveFeed.mergeNews(document, fresh, bindStory);
      stories = result.stories;
      visibleCount += result.added;
      stories.forEach((el) => {
        el.classList.toggle("is-active", el.dataset.id === activeId);
        const original = el.querySelector(".original");
        if (original) original.hidden = !$("orig-toggle").checked;
      });
      updateList();
      $("feed-heading").replaceChildren(
        ...[...fresh.getElementById("feed-heading").childNodes].map((node) =>
          document.importNode(node, true),
        ),
      );
      $("scan-status").replaceWith(
        document.importNode(fresh.getElementById("scan-status"), true),
      );
      if (watchingManualScan && $("scan-status").dataset.running !== "true") {
        const failed = ["failed", "interrupted"].includes($("scan-status").dataset.status);
        const message = $("refresh-message");
        message.classList.toggle("error", failed);
        message.textContent = failed
          ? "Tarama tamamlanamadı. Son haberler korunuyor; yeniden deneyebilirsin."
          : `Tarama tamamlandı · ${$("scan-status").dataset.count || 0} yeni haber. Tarih ve kaynak filtrelerin korunuyor.`;
        watchingManualScan = false;
      }
      const digest = $("digest-region"),
        nextDigest = fresh.getElementById("digest-region");
      if (
        nextDigest &&
        !digest.querySelector("details[open]") &&
        !digest.contains(document.activeElement) &&
        digest.innerHTML !== nextDigest.innerHTML
      )
        digest.replaceChildren(
          ...[...nextDigest.childNodes].map((node) =>
            document.importNode(node, true),
          ),
        );
      updateScanButton();
      if (
        anchor?.isConnected &&
        !document.body.classList.contains("chat-open")
      ) {
        window.scrollBy({
          top: anchor.getBoundingClientRect().top - top,
          behavior: "instant",
        });
      }
      $("live-update-message").classList.remove("is-error");
      $("live-update-message").textContent = result.added
        ? `${result.added} yeni haber otomatik eklendi.`
        : $("scan-status").dataset.running === "true"
          ? "Tarama sürüyor · 10 saniyede bir kontrol"
          : "Yeni haberler otomatik eklenir · Dakikada bir kontrol";
    },
    error: () => {
      $("live-update-message").classList.add("is-error");
      $("live-update-message").textContent =
        "Canlı bağlantı kurulamadı. Haberler korunuyor; yeniden denenecek.";
    },
  });
  setInterval(() => {
    if ($("scan-status").dataset.running === "true") return poller.check();
  }, 10000);
  setInterval(() => poller.check(), 60000);
  document.addEventListener("visibilitychange", () => poller.check());
  window.addEventListener("online", () => poller.check());
  window.addEventListener("offline", () => {
    $("live-update-message").classList.add("is-error");
    $("live-update-message").textContent =
      "Çevrimdışısın. Bağlantı geldiğinde haberler otomatik güncellenecek.";
  });
  window.addEventListener("pageshow", () => poller.check());
  if (!mobile.matches)
    openChat(developments.values().next().value, null, false);
})();
