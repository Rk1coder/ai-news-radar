(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const modal = $("settings-modal");
  const sourceTypeLabels = {
    academic: "Akademik",
    company: "Şirket",
    media: "Medya",
    defense: "Savunma Sanayii",
    social: "Sosyal Medya",
  };
  let data = null;
  let pendingSources = new Map();

  async function api(url, options) {
    const response = await fetch(url, {
      headers: options?.body ? { "Content-Type": "application/json" } : undefined,
      ...options,
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.error || "İstek başarısız oldu.");
    return body;
  }

  function findSource(name) {
    return data.sources.find((s) => s.name === name);
  }
  function sourceEnabled(name) {
    return pendingSources.has(name) ? pendingSources.get(name) : !!findSource(name)?.enabled;
  }
  function pendingInterval() {
    const checked = document.querySelector(
      '#scan-interval-group input[name="scan-interval"]:checked',
    );
    return Number(checked?.value ?? data.scan.interval_minutes ?? 15);
  }
  function scanDirty() {
    return (
      pendingInterval() !== data.scan.interval_minutes ||
      $("auto-scan-enabled").checked !== !!data.scan.auto_scan_enabled
    );
  }
  function sourcesDirty() {
    return [...pendingSources.entries()].some(
      ([name, enabled]) => enabled !== !!findSource(name)?.enabled,
    );
  }

  function renderScan() {
    const val = String(data.scan.interval_minutes ?? 15);
    document
      .querySelectorAll('#scan-interval-group input[name="scan-interval"]')
      .forEach((r) => (r.checked = r.value === val));
    $("auto-scan-enabled").checked = !!data.scan.auto_scan_enabled;
    $("interval-changed").hidden = true;
    $("auto-scan-changed").hidden = true;
  }

  function renderSources() {
    const filter = $("source-filter").value.trim().toLowerCase();
    const builtin = data.sources.filter((s) => s.builtin);
    const custom = data.sources.filter((s) => !s.builtin);
    const groups = new Map();
    builtin
      .filter((s) => !filter || s.name.toLowerCase().includes(filter))
      .forEach((s) => {
        if (!groups.has(s.source_type)) groups.set(s.source_type, []);
        groups.get(s.source_type).push(s);
      });
    $("source-list").innerHTML =
      [...groups.entries()]
        .map(
          ([type, items]) =>
            `<fieldset><legend>${sourceTypeLabels[type] || type}</legend>${items
              .map((s) => {
                const enabled = sourceEnabled(s.name);
                const changed = enabled !== !!s.enabled;
                return `<label class="source-row"><span class="row-label">${s.name}${changed ? ' <span class="badge-changed">Değişti</span>' : ""}</span><span class="switch"><input type="checkbox" data-source="${s.name}" ${enabled ? "checked" : ""}></span></label>`;
              })
              .join("")}</fieldset>`,
        )
        .join("") || `<p class="muted">Eşleşen kaynak yok.</p>`;
    $("custom-source-list").innerHTML = custom.length
      ? custom
          .map(
            (s) =>
              `<div class="custom-source-row"><span>${s.name} · ${s.feed_url}</span><button type="button" class="icon-button" data-remove="${s.id}" aria-label="${s.name} kaynağını kaldır">✕</button></div>`,
          )
          .join("")
      : `<p class="muted">Henüz özel kaynak eklenmedi.</p>`;
  }

  function updateFooter() {
    const dirty = scanDirty() || sourcesDirty();
    $("settings-footer").hidden = !dirty;
    if (dirty) $("settings-footer-status").textContent = "Kaydedilmemiş değişiklikler var";
    $("interval-changed").hidden = pendingInterval() === data.scan.interval_minutes;
    $("auto-scan-changed").hidden =
      $("auto-scan-enabled").checked === !!data.scan.auto_scan_enabled;
  }

  function render() {
    renderScan();
    renderSources();
    updateFooter();
  }

  async function load() {
    data = await api("/settings-api");
    pendingSources = new Map();
    render();
  }

  function openSettings() {
    modal.showModal();
    $("custom-add-status").textContent = "";
    load().catch((e) => {
      $("settings-footer-status").textContent = e.message;
      $("settings-footer").hidden = false;
    });
  }

  document.querySelectorAll("#open-settings").forEach((btn) => btn.addEventListener("click", openSettings));
  $("close-settings").addEventListener("click", () => modal.close());

  document.querySelectorAll(".settings-nav-item").forEach((btn) => {
    btn.addEventListener("click", () => {
      document
        .querySelectorAll(".settings-nav-item")
        .forEach((b) => b.classList.toggle("is-active", b === btn));
      document
        .querySelectorAll(".settings-section[data-panel]")
        .forEach((sec) => (sec.hidden = sec.dataset.panel !== btn.dataset.panel));
    });
  });

  modal.addEventListener("click", (e) => {
    if (e.target !== modal) return;
    const r = modal.getBoundingClientRect();
    if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) modal.close();
  });

  $("scan-interval-group").addEventListener("change", () => {
    $("interval-changed").hidden = pendingInterval() === data.scan.interval_minutes;
    updateFooter();
  });
  $("auto-scan-enabled").addEventListener("change", updateFooter);

  $("source-filter").addEventListener("input", renderSources);

  $("source-list").addEventListener("change", (e) => {
    const name = e.target.dataset.source;
    if (!name) return;
    pendingSources.set(name, e.target.checked);
    renderSources();
    updateFooter();
  });

  $("settings-cancel").addEventListener("click", () => {
    pendingSources = new Map();
    render();
  });

  $("settings-save").addEventListener("click", async () => {
    $("settings-footer-status").textContent = "Kaydediliyor…";
    try {
      if (scanDirty()) {
        data = await api("/settings-api/scan", {
          method: "PUT",
          body: JSON.stringify({
            interval_minutes: pendingInterval(),
            auto_scan_enabled: $("auto-scan-enabled").checked,
          }),
        });
      }
      for (const [name, enabled] of pendingSources.entries()) {
        if (enabled === !!findSource(name)?.enabled) continue;
        data = await api(`/settings-api/sources/${encodeURIComponent(name)}`, {
          method: "PUT",
          body: JSON.stringify({ enabled }),
        });
      }
      pendingSources = new Map();
      render();
      $("settings-footer-status").textContent = "Kaydedildi.";
      $("settings-footer").hidden = true;
    } catch (e) {
      $("settings-footer-status").textContent = e.message;
    }
  });

  $("custom-source-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    $("custom-add-status").textContent = "Ekleniyor…";
    try {
      data = await api("/settings-api/sources/custom", {
        method: "POST",
        body: JSON.stringify({
          name: $("custom-name").value.trim(),
          feed_url: $("custom-url").value.trim(),
          source_type: $("custom-type").value,
        }),
      });
      e.target.reset();
      $("custom-add-status").textContent = "Eklendi.";
      renderSources();
    } catch (err) {
      $("custom-add-status").textContent = err.message;
    }
  });

  $("custom-source-list").addEventListener("click", async (e) => {
    const id = e.target.dataset.remove;
    if (!id) return;
    try {
      data = await api(`/settings-api/sources/custom/${id}`, { method: "DELETE" });
      renderSources();
    } catch {
      /* leave the row; the user can retry */
    }
  });
})();
