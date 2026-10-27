const { test, before, after } = require("node:test");
const assert = require("node:assert/strict");
const http = require("node:http");
const { spawn } = require("node:child_process");
const { once } = require("node:events");
let upstream, child, base, refreshStatus = 503, lastFeedUrl;
const fixture = {
  developments: [],
  total_count: 0,
  verified_count: 0,
  pending_count: 0,
  all_sectors: [],
  source_type_counts: {},
  source_type_labels: {},
  last_fetched_at: null,
  weekly_digest: null,
};
before(async () => {
  upstream = http.createServer((req, res) => {
    res.setHeader("Content-Type", "application/json");
    if (req.url.startsWith("/api/developments?")) {
      lastFeedUrl = req.url;
      res.end(JSON.stringify(fixture));
    } else if (req.url === "/api/refresh" && refreshStatus !== 503) {
      res.statusCode = refreshStatus;
      res.end(JSON.stringify({ started: true, scan: { id: 7, status: "running" } }));
    }
    else {
      res.statusCode = 503;
      res.end('{"error":"upstream failed"}');
    }
  });
  upstream.listen(0, "127.0.0.1");
  await once(upstream, "listening");
  const probe = http.createServer();
  probe.listen(0, "127.0.0.1");
  await once(probe, "listening");
  const port = probe.address().port;
  await new Promise((r) => probe.close(r));
  base = `http://127.0.0.1:${port}`;
  child = spawn(process.execPath, ["server.js"], {
    cwd: require("node:path").join(__dirname, ".."),
    env: {
      ...process.env,
      PORT: String(port),
      API_BASE_URL: `http://127.0.0.1:${upstream.address().port}`,
    },
    stdio: ["ignore", "pipe", "pipe"],
  });
  await once(child.stdout, "data");
});
after(async () => {
  child?.kill();
  await new Promise((r) => upstream.close(r));
});
test("failed refresh never redirects to a successful zero-results message", async () => {
  const response = await fetch(base + "/refresh", {
    method: "POST",
    redirect: "manual",
  });
  assert.equal(response.status, 303);
  assert.equal(
    new URL(response.headers.get("location"), base).searchParams.get(
      "refresh_error",
    ),
    "1",
  );
});
test("checked verification filter has only one successful form control", async () => {
  const response = await fetch(base + "/?show_unverified=true");
  const html = await response.text();
  assert.equal((html.match(/name="show_unverified"/g) || []).length, 1);
});
test("upstream chat failure stays a retryable JSON error", async () => {
  const response = await fetch(base + "/developments/1/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question: "Neden önemli?", history: [] }),
  });
  assert.equal(response.status, 503);
  assert.equal(typeof (await response.json()).error, "string");
});

test("empty dated search keeps query and other filters in the archive link", async () => {
  const { JSDOM } = require('jsdom');
  fixture.search = { archive_count: 2 };
  try {
    const response = await fetch(base + '/?period=today&q=bilgisayarli+goru&sector=healthcare&source_type=academic&show_unverified=true&min_priority=20');
    const dom = new JSDOM(await response.text());
    const empty = dom.window.document.querySelector('.empty-state');
    assert.match(empty.textContent, /2/);
    const target = new URL(empty.querySelector('a').getAttribute('href'), base);
    assert.equal(target.searchParams.get('q'), 'bilgisayarli goru');
    assert.equal(target.searchParams.get('period'), 'all');
    assert.equal(target.searchParams.get('sector'), 'healthcare');
    assert.equal(target.searchParams.get('source_type'), 'academic');
    assert.equal(target.searchParams.get('show_unverified'), 'true');
    assert.equal(target.searchParams.get('min_priority'), '20');
    dom.window.close();
  } finally { delete fixture.search; }
});

test("search defaults to relevance, but explicit recent ordering survives", async () => {
  const { JSDOM } = require('jsdom');
  for (const [query, expected] of [['?q=robotik', 'relevance'], ['?q=robotik&sort=recent', 'recent'], ['', 'recent']]) {
    const response = await fetch(base + '/' + query);
    const dom = new JSDOM(await response.text());
    assert.equal(dom.window.document.querySelector('#sort-select').value, expected);
    dom.window.close();
  }
});


test("default page requests all dates and newest stories", async () => {
  const html = await (await fetch(base + '/')).text();
  assert.equal(new URL(lastFeedUrl, base).searchParams.get('period'), 'all');
  assert.equal(new URL(lastFeedUrl, base).searchParams.get('sort'), 'recent');
  assert.match(html, /Son haberler/);
});

test("manual refresh acknowledges an asynchronous scan without a page redirect", async () => {
  refreshStatus = 202;
  try {
    const response = await fetch(base + '/refresh', {method:'POST', headers:{Accept:'application/json'}, redirect:'manual'});
    assert.equal(response.status, 202);
    assert.equal((await response.json()).scan.id, 7);
  } finally { refreshStatus = 503; }
});

test("busy manual refresh remains a JSON 409 for the live page", async () => {
  refreshStatus = 409;
  try {
    const response = await fetch(base + '/refresh', {method:'POST', headers:{Accept:'application/json'}, redirect:'manual'});
    assert.equal(response.status, 409);
  } finally { refreshStatus = 503; }
});
