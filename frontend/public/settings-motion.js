/* Motion adapted from https://codepen.io/GreenSock/pen/JoRMPLg.
   The native dialog owns focus containment; GSAP only controls presentation. */
(() => {
  "use strict";
  window.createSettingsMotion = (modal, trigger) => {
    const island = modal.querySelector(".settings-island");
    const content = modal.querySelector(".settings-inner");
    const nav = [...modal.querySelectorAll(".settings-nav-item")];
    const heading = modal.querySelector(".settings-island-heading");
    const closeButton = modal.querySelector(".settings-close");
    const backdrop = document.createElement("div");
    backdrop.className = "settings-shade";
    backdrop.setAttribute("aria-hidden", "true");
    modal.prepend(backdrop);
    const gsap = window.gsap;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
    let timeline;
    let sectionTween;
    let closing = false;
    let origin;

    function stop() {
      timeline?.kill();
      sectionTween?.kill();
      if (gsap) gsap.set([island, content, heading, closeButton, backdrop, ...nav, ...modal.querySelectorAll(".settings-section")], { clearProps: "transform,opacity,visibility,clipPath,width" });
    }

    function position() {
      const source = trigger.getBoundingClientRect();
      const width = modal.offsetWidth;
      const height = modal.offsetHeight;
      const left = Math.max(16, Math.min(source.right - width, window.innerWidth - width - 16));
      const top = Math.max(16, Math.min(source.top, window.innerHeight - height - 16));
      modal.style.left = `${left}px`;
      modal.style.top = `${top}px`;
      origin = {
        x: source.left - left,
        y: source.top - top,
        width: source.width || 44,
      };
    }

    function cleanup() {
      stop();
      closing = false;
      document.body.classList.remove("settings-open");
      trigger.setAttribute("aria-expanded", "false");
      trigger.focus({ preventScroll: true });
    }

    function finishClose() {
      modal.close();
      // Native close events are queued: clean up before another opening can start.
      cleanup();
    }

    function close() {
      if (!modal.open || closing) return;
      closing = true;
      trigger.setAttribute("aria-expanded", "false");
      if (!gsap || reduced.matches) { finishClose(); return; }
      // Capture the current state, so closing during entry never jumps to its end.
      timeline?.kill();
      sectionTween?.kill();
      timeline = gsap.timeline({ onComplete: finishClose });
      timeline.to([heading, closeButton], { opacity: 0, duration: 0.1 }, 0)
        .to(nav, { opacity: 0, y: -6, duration: 0.12, stagger: { each: 0.02, from: "end" } }, 0)
        .to(content, { opacity: 0, y: -10, scaleY: 0.96, duration: 0.2, ease: "power2.in" }, 0.03)
        .to(backdrop, { opacity: 0, duration: 0.28 }, 0)
        .to(island, { x: origin.x, y: origin.y, width: origin.width, duration: 0.3, ease: "power2.inOut" }, 0.08);
    }

    function open() {
      if (modal.open) return;
      closing = false;
      stop();
      modal.showModal();
      document.body.classList.add("settings-open");
      trigger.setAttribute("aria-expanded", "true");
      position();
      if (!gsap || reduced.matches) return;
      timeline = gsap.timeline();
      timeline.from(island, { x: origin.x, y: origin.y, width: origin.width, duration: 0.54, ease: "back.out(1.1)" }, 0)
        .from(backdrop, { opacity: 0, duration: 0.35 }, 0)
        .from([heading, closeButton], { opacity: 0, duration: 0.18 }, 0.19)
        .from(content, { opacity: 0, y: -14, scaleY: 0.94, duration: 0.36, ease: "power3.out" }, 0.16)
        .from(nav, { opacity: 0, y: -12, duration: 0.28, stagger: 0.055, ease: "power3.out" }, 0.25);
    }

    function reveal(section) {
      sectionTween?.kill();
      if (!gsap || reduced.matches || closing) return;
      gsap.set(modal.querySelectorAll(".settings-section"), { clearProps: "transform,opacity" });
      sectionTween = gsap.fromTo(section, { opacity: 0, y: 8 }, {
        opacity: 1, y: 0, duration: 0.22, ease: "power2.out", clearProps: "transform,opacity",
      });
    }

    modal.addEventListener("cancel", (event) => { event.preventDefault(); close(); });
    modal.addEventListener("close", () => {
      if (!modal.open) cleanup();
    });
    backdrop.addEventListener("click", close);
    window.addEventListener("resize", () => {
      if (!modal.open || closing) return;
      stop();
      position();
    });
    reduced.addEventListener?.("change", () => {
      if (!reduced.matches || !modal.open) return;
      if (closing) finishClose();
      else stop();
    });
    return { open, close, reveal };
  };
})();
