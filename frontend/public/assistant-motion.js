/* Keep the assistant's capsule/reveal timing in step with settings-motion.js. */
(() => {
  "use strict";
  window.createAssistantMotion = (panel) => {
    const header = panel.querySelector(".assistant-header");
    const content = panel.querySelector(".assistant-content");
    const heading = panel.querySelector(".assistant-name");
    const closeButton = panel.querySelector("#close-chat");
    const parts = [...content.children];
    const gsap = window.gsap;
    const reduced = matchMedia("(prefers-reduced-motion: reduce)");
    let timeline;
    let phase = "closed";
    let origin;
    let onClosed;

    function stop(clear = true) {
      timeline?.kill();
      if (clear && gsap) gsap.set([header, content, heading, closeButton, ...parts], {
        clearProps: "transform,opacity,visibility,width",
      });
    }

    function anchorOrigin(source) {
      const target = panel.getBoundingClientRect();
      return source?.width ? {
        x: source.left - target.left,
        y: Math.max(16, Math.min(source.top, innerHeight - 60)) - target.top,
        width: Math.min(source.width, target.width || source.width),
      } : { x: Math.max(0, target.width - 44), y: 0, width: 44 };
    }

    function open(source) {
      if (phase === "open" || phase === "opening") return;
      stop();
      onClosed = null;
      phase = "open";
      const target = panel.getBoundingClientRect();
      origin = anchorOrigin(source);
      if (!gsap || reduced.matches) return;
      phase = "opening";
      gsap.set(header, origin);
      timeline = gsap.timeline({ onComplete: () => { phase = "open"; stop(); } });
      timeline.to(header, { width: target.width || "100%", duration: 0.48, ease: "back.out(0.8)" }, 0)
        .to(header, { x: 0, y: 0, duration: 0.4, ease: "power3.out" }, 0)
        .from([heading, closeButton], { opacity: 0, duration: 0.18 }, 0.19)
        .from(content, { opacity: 0, y: -14, scaleY: 0.94, duration: 0.36, ease: "power3.out" }, 0.16)
        .from(parts.filter((part) => !part.hidden), { opacity: 0, y: -12, duration: 0.28, stagger: 0.055, ease: "power3.out" }, 0.25);
    }

    function finishClose() {
      const callback = onClosed;
      onClosed = null;
      phase = "closed";
      stop();
      callback?.();
    }

    function close(callback, source) {
      if (phase === "closing") return;
      onClosed = callback;
      phase = "closing";
      if (source) origin = anchorOrigin(source);
      if (!gsap || reduced.matches) { finishClose(); return; }
      stop(false);
      timeline = gsap.timeline({ onComplete: finishClose });
      timeline.to([heading, closeButton], { opacity: 0, duration: 0.1 }, 0)
        .to(parts, { opacity: 0, y: -6, duration: 0.12, stagger: { each: 0.02, from: "end" } }, 0)
        .to(content, { opacity: 0, y: -10, scaleY: 0.96, duration: 0.2, ease: "power2.in" }, 0.03)
        .to(header, { ...origin, duration: 0.3, ease: "power2.inOut" }, 0.08);
    }

    function settle() {
      if (phase === "closed") return;
      if (phase === "closing") finishClose();
      else { phase = "open"; stop(); }
    }
    window.addEventListener("resize", settle);
    window.visualViewport?.addEventListener("resize", settle);
    reduced.addEventListener?.("change", () => { if (reduced.matches) settle(); });
    return { open, close, isClosing: () => phase === "closing" };
  };
})();
