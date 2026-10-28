const express = require("express");
const path = require("path");
const fs = require("fs");
const API_BASE = process.env.API_BASE_URL || "http://localhost:8008";
const PORT = process.env.PORT || 3000;
const app = express();
app.set("view engine", "ejs");
app.set("views", path.join(__dirname, "views"));
app.use(express.json({ limit: "128kb" }));
app.use(express.static(path.join(__dirname, "public")));
app.get("/vendor/gsap.min.js", (req, res) => {
  res.sendFile(require.resolve("gsap/dist/gsap.min.js"));
});

const icons = new Map();
function icon(name) {
  if (!/^[a-z-]+$/.test(name)) return "";
  if (!icons.has(name))
    icons.set(
      name,
      fs
        .readFileSync(
          path.join(
            __dirname,
            "node_modules/@phosphor-icons/core/assets/regular",
            `${name}.svg`,
          ),
          "utf8",
        )
        .replace(
          "<svg ",
          '<svg aria-hidden="true" focusable="false" class="icon" ',
        ),
    );
  return icons.get(name);
}
const sectorLabels = {
  advertising: "Reklam",
  autonomous_systems: "Otonom sistemler",
  cybersecurity: "Siber güvenlik",
  defense: "Savunma",
  design: "Tasarım",
  "e-commerce": "E-ticaret",
  education: "Eğitim",
  enterprise: "Kurumsal",
  entertainment: "Eğlence",
  finance: "Finans",
  general_software: "Yazılım",
  government: "Kamu",
  healthcare: "Sağlık",
  manufacturing: "Üretim",
  marketing: "Pazarlama",
  robotics: "Robotik",
  nlp: "Dil işleme",
};
const sourceLabels = {
  "nvidia-blog": "NVIDIA Blog",
  arxiv: "arXiv",
  "openai-news": "OpenAI",
  "huggingface-daily-papers": "Hugging Face Papers",
  "huggingface-blog": "Hugging Face",
  "substack-ai": "Substack · AI",
  "aws-ml-blog": "AWS ML Blog",
  "the-decoder": "The Decoder",
  "smol-ai-news": "Smol AI",
  "mit-technology-review": "MIT Technology Review",
  "theverge-ai": "The Verge",
  "arstechnica-ai": "Ars Technica",
  "bens-bites": "Ben’s Bites",
  "ai-weekly": "AI Weekly",
  "tldr-ai": "TLDR AI",
  "wired-ai": "WIRED",
  "import-ai": "Import AI",
  "n8n-blog": "n8n Blog",
  "make-blog": "Make",
  "zapier-blog": "Zapier",
  "the-rundown-ai": "The Rundown AI",
  "medium-ai-automation": "Medium · AI ve Otomasyon",
  "dogus-teknoloji-medium": "Doğuş Teknoloji · Medium",
  "dogus-teknoloji-blog": "Doğuş Teknoloji",
  "atalay-tech": "Atalay Tech",
  "reddit-localllama": "Reddit · r/LocalLLaMA",
  "reddit-ai-communities": "Reddit · AI ve yerel modeller",
  "yt-two-minute-papers": "YouTube · Two Minute Papers",
  "yt-yannic-kilcher": "YouTube · Yannic Kilcher",
  "yt-ai-explained": "YouTube · AI Explained",
  "yt-lex-fridman": "YouTube · Lex Fridman",
  "yt-matt-wolfe": "YouTube · Matt Wolfe",
  "yt-ai-jason": "YouTube · AI Jason",
  "yt-vllm-office-hours": "YouTube · vLLM Office Hours",
  "yt-matt-williams": "YouTube · Matt Williams",
  "yt-matthew-berman": "YouTube · Matthew Berman",
  "yt-sam-witteveen": "YouTube · Sam Witteveen",
  "ollama-blog": "Ollama Blog",
  "lm-studio-blog": "LM Studio",
  "civitai-education": "Civitai Education",
  "stable-diffusion-art": "Stable Diffusion Art",
  "openzeka-blog": "OpenZeka",
  "masqot-blog": "Masqot",
};
function dateValue(iso) {
  return iso
    ? new Date(/Z$|[+-]\d{2}:\d{2}$/.test(iso) ? iso : `${iso}Z`)
    : null;
}
function formatDate(iso) {
  const d = dateValue(iso);
  return d && !isNaN(d)
    ? new Intl.DateTimeFormat("tr-TR", {
        day: "numeric",
        month: "long",
        year: "numeric",
        timeZone: "Europe/Istanbul",
      }).format(d)
    : "Tarih belirtilmemiş";
}
function formatRelative(iso) {
  const d = dateValue(iso);
  if (!d || isNaN(d)) return "henüz yok";
  const m = Math.max(0, Math.floor((Date.now() - d) / 60000));
  return m < 1
    ? "az önce"
    : m < 60
      ? `${m} dakika önce`
      : m < 1440
        ? `${Math.floor(m / 60)} saat önce`
        : `${Math.floor(m / 1440)} gün önce`;
}
function scanLabels(state = {}) {
  const scan = state.last_scan;
  let status = "İlk tarama bekleniyor";
  if (scan?.status === "running") {
    const checked = (scan.successful_sources || 0) + (scan.failed_sources?.length || 0);
    status = checked ? `Taranıyor · ${checked} kaynak kontrol edildi · ${scan.new_count || 0} yeni kayıt` : "Kaynaklar taranıyor…";
  }
  else if (["failed", "interrupted"].includes(scan?.status))
    status = "Son tarama tamamlanamadı";
  else if (scan?.finished_at)
    status = `Son kontrol ${formatRelative(scan.finished_at)}`;
  if (scan?.status === "partial")
    status += ` · ${scan.failed_sources.length} kaynağa ulaşılamadı`;
  if (scan?.digest_failed) status += " · Özet güncellenemedi";
  const next = dateValue(state.next_run_at);
  const time =
    next && !isNaN(next)
      ? new Intl.DateTimeFormat("tr-TR", {
          hour: "2-digit",
          minute: "2-digit",
          timeZone: state.timezone || "Europe/Istanbul",
        }).format(next)
      : null;
  const schedule = !state.enabled
    ? "Otomatik tarama kapalı"
    : !state.scheduler_online
      ? "Otomatik tarama bağlantısı bekleniyor"
      : `${state.interval_minutes ? `${state.interval_minutes} dakikada bir tarama` : "Özel tarama programı"}${time ? ` · Sıradaki ${time} (TR)` : ""}`;
  return { status, schedule, running: scan?.status === "running", outcome: scan?.status || "", newCount: scan?.new_count || 0 };
}
function buildQs(current) {
  return (overrides) => {
    const params = Object.entries({ ...current, ...overrides }).filter(
      ([, v]) =>
        v !== "" && v !== null && v !== undefined && v !== false && v !== 0,
    );
    return `?${new URLSearchParams(params)}`;
  };
}
function safeUrl(value) {
  try {
    const u = new URL(value);
    return ["http:", "https:"].includes(u.protocol) ? u.href : "";
  } catch {
    return "";
  }
}
const asyncRoute = (fn) => (req, res, next) =>
  Promise.resolve(fn(req, res, next)).catch(next);
const apiFetch = (url, options = {}) =>
  fetch(`${API_BASE}${url}`, {
    signal: AbortSignal.timeout(90000),
    ...options,
  });
app.get(
  "/",
  asyncRoute(async (req, res) => {
    res.set("Cache-Control", "no-store");
    const str = (key) =>
      typeof req.query[key] === "string" ? req.query[key] : "";
    const current = {
      q: str("q").trim(),
      sector: str("sector"),
      source_type: str("source_type"),
      min_priority: Math.max(
        0,
        Math.min(100, Number(str("min_priority")) || 0),
      ),
      show_unverified: str("show_unverified") === "true",
      sort: ["priority", "recent", "relevance"].includes(str("sort"))
        ? str("sort")
        : (str("q").trim() ? "relevance" : "recent"),
      period: ["today", "week", "all"].includes(str("period"))
        ? str("period")
        : "all",
    };
    const response = await apiFetch(
      `/api/developments?${new URLSearchParams(current)}`,
    );
    if (!response.ok) throw new Error("API unavailable");
    const data = await response.json();
    res.render("index", {
      ...data,
      searchInfo: data.search || null,
      ...current,
      qs: buildQs(current),
      formatDate,
      icon,
      safeUrl,
      sectorLabel: (s) => sectorLabels[s] || s.replaceAll("_", " "),
      sourceLabel: (s) => sourceLabels[s] || s.replaceAll("-", " "),
      lastFetchedLabel: formatRelative(data.last_fetched_at),
      scanLabels: scanLabels(data.scan_status),
      digestLabel: data.weekly_digest
        ? formatRelative(data.weekly_digest.generated_at)
        : null,
      refreshed: str("refreshed") !== "" ? Number(str("refreshed")) : null,
      refreshError: str("refresh_error") === "1",
      refreshBusy: str("refresh_busy") === "1",
      refreshStarted: str("refresh_started") === "1",
    });
  }),
);
app.post("/refresh", async (req, res) => {
  const json = req.get("accept")?.includes("application/json");
  try {
    const response = await apiFetch("/api/refresh", {
      method: "POST",
      signal: AbortSignal.timeout(15000),
    });
    if (response.status === 409)
      return json ? res.status(409).json({ busy: true }) : res.redirect(303, "/?refresh_busy=1");
    if (!response.ok) throw new Error("Refresh failed");
    const data = await response.json();
    if (response.status !== 202 || !data.started || !data.scan?.id)
      throw new Error("Invalid scan acknowledgement");
    return json ? res.status(202).json(data) : res.redirect(303, "/?refresh_started=1");
  } catch {
    return json ? res.status(503).json({ error: "Tarama başlatılamadı. Yeniden deneyebilirsin." })
      : res.redirect(303, "/?refresh_error=1");
  }
});
app.get(
  "/developments/:id/preview",
  asyncRoute(async (req, res) => {
    const response = await apiFetch(
      `/api/developments/${encodeURIComponent(req.params.id)}/preview`,
      { signal: AbortSignal.timeout(15000) },
    );
    if (!response.ok)
      return res.status(response.status).json({ error: "Önizleme alınamadı." });
    const data = await response.json();
    res.json({ ...data, image: safeUrl(data.image), url: safeUrl(data.url) });
  }),
);
app.post(
  "/developments/:id/chat",
  asyncRoute(async (req, res) => {
    const question =
      typeof req.body.question === "string" ? req.body.question.trim() : "";
    if (!question || question.length > 4000)
      return res
        .status(400)
        .json({ error: "1–4000 karakter arasında bir soru yaz." });
    const history = Array.isArray(req.body.history)
      ? req.body.history
          .filter(
            (m) =>
              m &&
              ["user", "assistant"].includes(m.role) &&
              typeof m.content === "string",
          )
          .slice(-24)
      : [];
    const response = await apiFetch(
      `/api/developments/${encodeURIComponent(req.params.id)}/chat`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, history }),
      },
    );
    if (!response.ok)
      return res.status(response.status).json({
        error:
          response.status === 429
            ? "Şu an çok fazla istek var. Biraz sonra yeniden dene."
            : "Yanıt alınamadı. Yeniden deneyebilirsin.",
      });
    res.json(await response.json());
  }),
);
app.get(
  "/settings-api",
  asyncRoute(async (req, res) => {
    const response = await apiFetch("/api/settings", { signal: AbortSignal.timeout(15000) });
    if (!response.ok) return res.status(502).json({ error: "Ayarlar alınamadı." });
    res.json(await response.json());
  }),
);
app.put(
  "/settings-api/scan",
  asyncRoute(async (req, res) => {
    const response = await apiFetch("/api/settings/scan", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req.body),
      signal: AbortSignal.timeout(15000),
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      return res.status(response.status).json({ error: response.status < 500 && typeof body.detail === "string" ? body.detail : "Ayar kaydedilemedi." });
    }
    res.json(await response.json());
  }),
);
app.put(
  "/settings-api/sources/:name",
  asyncRoute(async (req, res) => {
    const response = await apiFetch(
      `/api/settings/sources/${encodeURIComponent(req.params.name)}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(req.body),
        signal: AbortSignal.timeout(15000),
      },
    );
    if (!response.ok) return res.status(response.status).json({ error: "Kaynak güncellenemedi." });
    res.json(await response.json());
  }),
);
app.post(
  "/settings-api/sources/custom",
  asyncRoute(async (req, res) => {
    const response = await apiFetch("/api/settings/sources/custom", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req.body),
      signal: AbortSignal.timeout(15000),
    });
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      return res.status(response.status).json({ error: data.detail || "Kaynak eklenemedi." });
    }
    res.json(await response.json());
  }),
);
app.delete(
  "/settings-api/sources/custom/:id",
  asyncRoute(async (req, res) => {
    const response = await apiFetch(
      `/api/settings/sources/custom/${encodeURIComponent(req.params.id)}`,
      { method: "DELETE", signal: AbortSignal.timeout(15000) },
    );
    if (!response.ok) return res.status(response.status).json({ error: "Kaynak kaldırılamadı." });
    res.json(await response.json());
  }),
);
app.use((error, req, res, next) => {
  if (res.headersSent) return next(error);
  if (error.type === "entity.too.large")
    return res.status(413).json({
      error: "Sohbet isteği çok uzun. Daha kısa bir soru deneyebilirsin.",
    });
  if (error.type === "entity.parse.failed")
    return res.status(400).json({ error: "Geçersiz istek." });
  if (req.path !== "/")
    return res
      .status(502)
      .json({ error: "Bağlantı kurulamadı. Yeniden deneyebilirsin." });
  res.status(502).render("error", { icon });
});
if (require.main === module)
  app.listen(PORT, () => console.log(`AI News Radar http://localhost:${PORT}`));
module.exports = { app };
