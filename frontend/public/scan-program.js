(() => {
  "use strict";
  window.createScanProgramEditor = (root, onChange) => {
    const $ = (id) => root.querySelector(`#${id}`);
    const timePattern = /^(?:[01][0-9]|2[0-3]):[0-5][0-9]$/;
    const cadences = [5, 10, 15, 20, 30, 60];
    let program = { times: [], windows: [] };

    function message(text = "") {
      $("program-error").textContent = text;
      $("program-error").hidden = !text;
    }
    function element(tag, className, text) {
      const el = document.createElement(tag);
      el.className = className;
      if (text) el.textContent = text;
      return el;
    }
    function removeButton(label, action) {
      const button = element("button", "program-remove", "×");
      button.type = "button";
      button.setAttribute("aria-label", label);
      button.addEventListener("click", () => { action(); changed(); });
      return button;
    }
    function render() {
      $("program-time-list").replaceChildren(...program.times.map((time) => {
        const chip = element("span", "program-chip");
        chip.append(element("span", "", time), removeButton(`${time} saatini kaldır`, () => {
          program.times = program.times.filter((value) => value !== time);
        }));
        return chip;
      }));
      $("program-window-list").replaceChildren(...program.windows.map((window, index) => {
        const row = element("div", "program-window");
        const text = element("div", "program-window-text");
        text.append(element("strong", "", `${window.start}–${window.end}`));
        const overnight = window.end < window.start ? " · ertesi güne kadar" : "";
        text.append(element("span", "", `Her ${window.interval_minutes} dakikada bir${overnight}`));
        row.append(text, removeButton(`${window.start}–${window.end} aralığını kaldır`, () => program.windows.splice(index, 1)));
        return row;
      }));
      $("program-times-empty").hidden = program.times.length > 0;
      $("program-windows-empty").hidden = program.windows.length > 0;
    }
    function changed() {
      program.times.sort();
      program.windows.sort((a, b) => a.start.localeCompare(b.start) || a.end.localeCompare(b.end) || a.interval_minutes - b.interval_minutes);
      message();
      render();
      onChange();
    }
    function addTime() {
      const time = $("program-time").value;
      if (!timePattern.test(time)) { message("Geçerli bir tarama saati seç."); return; }
      if (program.times.includes(time)) { message("Bu saat zaten programda var."); return; }
      if (program.times.length >= 48) { message("En fazla 48 tarama saati ekleyebilirsin."); return; }
      program.times.push(time);
      $("program-time").value = "";
      changed();
    }
    function addWindow() {
      const start = $("program-start").value;
      const end = $("program-end").value;
      const interval_minutes = Number($("program-cadence").value);
      if (!timePattern.test(start) || !timePattern.test(end)) { message("Başlangıç ve bitiş saatlerini seç."); return; }
      if (start === end) { message("Başlangıç ve bitiş saatleri aynı olamaz."); return; }
      if (!cadences.includes(interval_minutes)) { message("Geçerli bir tekrar aralığı seç."); return; }
      if (program.windows.some((window) => window.start === start && window.end === end && window.interval_minutes === interval_minutes)) {
        message("Bu zaman aralığı zaten programda var."); return;
      }
      if (program.windows.length >= 12) { message("En fazla 12 zaman aralığı ekleyebilirsin."); return; }
      program.windows.push({ start, end, interval_minutes });
      changed();
    }
    $("program-add-time").addEventListener("click", addTime);
    $("program-add-window").addEventListener("click", addWindow);
    $("program-time").addEventListener("keydown", (event) => {
      if (event.key === "Enter") { event.preventDefault(); addTime(); }
    });
    return {
      getProgram: () => ({ times: [...program.times], windows: program.windows.map((window) => ({ ...window })) }),
      setProgram(value, timezone = "Europe/Istanbul") {
        program = { times: [...(value?.times || [])], windows: (value?.windows || []).map((window) => ({ ...window })) };
        $("program-timezone").textContent = timezone;
        $("program-time").value = "";
        message();
        render();
      },
      validate() {
        const valid = program.times.length > 0 || program.windows.length > 0;
        message(valid ? "" : "En az bir tarama saati veya zaman aralığı ekle.");
        if (!valid) $("program-time").focus();
        return valid;
      },
    };
  };
})();
