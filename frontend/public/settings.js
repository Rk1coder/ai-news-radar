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

  async function api(url, options) {
    const response = await fetch(url, {
      headers: options?.body ? { "Content-Type": "application/json" } : undefined,
      ...options,
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.error || "İstek başarısız oldu.");
    return body;
  }

  function renderScan() {
    $("scan-interval").value = String(data.scan.interval_minutes ?? 15);
    $("auto-scan-enabled").checked = !!data.scan.auto_scan_enabled;
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
              .map(
                (s) =>
                  `<label class="checkbox"><input type="checkbox" data-source="${s.name}" ${s.enabled ? "checked" : ""}> ${s.name}</label>`,
              )
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

  function render() {
    renderScan();
    renderSources();
  }

  async function load() {
    data = await api("/settings-api");
    render();
  }

  function openSettings() {
    modal.showModal();
    $("scan-save-status").textContent = "";
    $("custom-add-status").textContent = "";
    load().catch((e) => {
      $("scan-save-status").textContent = e.message;
    });
  }

  document.querySelectorAll("#open-settings").forEach((btn) => btn.addEventListener("click", openSettings));
  $("close-settings").addEventListener("click", () => modal.close());
  modal.addEventListener("click", (e) => {
    if (e.target !== modal) return;
    const r = modal.getBoundingClientRect();
    if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) modal.close();
  });

  $("save-scan").addEventListener("click", async () => {
    $("scan-save-status").textContent = "Kaydediliyor…";
    try {
      data = await api("/settings-api/scan", {
        method: "PUT",
        body: JSON.stringify({
          interval_minutes: Number($("scan-interval").value),
          auto_scan_enabled: $("auto-scan-enabled").checked,
        }),
      });
      render();
      $("scan-save-status").textContent = "Kaydedildi.";
    } catch (e) {
      $("scan-save-status").textContent = e.message;
    }
  });

  $("source-filter").addEventListener("input", renderSources);

  $("source-list").addEventListener("change", async (e) => {
    const name = e.target.dataset.source;
    if (!name) return;
    try {
      data = await api(`/settings-api/sources/${encodeURIComponent(name)}`, {
        method: "PUT",
        body: JSON.stringify({ enabled: e.target.checked }),
      });
      renderSources();
    } catch {
      e.target.checked = !e.target.checked;
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
