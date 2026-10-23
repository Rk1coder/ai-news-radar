const express = require("express");
const path = require("path");

const API_BASE = process.env.API_BASE_URL || "http://localhost:8008";
const PORT = process.env.PORT || 3000;

const app = express();
app.set("view engine", "ejs");
app.set("views", path.join(__dirname, "views"));

function formatDate(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  const pad = (n) => String(n).padStart(2, "0");
  return `${pad(d.getUTCDate())}.${pad(d.getUTCMonth() + 1)}.${d.getUTCFullYear()}`;
}

function buildQs(current) {
  return function qs(overrides) {
    const params = { ...current, ...overrides };
    const clean = {};
    for (const [k, v] of Object.entries(params)) {
      if (v === null || v === undefined || v === "" || v === false || v === 0) continue;
      clean[k] = v;
    }
    const search = new URLSearchParams(clean).toString();
    return search ? `?${search}` : "?";
  };
}

app.get("/", async (req, res) => {
  const current = {
    q: req.query.q || "",
    sector: req.query.sector || "",
    source_type: req.query.source_type || "",
    min_priority: req.query.min_priority || 0,
    show_unverified: req.query.show_unverified === "true",
    sort: req.query.sort || "priority",
  };

  const apiParams = new URLSearchParams(current);
  const apiRes = await fetch(`${API_BASE}/api/developments?${apiParams.toString()}`);
  if (!apiRes.ok) {
    return res.status(502).send("AI News Radar API'sine ulasilamadi.");
  }
  const data = await apiRes.json();

  res.render("index", {
    ...data,
    ...current,
    selected_sector: current.sector,
    selected_source_type: current.source_type,
    refreshed: req.query.refreshed !== undefined ? Number(req.query.refreshed) : null,
    qs: buildQs(current),
    formatDate,
  });
});

app.post("/refresh", async (req, res) => {
  const apiRes = await fetch(`${API_BASE}/api/refresh`, { method: "POST" });
  const data = apiRes.ok ? await apiRes.json() : { refreshed: 0 };
  res.redirect(`/?refreshed=${data.refreshed}`);
});

app.listen(PORT, () => {
  console.log(`AI News Radar frontend http://localhost:${PORT} uzerinde calisiyor (API: ${API_BASE})`);
});
