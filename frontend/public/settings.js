(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const modal = $("settings-modal");
  const trigger = $("open-settings");
  const motion = window.createSettingsMotion(modal, trigger);
  const tabs = [...modal.querySelectorAll(".settings-nav-item")];
  const sections = [...modal.querySelectorAll(".settings-section[data-panel]")];
  const horizontalNav = window.matchMedia("(max-width: 600px)");
  const setOrientation = () => modal.querySelector(".settings-nav").setAttribute("aria-orientation", horizontalNav.matches ? "horizontal" : "vertical");
  setOrientation();
  horizontalNav.addEventListener?.("change", setOrientation);
  const sourceTypeLabels = {
    academic: "Akademik",
    company: "Şirket",
    media: "Medya",
    defense: "Savunma Sanayii",
    social: "Sosyal Medya",
  };
  let data = null;
  let pendingSources = new Map();
  let loadVersion = 0;
  let loadController;
  const programEditor = window.createScanProgramEditor($("scan-program-editor"), updateFooter);
  const emptyProgram = { times: [], windows: [] };

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
      $("auto-scan-enabled").checked !== !!data.scan.auto_scan_enabled || programDirty()
    );
  }
  function programDirty() {
    return JSON.stringify(programEditor.getProgram()) !== JSON.stringify(data.scan.program || emptyProgram);
  }
  function showProgram() {
    $("scan-program-editor").hidden = pendingInterval() !== 0;
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
    programEditor.setProgram(data.scan.program, data.scan.timezone);
    showProgram();
  }

  function renderSources() {
    if (!data) return;
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
    if (!data) return;
    const dirty = scanDirty() || sourcesDirty();
    $("settings-footer").hidden = !dirty;
    if (dirty) $("settings-footer-status").textContent = "Kaydedilmemiş değişiklikler var";
    $("interval-changed").hidden = pendingInterval() === data.scan.interval_minutes && !programDirty();
    $("auto-scan-changed").hidden =
      $("auto-scan-enabled").checked === !!data.scan.auto_scan_enabled;
  }

  function render() {
    renderScan();
    renderSources();
    updateFooter();
  }

  async function load() {
    const version = ++loadVersion;
    loadController?.abort();
    loadController = new AbortController();
    data = null;
    pendingSources = new Map();
    $("settings-footer").hidden = true;
    $("settings-load-notice").hidden = false;
    $("settings-load-status").textContent = "Ayarlar yükleniyor…";
    $("settings-retry").hidden = true;
    sections.filter((section) => section.dataset.panel !== "appearance")
      .forEach((section) => { section.inert = true; });
    try {
      const result = await api("/settings-api", { signal: loadController.signal });
      if (version !== loadVersion || !modal.open) return;
      data = result;
      $("settings-save").disabled = false;
      render();
      sections.forEach((section) => { section.inert = false; });
      $("settings-load-notice").hidden = true;
    } catch (error) {
      if (version !== loadVersion || !modal.open) return;
      $("settings-load-status").textContent = error.message;
      $("settings-retry").hidden = false;
    }
  }

  function currentThemePref() {
    try {
      const t = localStorage.getItem("radar-theme");
      return t === "light" || t === "dark" ? t : "system";
    } catch {
      return "system";
    }
  }
  function applyTheme(pref) {
    if (pref === "light" || pref === "dark") document.documentElement.dataset.theme = pref;
    else delete document.documentElement.dataset.theme;
    try {
      localStorage.setItem("radar-theme", pref);
    } catch {
      /* theme still applies for this page load */
    }
  }
  function renderTheme() {
    const pref = currentThemePref();
    document
      .querySelectorAll('#theme-group input[name="theme-pref"]')
      .forEach((r) => (r.checked = r.value === pref));
  }
  $("theme-group").addEventListener("change", (e) => applyTheme(e.target.value));

  function openSettings() {
    if (modal.open) return;
    motion.open();
    $("custom-add-status").textContent = "";
    renderTheme();
    load();
  }

  document.querySelectorAll("#open-settings").forEach((btn) => btn.addEventListener("click", openSettings));
  $("close-settings").addEventListener("click", motion.close);
  $("settings-retry").addEventListener("click", load);
  modal.addEventListener("close", () => {
    if (modal.open) return;
    ++loadVersion;
    loadController?.abort();
  });

  function selectTab(selected) {
    tabs.forEach((tab) => {
      const active = tab === selected;
      tab.classList.toggle("is-active", active);
      tab.setAttribute("aria-selected", String(active));
      tab.tabIndex = active ? 0 : -1;
    });
    sections.forEach((section) => { section.hidden = section.dataset.panel !== selected.dataset.panel; });
    $("settings-body").scrollTop = 0;
    motion.reveal(sections.find((section) => !section.hidden));
  }
  tabs.forEach((tab, index) => {
    tab.addEventListener("click", () => selectTab(tab));
    tab.addEventListener("keydown", (event) => {
      let next;
      if (event.key === "ArrowRight" || event.key === "ArrowDown") next = (index + 1) % tabs.length;
      if (event.key === "ArrowLeft" || event.key === "ArrowUp") next = (index - 1 + tabs.length) % tabs.length;
      if (event.key === "Home") next = 0;
      if (event.key === "End") next = tabs.length - 1;
      if (next === undefined) return;
      event.preventDefault();
      selectTab(tabs[next]);
      tabs[next].focus();
    });
  });

  modal.addEventListener("click", (e) => {
    if (e.target !== modal) return;
    const r = modal.getBoundingClientRect();
    if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) motion.close();
  });

  $("scan-interval-group").addEventListener("change", () => {
    if (!data) return;
    showProgram();
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
    if (!data) return;
    pendingSources = new Map();
    render();
  });

  $("settings-save").addEventListener("click", async () => {
    if (!data) return;
    if (pendingInterval() === 0) {
      const program = programEditor.getProgram();
      if (!program.times.length && !program.windows.length) selectTab(tabs.find((tab) => tab.dataset.panel === "scan"));
      if (!programEditor.validate()) return;
    }
    const version = loadVersion;
    const current = () => version === loadVersion && modal.open;
    const scanChange = scanDirty() ? {
      interval_minutes: pendingInterval(),
      auto_scan_enabled: $("auto-scan-enabled").checked,
    } : null;
    if (scanChange && (programDirty() || pendingInterval() === 0)) scanChange.program = programEditor.getProgram();
    const sourceChanges = [...pendingSources.entries()].filter(
      ([name, enabled]) => enabled !== !!findSource(name)?.enabled,
    );
    let savedData = data;
    $("settings-save").disabled = true;
    $("settings-footer-status").textContent = "Kaydediliyor…";
    try {
      if (scanChange) {
        savedData = await api("/settings-api/scan", {
          method: "PUT",
          body: JSON.stringify(scanChange),
        });
      }
      // Complete the submitted snapshot even if the user closes the dialog.
      // Only rendering belongs to the opening that initiated the save.
      for (const [name, enabled] of sourceChanges) {
        savedData = await api(`/settings-api/sources/${encodeURIComponent(name)}`, {
          method: "PUT",
          body: JSON.stringify({ enabled }),
        });
      }
      if (!current()) return;
      data = savedData;
      pendingSources = new Map();
      render();
      $("settings-footer-status").textContent = "Kaydedildi.";
      $("settings-footer").hidden = true;
    } catch (e) {
      if (current()) {
        data = savedData;
        updateFooter();
        $("settings-footer-status").textContent = e.message;
        $("settings-footer").hidden = false;
      }
    } finally {
      if (current()) $("settings-save").disabled = false;
    }
  });

  $("custom-source-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!data) return;
    const version = loadVersion;
    $("custom-add-status").textContent = "Ekleniyor…";
    try {
      const result = await api("/settings-api/sources/custom", {
        method: "POST",
        body: JSON.stringify({
          name: $("custom-name").value.trim(),
          feed_url: $("custom-url").value.trim(),
          source_type: $("custom-type").value,
        }),
      });
      if (version !== loadVersion || !modal.open) return;
      data = result;
      e.target.reset();
      $("custom-add-status").textContent = "Eklendi.";
      renderSources();
    } catch (err) {
      if (version === loadVersion && modal.open) $("custom-add-status").textContent = err.message;
    }
  });

  $("custom-source-list").addEventListener("click", async (e) => {
    const id = e.target.dataset.remove;
    if (!id || !data) return;
    const version = loadVersion;
    try {
      const result = await api(`/settings-api/sources/custom/${id}`, { method: "DELETE" });
      if (version !== loadVersion || !modal.open) return;
      data = result;
      renderSources();
    } catch {
      /* leave the row; the user can retry */
    }
  });
})();
