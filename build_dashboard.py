"""
report_data.json + history.json 을 읽어 단일 HTML 대시보드(index.html)를 만든다.
데이터가 없으면 샘플로 대체하고 화면에 "샘플 데이터" 배너를 띄운다.

실행: python3 build_dashboard.py
"""

import json
import os
from datetime import datetime, timedelta, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPORT_PATH = os.path.join(BASE_DIR, "report_data.json")
HISTORY_PATH = os.path.join(BASE_DIR, "history.json")
OUT_PATH = os.path.join(BASE_DIR, "index.html")   # GitHub Pages가 첫 화면으로 읽는 파일명


def _sample():
    now = datetime.now(timezone.utc)
    accounts, history = [], {}
    for ai, (uname, base_f, base_reach) in enumerate(
        [("my_account", 717, 150), ("my_second", 4, 2)]
    ):
        posts = []
        for i in range(8):
            posts.append({
                "caption": f"샘플 게시물 {i+1} — 실제 연동 전 미리보기",
                "media_type": "IMAGE",
                "timestamp": (now - timedelta(days=i * 4)).isoformat(),
                "permalink": "#",
                "like_count": max(0, 8 - i + ai),
                "comments_count": 1,
                "insights": {
                    "reach": max(0, base_reach - i * 9),
                    "views": max(0, base_reach * 2 - i * 15),
                    "saved": 0, "shares": 0,
                    "total_interactions": max(0, 9 - i),
                },
            })
        accounts.append({
            "label": uname,
            "profile": {"username": uname, "name": "샘플 계정",
                        "followers_count": base_f, "follows_count": 100,
                        "media_count": 40 + ai},
            "account_insights": {"reach": base_reach // 6, "profile_views": 20,
                                 "accounts_engaged": 2, "total_interactions": 2},
            "posts": posts,
        })
        rows, f = [], base_f - 14
        for i in range(14, -1, -1):
            f += 1 if i % 2 == 0 else 0
            rows.append({"date": (now.date() - timedelta(days=i)).isoformat(),
                         "followers_count": f})
        history[uname] = rows
    return {"generated_at": now.isoformat(timespec="seconds"), "accounts": accounts}, history


def load_data():
    if os.path.exists(REPORT_PATH) and os.path.exists(HISTORY_PATH):
        with open(REPORT_PATH, encoding="utf-8") as f:
            report = json.load(f)
        with open(HISTORY_PATH, encoding="utf-8") as f:
            history = json.load(f)
        return report, history, False
    report, history = _sample()
    return report, history, True


TEMPLATE = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<meta name="color-scheme" content="light" />
<title>인스타그램 리포트</title>
<style>
  /* 항상 밝은 배경으로 고정 (기기가 다크 모드여도 흰 배경 유지).
     변수를 :root 에 두어야 body 배경에도 적용된다. */
  :root, .viz-root {
    color-scheme: light only;
    --surface-1:#ffffff; --page-plane:#ffffff;
    --text-primary:#111111; --text-secondary:#444444; --text-muted:#6b6b6b;
    --gridline:#e6e6e6; --baseline:#cccccc; --border:rgba(17,17,17,0.14);
    --series-1:#1f6fc7; --seq-400:#2a78d6; --seq-100:#cde2fb;
    --good:#006300; --critical:#c02a2a;
  }
  * { box-sizing:border-box; }
  html, body { background:#ffffff; }
  body { margin:0; font-family:system-ui,-apple-system,"Segoe UI",sans-serif;
         color:#111111; }
  .wrap { max-width:920px; margin:0 auto; padding:24px 16px 64px; }
  header.top { display:flex; justify-content:space-between; align-items:baseline;
               flex-wrap:wrap; gap:8px; margin-bottom:12px; }
  header.top h1 { font-size:20px; margin:0; }
  .updated { font-size:12px; color:var(--text-muted); }
  .sample-banner { background:#fff8e1; color:#6b5300; border:1px solid #f0dca0;
                   border-radius:8px; padding:10px 14px; font-size:13px; margin:12px 0 20px; }
  .tabs { display:flex; gap:6px; margin:16px 0 20px; flex-wrap:wrap; }
  .tab { padding:7px 14px; border-radius:999px; border:1px solid var(--border);
         background:var(--surface-1); color:var(--text-secondary);
         font-size:13px; cursor:pointer; font-family:inherit; }
  .tab[aria-selected="true"] { background:var(--series-1); border-color:var(--series-1);
                               color:#fff; font-weight:600; }
  .kpi-row { display:grid; grid-template-columns:repeat(auto-fit,minmax(148px,1fr));
             gap:12px; margin-bottom:24px; }
  .stat-tile { background:var(--surface-1); border:1px solid var(--border);
               border-radius:10px; padding:14px 16px; }
  .stat-tile .label { font-size:12px; color:var(--text-secondary); margin-bottom:6px; }
  .stat-tile .value { font-size:26px; font-weight:600; line-height:1.1; }
  .stat-tile .delta { font-size:12px; margin-top:4px; color:var(--text-muted); }
  .delta.up { color:var(--good); } .delta.down { color:var(--critical); }
  section { background:var(--surface-1); border:1px solid var(--border);
            border-radius:10px; padding:16px 18px; margin-bottom:20px; }
  section h2 { font-size:14px; margin:0 0 4px; color:var(--text-secondary); font-weight:600; }
  section .sub { font-size:11px; color:var(--text-muted); margin:0 0 12px; }
  svg { display:block; width:100%; height:auto; overflow:visible; }
  .axis-label { fill:var(--text-muted); font-size:10px; }
  .gridline { stroke:var(--gridline); stroke-width:1; }
  .line-path { fill:none; stroke:var(--series-1); stroke-width:2;
               stroke-linecap:round; stroke-linejoin:round; }
  .dot { fill:var(--series-1); }
  .bar { fill:var(--seq-400); }
  .bar-label { fill:var(--text-secondary); font-size:11px; }
  table { width:100%; border-collapse:collapse; font-size:13px; }
  th, td { text-align:left; padding:8px 6px; border-bottom:1px solid var(--gridline);
           vertical-align:top; }
  th { color:var(--text-muted); font-weight:500; font-size:11px;
       text-transform:uppercase; letter-spacing:.02em; }
  td.num { text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }
  td.cap { max-width:340px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;
           color:var(--text-secondary); }
  a { color:var(--series-1); text-decoration:none; }
  a:hover { text-decoration:underline; }
  .chart-wrap { position:relative; }
  .tooltip { position:absolute; pointer-events:none; background:var(--text-primary);
             color:var(--page-plane); font-size:11px; padding:4px 8px; border-radius:6px;
             opacity:0; transition:opacity .1s; white-space:nowrap; transform:translateX(-50%); }
  .empty { color:var(--text-muted); font-size:13px; padding:8px 0; }
</style>
</head>
<body>
<div class="viz-root">
<div class="wrap">
  <header class="top">
    <h1>인스타그램 리포트</h1>
    <span class="updated" id="updated"></span>
  </header>
  __SAMPLE_BANNER__

  <div class="tabs" id="tabs" role="tablist"></div>

  <div class="kpi-row" id="kpis"></div>

  <section>
    <h2>팔로워 수 추이</h2>
    <p class="sub">매일 실행될 때마다 기록이 쌓입니다. 첫날은 점 하나뿐입니다.</p>
    <div class="chart-wrap">
      <svg id="followerChart" viewBox="0 0 860 220"></svg>
      <div class="tooltip" id="tip"></div>
    </div>
  </section>

  <section>
    <h2>최근 게시물별 도달</h2>
    <p class="sub">도달 = 이 게시물을 본 고유 계정 수</p>
    <svg id="reachChart" viewBox="0 0 860 260"></svg>
  </section>

  <section>
    <h2>최근 게시물</h2>
    <table>
      <thead><tr>
        <th>날짜</th><th>내용</th>
        <th class="num">도달</th><th class="num">조회</th>
        <th class="num">좋아요</th><th class="num">댓글</th><th class="num">저장</th>
      </tr></thead>
      <tbody id="postsBody"></tbody>
    </table>
  </section>
</div>
</div>

<script id="report-data" type="application/json">__REPORT_JSON__</script>
<script id="history-data" type="application/json">__HISTORY_JSON__</script>
<script>
(function () {
  const report  = JSON.parse(document.getElementById('report-data').textContent);
  const history = JSON.parse(document.getElementById('history-data').textContent);
  const accounts = report.accounts || [];
  let current = 0;

  const d = new Date(report.generated_at);
  document.getElementById('updated').textContent =
    '업데이트: ' + (isNaN(d) ? report.generated_at : d.toLocaleString('ko-KR'));

  const n = v => (v === null || v === undefined) ? '-' : Number(v).toLocaleString();

  // ---- 탭 ----
  const tabs = document.getElementById('tabs');
  accounts.forEach((a, i) => {
    const b = document.createElement('button');
    b.className = 'tab'; b.textContent = '@' + a.profile.username;
    b.setAttribute('role','tab');
    b.onclick = () => { current = i; render(); };
    tabs.appendChild(b);
  });
  if (accounts.length < 2) tabs.style.display = 'none';

  function render() {
    Array.from(tabs.children).forEach((b,i) =>
      b.setAttribute('aria-selected', i === current ? 'true' : 'false'));

    const acc = accounts[current];
    const prof = acc.profile || {};
    const ins  = acc.account_insights || {};
    const posts = acc.posts || [];
    const hist = history[prof.username] || [];

    // ---- KPI ----
    const prev = hist.length >= 2 ? hist[hist.length-2].followers_count : null;
    const delta = prev === null ? null : (prof.followers_count - prev);
    const reaches = posts.map(p => p.insights && p.insights.reach).filter(v => typeof v === 'number');
    const avgReach = reaches.length ? Math.round(reaches.reduce((a,b)=>a+b,0)/reaches.length) : null;

    document.getElementById('kpis').innerHTML = `
      <div class="stat-tile"><div class="label">팔로워</div>
        <div class="value">${n(prof.followers_count)}</div>
        <div class="delta ${delta>0?'up':delta<0?'down':''}">${
          delta === null ? '기록 쌓이는 중' : (delta>0?'+':'') + delta + '명 (전일 대비)'}</div></div>
      <div class="stat-tile"><div class="label">게시물</div>
        <div class="value">${n(prof.media_count)}</div></div>
      <div class="stat-tile"><div class="label">오늘 도달</div>
        <div class="value">${n(ins.reach)}</div>
        <div class="delta">프로필 조회 ${n(ins.profile_views)}</div></div>
      <div class="stat-tile"><div class="label">최근 게시물 평균 도달</div>
        <div class="value">${n(avgReach)}</div></div>`;

    drawFollowers(hist);
    drawReach(posts);
    drawTable(posts);
  }

  // ---- 팔로워 추이 ----
  function drawFollowers(hist) {
    const svg = document.getElementById('followerChart');
    const tip = document.getElementById('tip');
    const W = 860, H = 220, PAD = 34;
    if (!hist.length) { svg.innerHTML =
      `<text class="axis-label" x="${W/2}" y="${H/2}" text-anchor="middle">기록이 아직 없습니다</text>`; return; }
    if (hist.length === 1) { svg.innerHTML =
      `<circle class="dot" cx="${W/2}" cy="${H/2}" r="5"/>
       <text class="axis-label" x="${W/2}" y="${H/2+24}" text-anchor="middle">${hist[0].date} · ${hist[0].followers_count}명 (내일부터 선이 그려집니다)</text>`; return; }

    const vals = hist.map(h => h.followers_count);
    const min = Math.min(...vals), max = Math.max(...vals), range = (max-min)||1;
    const stepX = (W-PAD*2)/(hist.length-1);
    const pts = hist.map((h,i) => ({
      x: PAD + i*stepX,
      y: H-PAD - ((h.followers_count-min)/range)*(H-PAD*2), ...h }));

    let s = '';
    for (let g=0; g<=3; g++) {
      const y = PAD + (g/3)*(H-PAD*2);
      s += `<line class="gridline" x1="${PAD}" y1="${y}" x2="${W-PAD}" y2="${y}"/>`;
    }
    s += `<text class="axis-label" x="${PAD-6}" y="${PAD+4}" text-anchor="end">${max}</text>`;
    s += `<text class="axis-label" x="${PAD-6}" y="${H-PAD+4}" text-anchor="end">${min}</text>`;
    s += `<path class="line-path" d="${pts.map((p,i)=>(i?'L':'M')+p.x.toFixed(1)+','+p.y.toFixed(1)).join(' ')}"/>`;
    const every = Math.max(1, Math.ceil(pts.length/6));
    pts.forEach((p,i) => {
      if (i===0 || i===pts.length-1 || i%every===0) {
        s += `<circle class="dot" cx="${p.x}" cy="${p.y}" r="3.5" data-i="${i}"/>`;
        s += `<text class="axis-label" x="${p.x}" y="${H-10}" text-anchor="middle">${p.date.slice(5)}</text>`;
      }
    });
    svg.innerHTML = s;

    svg.querySelectorAll('circle.dot').forEach(c => {
      c.addEventListener('mouseenter', () => {
        const p = pts[+c.dataset.i];
        const r = svg.getBoundingClientRect();
        tip.textContent = `${p.date} · 팔로워 ${p.followers_count.toLocaleString()}명`;
        tip.style.left = (p.x/W*r.width)+'px';
        tip.style.top  = (p.y/H*r.height-30)+'px';
        tip.style.opacity = 1;
      });
      c.addEventListener('mouseleave', () => tip.style.opacity = 0);
    });
  }

  // ---- 게시물별 도달 ----
  function drawReach(posts) {
    const svg = document.getElementById('reachChart');
    const rows = posts.slice(0,10).filter(p => p.insights && typeof p.insights.reach === 'number');
    if (!rows.length) { svg.setAttribute('viewBox','0 0 860 60');
      svg.innerHTML = `<text class="axis-label" x="430" y="34" text-anchor="middle">도달 데이터가 없습니다</text>`; return; }
    const BH=26, GAP=10, L=88, R=64, bw=860-L-R;
    const max = Math.max(...rows.map(p => p.insights.reach), 1);
    let s = '';
    rows.forEach((p,i) => {
      const y = i*(BH+GAP)+8, w = (p.insights.reach/max)*bw;
      s += `<text class="bar-label" x="0" y="${y+BH/2+4}">${(p.timestamp||'').slice(5,10)}</text>`;
      s += `<rect class="bar" x="${L}" y="${y}" width="${Math.max(w,2)}" height="${BH}" rx="4"/>`;
      s += `<text class="bar-label" x="${L+Math.max(w,2)+8}" y="${y+BH/2+4}">${p.insights.reach.toLocaleString()}</text>`;
    });
    svg.setAttribute('viewBox', `0 0 860 ${rows.length*(BH+GAP)+16}`);
    svg.innerHTML = s;
  }

  // ---- 표 ----
  function drawTable(posts) {
    const esc = t => (t||'').replace(/[<>&]/g, c => ({'<':'&lt;','>':'&gt;','&':'&amp;'}[c]));
    const body = document.getElementById('postsBody');
    if (!posts.length) { body.innerHTML = `<tr><td colspan="7" class="empty">게시물이 없습니다</td></tr>`; return; }
    body.innerHTML = posts.map(p => {
      const i = p.insights || {};
      const cap = esc((p.caption||'').replace(/\\s+/g,' ').trim()) || '(내용 없음)';
      const link = p.permalink && p.permalink !== '#'
        ? `<a href="${p.permalink}" target="_blank" rel="noopener">${cap}</a>` : cap;
      return `<tr>
        <td>${(p.timestamp||'').slice(0,10)}</td>
        <td class="cap">${link}</td>
        <td class="num">${n(i.reach)}</td>
        <td class="num">${n(i.views)}</td>
        <td class="num">${n(p.like_count)}</td>
        <td class="num">${n(p.comments_count)}</td>
        <td class="num">${n(i.saved)}</td>
      </tr>`;
    }).join('');
  }

  render();
})();
</script>
</body>
</html>
"""


def render(report, history, is_sample):
    html = TEMPLATE
    banner = ('<div class="sample-banner">⚠️ 아직 실제 데이터가 없어 샘플로 만든 미리보기입니다. '
              'instagram_api.py 를 실행하면 실제 데이터로 바뀝니다.</div>') if is_sample else ""
    for k, v in {
        "__SAMPLE_BANNER__": banner,
        "__REPORT_JSON__": json.dumps(report, ensure_ascii=False),
        "__HISTORY_JSON__": json.dumps(history, ensure_ascii=False),
    }.items():
        html = html.replace(k, v)
    return html


if __name__ == "__main__":
    report, history, is_sample = load_data()
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(render(report, history, is_sample))
    names = ", ".join("@" + a["profile"].get("username", "?") for a in report["accounts"])
    print(f"저장됨: {OUT_PATH} (계정: {names}, 샘플: {is_sample})")
