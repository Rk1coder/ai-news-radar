(function (root) {
  "use strict";
  class ConversationStore {
    constructor(saved) {
      this.sessions = Object.create(null);
      try {
        const parsed = typeof saved === "string" ? JSON.parse(saved) : saved;
        for (const [id, value] of Object.entries(parsed || {}).slice(-40)) {
          if (!value || !Array.isArray(value.turns)) continue;
          this.sessions[id] = {
            draft:
              typeof value.draft === "string" ? value.draft.slice(0, 4000) : "",
            pending: false,
            pendingIndex: null,
            turns: value.turns
              .filter((t) => t && typeof t.question === "string")
              .slice(-30)
              .map((t) => ({
                question: t.question.slice(0, 4000),
                answer: typeof t.answer === "string" ? t.answer : "",
                status: t.status === "done" ? "done" : "error",
                ts: typeof t.ts === "number" ? t.ts : Date.now(),
                error:
                  t.status === "pending"
                    ? "Yanıt yarıda kaldı. Yeniden deneyebilirsin."
                    : typeof t.error === "string"
                      ? t.error
                      : "Yanıt alınamadı.",
              })),
          };
        }
      } catch (_) {
        /* An unavailable/corrupt cache must never block the chat. */
      }
    }
    get(id) {
      return (this.sessions[String(id)] ||= {
        turns: [],
        draft: "",
        pending: false,
        pendingIndex: null,
      });
    }
    history(id, beforeIndex = Infinity) {
      const turns = this.get(id)
        .turns.filter((t, index) => index < beforeIndex && t.status === "done")
        .slice(-12);
      let history = [];
      for (const turn of turns.reverse()) {
        const candidate = [
          { role: "user", content: turn.question },
          { role: "assistant", content: turn.answer },
          ...history,
        ];
        if (
          new TextEncoder().encode(JSON.stringify(candidate)).byteLength > 48000
        )
          break;
        history = candidate;
      }
      return history;
    }
    start(id, question) {
      const s = this.get(id);
      if (s.pending) throw new Error("Yanıt bekleniyor.");
      if (!question.trim()) throw new Error("Bir soru yaz.");
      s.turns.push({
        question: question.trim(),
        answer: "",
        status: "pending",
        error: "",
        ts: Date.now(),
      });
      s.pending = true;
      s.pendingIndex = s.turns.length - 1;
      s.draft = "";
    }
    succeed(id, answer) {
      const s = this.get(id),
        turn = s.turns[s.pendingIndex];
      if (!s.pending || !turn) return;
      turn.answer = answer;
      turn.status = "done";
      turn.error = "";
      s.pending = false;
    }
    fail(id, error) {
      const s = this.get(id),
        turn = s.turns[s.pendingIndex];
      if (!s.pending || !turn) return;
      turn.status = "error";
      turn.error = error;
      s.pending = false;
    }
    retry(id, index = this.get(id).turns.length - 1) {
      const s = this.get(id),
        turn = s.turns[index];
      if (s.pending || !turn || turn.status !== "error")
        throw new Error("Yeniden denenecek soru yok.");
      turn.status = "pending";
      turn.error = "";
      s.pending = true;
      s.pendingIndex = index;
      return turn.question;
    }
    serialize() {
      return JSON.stringify(this.sessions);
    }
  }
  if (typeof module !== "undefined" && module.exports)
    module.exports = { ConversationStore };
  else root.ConversationStore = ConversationStore;
})(typeof window !== "undefined" ? window : globalThis);
