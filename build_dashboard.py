"""
report_data.json + history.json 을 읽어 일일 리포트(index.html)를 만든다.
데이터가 없으면 샘플로 대체하고 화면에 "샘플 데이터" 배너를 띄운다.

구성: KPI → 조회수(일/주/월) → 신규 팔로워 유입 → 팔로워 수 추이(일/주/월) → 최근 게시물

실행: python3 build_dashboard.py
"""

import json
import os
from datetime import datetime, timedelta, timezone

import layout

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
                    "saved": 0, "shares": 0, "follows": max(0, 3 - i),
                    "total_interactions": max(0, 9 - i),
                },
            })
        accounts.append({
            "label": uname,
            "profile": {"username": uname, "name": "샘플 계정",
                        "followers_count": base_f, "follows_count": 100,
                        "media_count": 40 + ai},
            "account_insights": {"reach": base_reach // 6, "views": base_reach // 3,
                                 "profile_views": 20, "accounts_engaged": 2,
                                 "total_interactions": 2,
                                 "reach_follower": 12, "reach_non_follower": 6,
                                 "views_follower": 30, "views_non_follower": 18},
            "demographics": {},
            "posts_total": 40 + ai, "posts_analyzable": 8,
            "posts_recent_days": 31, "posts_recent_count": 8,
            "posts": posts,
        })
        rows, f = [], base_f - 28
        for i in range(28, -1, -1):
            gained = 1 if i % 2 == 0 else 0
            f += gained
            rows.append({"date": (now.date() - timedelta(days=i)).isoformat(),
                         "followers_count": f, "new_followers": gained,
                         "reach": base_reach // 6 + (i % 5), "views": base_reach // 3 + (i % 9)})
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


PAGE_CSS = """
  :root {
    color-scheme: light only;
    --surface-1:#ffffff;
    --text-primary:#1A1A1A; --text-secondary:#54524B; --text-muted:#7a756a;
    --gridline:#E7E2D6; --border:#E7E2D6;
    --series-1:#1A1A1A; --seq-100:#FFF3C4; --gray:#cfc9ba;
    --good:#1F8A45; --critical:#C1392B;
  }
  * { box-sizing:border-box; }
  html, body { background:#F4F1E8; }
  /* 글꼴은 layout.py(SHELL_CSS)에서 한 곳으로 정한다. 여기서 다시 정하지 않는다. */
  body { margin:0; color:#1A1A1A; }
  .sample-banner { background:#fff8e1; color:#6b5300; border:1px solid #f0dca0;
                   border-radius:8px; padding:10px 14px; font-size:13px; margin:12px 0 20px; }
  .tabs { display:flex; gap:6px; margin:16px 0 20px; flex-wrap:wrap; }
  .tab { padding:7px 14px; border-radius:999px; border:1px solid var(--border);
         background:var(--surface-1); color:var(--text-secondary);
         font-size:13px; cursor:pointer; font-family:inherit; }
  .tab[aria-selected="true"] { background:var(--series-1); border-color:var(--series-1);
                               color:#FFC800; font-weight:650; }
  .kpi-row { display:grid; grid-template-columns:repeat(auto-fit,minmax(155px,1fr));
             gap:12px; margin-bottom:24px; }
  .stat-tile { background:var(--surface-1); border:1px solid var(--border);
               border-radius:10px; padding:14px 16px; }
  .stat-tile .label { font-size:12px; color:var(--text-secondary); margin-bottom:6px;
                      font-weight:600; }
  .stat-tile .value { font-size:30px; font-weight:650; line-height:1.1; }
  .stat-tile .note { font-size:11px; color:var(--text-muted); margin-top:5px; line-height:1.45; }
  .stat-tile .delta { font-size:12px; margin-top:5px; color:var(--text-muted); }
  .delta.up { color:var(--good); } .delta.down { color:var(--critical); }
  section { background:var(--surface-1); border:1px solid var(--border);
            border-radius:10px; padding:18px 18px 16px; margin-bottom:20px; }
  .sec-h { display:flex; justify-content:space-between; align-items:flex-start;
           gap:12px; flex-wrap:wrap; margin-bottom:4px; }
  section h2 { font-size:18px; margin:0; color:var(--text-primary); font-weight:700;
               letter-spacing:-0.01em; }
  section .sub { font-size:11.5px; color:var(--text-muted); margin:0 0 14px; line-height:1.55; }
  .seg { display:inline-flex; border:1px solid var(--border); border-radius:8px; overflow:hidden; }
  .seg button { border:0; background:var(--surface-1); color:var(--text-secondary);
                font-family:inherit; font-size:12px; padding:6px 13px; cursor:pointer; }
  .seg button + button { border-left:1px solid var(--border); }
  .seg button[aria-pressed="true"] { background:var(--series-1); color:#FFC800; font-weight:650; }
  svg { display:block; width:100%; height:auto; overflow:visible; }
  .axis-label { fill:var(--text-muted); font-size:10.5px; }
  .val-label { fill:var(--text-primary); font-size:11px; font-weight:600; }
  .gridline { stroke:var(--gridline); stroke-width:1; }
  /* 선은 검정 대신 연노랑 계열로. 너무 강조되지 않게 낮춘다. */
  .line-path { fill:none; stroke:#E8C24A; stroke-width:2.4;
               stroke-linecap:round; stroke-linejoin:round; }
  /* 선 아래는 아주 옅게만 채운다 */
  .area { fill:rgba(255,222,122,.16); stroke:none; }
  .dot { fill:#E8C24A; }
  .dot.last { fill:#FFDE7A; stroke:#C9A227; stroke-width:1.6; }
  /* 막대는 기본을 연한 베이지로 두고 가장 큰 것 하나만 노랑으로 강조 */
  .bar { fill:#D9D2C2; }
  .bar.hl { fill:#FFCE33; }
  .bar-label { fill:var(--text-secondary); font-size:11px; }
  .split { display:grid; grid-template-columns:1fr 1fr; gap:22px; }
  @media (max-width:680px) { .split { grid-template-columns:1fr; } }
  .mini-t { font-size:12.5px; font-weight:700; color:var(--text-primary); margin-bottom:4px; }
  .mini-s { font-size:11px; color:var(--text-muted); margin:0 0 11px; line-height:1.5; }
  .srow { display:grid; grid-template-columns:96px 1fr 74px; align-items:center;
          gap:9px; margin-bottom:8px; font-size:12px; }
  .srow-k { color:var(--text-secondary); }
  .srow-b { background:var(--gridline); border-radius:3px; height:9px; overflow:hidden; }
  .srow-b i { display:block; height:100%; background:#D9D2C2; border-radius:3px; }
  .srow-b i.hl { background:#FFCE33; }
  .srow-b i.g { background:#C3BCAB; }
  .srow-v { text-align:right; font-variant-numeric:tabular-nums; }
  .big { display:flex; align-items:baseline; gap:12px; flex-wrap:wrap; margin-bottom:2px; }
  .big .n { font-size:36px; font-weight:650; line-height:1; }
  /* 신규 팔로워 유입 — 늘면 초록, 줄면 빨강 */
  .big .n.up { color:var(--good); }
  .big .n.down { color:var(--critical); }
  .big .u { font-size:14px; color:var(--text-muted); }
  table { width:100%; border-collapse:collapse; font-size:12.5px; }
  th, td { text-align:left; padding:8px 6px; border-bottom:1px solid var(--gridline);
           vertical-align:top; }
  th { color:var(--text-muted); font-weight:500; font-size:10.5px;
       text-transform:uppercase; letter-spacing:.02em; white-space:nowrap; }
  td.num { text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }
  td.cap { max-width:300px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;
           color:var(--text-secondary); }
  tr.extra { display:none; }
  tr.extra.on { display:table-row; }
  a { color:#8A6A00; text-decoration:none; }
  a:hover { text-decoration:underline; }
  .more { margin-top:12px; border:1px solid var(--border); background:var(--surface-1);
          color:var(--series-1); font-family:inherit; font-size:12.5px; font-weight:600;
          padding:8px 15px; border-radius:8px; cursor:pointer; }
  .chart-wrap { position:relative; }
  .tooltip { position:absolute; pointer-events:none; background:var(--text-primary);
             color:#fff; font-size:11px; padding:4px 8px; border-radius:6px;
             opacity:0; transition:opacity .1s; white-space:nowrap; transform:translateX(-50%); }
  .empty { color:var(--text-muted); font-size:12.5px; padding:10px 0; }
  .foot { font-size:11.5px; color:var(--text-muted); line-height:1.8; }
  .foot b { color:var(--text-secondary); }
"""

BODY = """
  __SAMPLE_BANNER__


  <div class="kpi-row" id="kpis"></div>

  <section>
    <div class="sec-h">
      <h2>조회수</h2>
      <div class="seg" id="segViews">
        <button data-g="day" aria-pressed="true">일</button>
        <button data-g="week" aria-pressed="false">주</button>
        <button data-g="month" aria-pressed="false">월</button>
      </div>
    </div>
    <p class="sub" id="subViews"></p>
    <svg id="viewsChart" viewBox="0 0 860 240"></svg>
  </section>

  <section>
    <div class="sec-h"><h2>신규 팔로워 유입</h2></div>
    <div id="newFollowers"></div>
  </section>

  <section>
    <div class="sec-h">
      <h2>팔로워 수 추이</h2>
      <div class="seg" id="segFollowers">
        <button data-g="day" aria-pressed="true">일</button>
        <button data-g="week" aria-pressed="false">주</button>
        <button data-g="month" aria-pressed="false">월</button>
      </div>
    </div>
    <p class="sub" id="subFollowers"></p>
    <div class="chart-wrap">
      <svg id="followerChart" viewBox="0 0 860 240"></svg>
      <div class="tooltip" id="tip"></div>
    </div>
  </section>

  <section>
    <div class="sec-h"><h2>최근 게시물</h2></div>

    <table>
      <thead><tr>
        <th>날짜</th><th>내용</th>
        <th class="num">도달</th><th class="num">조회</th>
        <th class="num">팔로워</th><th class="num">좋아요</th>
        <th class="num">댓글</th><th class="num">저장</th>
      </tr></thead>
      <tbody id="postsBody"></tbody>
    </table>
    <button class="more" id="morePosts" hidden></button>
  </section>

  <details class="tg"><summary>용어 설명</summary>
    <div class="tg-body foot">
      <b>도달</b> — 본 사람 수. 같은 사람이 여러 번 봐도 1로 셉니다.<br>
      <b>조회</b> — 화면에 표시된 횟수. 같은 사람이 3번 보면 3입니다. 도달보다 항상 큽니다.<br>
      <b>팔로워</b> — 그 게시물을 보고 팔로우한 수.<br>
      <b>저장</b> — 나중에 보려고 저장한 수. 좋아요보다 강한 관심 신호입니다.<br>
      <b>비팔로워</b> — 아직 팔로우하지 않은 사람. 이 비중이 오르면 새 사람에게 퍼지는 중입니다.
    </div>
  </details>

<script id="report-data" type="application/json">__REPORT_JSON__</script>
<script id="history-data" type="application/json">__HISTORY_JSON__</script>
<script>
(function () {
  const report  = JSON.parse(document.getElementById('report-data').textContent);
  const history = JSON.parse(document.getElementById('history-data').textContent);
  const accounts = report.accounts || [];
  let current = 0;
  let granViews = 'day', granFol = 'day';
  let postsOpen = false;

  const n  = v => (v === null || v === undefined) ? '-' : Number(v).toLocaleString();
  const esc = t => (t||'').replace(/[<>&]/g, c => ({'<':'&lt;','>':'&gt;','&':'&amp;'}[c]));
  const num = v => (typeof v === 'number' && isFinite(v));

  // ---- 계정 탭 ----
  const tabs = document.getElementById('tabs');
  accounts.forEach((a, i) => {
    const b = document.createElement('button');
    b.className = 'tab'; b.textContent = '@' + a.profile.username;
    b.setAttribute('role','tab');
    b.onclick = () => { current = i; postsOpen = false; render(); };
    tabs.appendChild(b);
  });
  if (accounts.length < 2) tabs.style.display = 'none';

  // ---- 기간 전환 ----
  function wireSeg(id, set) {
    document.getElementById(id).querySelectorAll('button').forEach(b => {
      b.onclick = () => {
        document.getElementById(id).querySelectorAll('button')
          .forEach(x => x.setAttribute('aria-pressed', x === b ? 'true' : 'false'));
        set(b.dataset.g); render();
      };
    });
  }
  wireSeg('segViews',     g => granViews = g);
  wireSeg('segFollowers', g => granFol   = g);

  document.getElementById('morePosts').onclick = () => { postsOpen = !postsOpen; render(); };

  // ---- 기간별 집계 ----
  // agg='sum' 은 흐름 지표(조회수), agg='last' 는 수준 지표(총 팔로워 수)
  function bucket(hist, key, gran, agg) {
    const rows = hist.filter(r => num(r[key]));
    if (!rows.length) return [];
    if (gran === 'day') {
      return rows.slice(-7).map(r => ({label: r.date.slice(5).replace('-','/'),
                                       full: r.date, value: r[key]}));
    }
    const m = new Map();
    if (gran === 'week') {
      rows.forEach(r => {
        const dt = new Date(r.date + 'T00:00:00Z');
        const dow = (dt.getUTCDay() + 6) % 7;               // 월요일=0
        dt.setUTCDate(dt.getUTCDate() - dow);
        const k = dt.toISOString().slice(0,10);
        if (!m.has(k)) m.set(k, []);
        m.get(k).push(r[key]);
      });
      return [...m.keys()].sort().slice(-4).map(k => ({
        label: k.slice(5).replace('-','/') + ' 주',
        full: k + ' 주간',
        value: agg === 'sum' ? m.get(k).reduce((a,b)=>a+b,0) : m.get(k)[m.get(k).length-1]}));
    }
    const yr = rows[rows.length-1].date.slice(0,4);
    rows.filter(r => r.date.slice(0,4) === yr).forEach(r => {
      const k = r.date.slice(0,7);
      if (!m.has(k)) m.set(k, []);
      m.get(k).push(r[key]);
    });
    return [...m.keys()].sort().map(k => ({
      label: (+k.slice(5)) + '월', full: k,
      value: agg === 'sum' ? m.get(k).reduce((a,b)=>a+b,0) : m.get(k)[m.get(k).length-1]}));
  }

  const GRAN_NOTE = {
    day:   '최근 7일',
    week:  '최근 4주 (월요일 시작)',
    month: '최근 12개월'
  };

  function render() {
    Array.from(tabs.children).forEach((b,i) =>
      b.setAttribute('aria-selected', i === current ? 'true' : 'false'));

    const acc  = accounts[current] || {};
    const prof = acc.profile || {};
    const ins  = acc.account_insights || {};
    const posts = acc.posts || [];
    const hist = history[prof.username] || [];

    drawKpis(prof, ins, posts, hist);

    document.getElementById('subViews').textContent = GRAN_NOTE[granViews];
    document.getElementById('subFollowers').textContent = GRAN_NOTE[granFol];

    drawBars(document.getElementById('viewsChart'), bucket(hist, 'views', granViews, 'sum'));
    drawNewFollowers(hist, posts, ins);
    drawLine(document.getElementById('followerChart'), bucket(hist, 'followers_count', granFol, 'last'));
    drawTable(acc, posts);
  }

  // ---- KPI ----
  // 전일 대비 증감 한 줄. 오르면 초록, 내리면 빨강.
  function deltaLine(hist, key, unit, fallback) {
    const rows = hist.filter(r => num(r[key]));
    if (rows.length < 2)
      return `<div class="delta">${fallback || '기록 쌓이는 중'}</div>`;
    const d = rows[rows.length-1][key] - rows[rows.length-2][key];
    if (d === 0) return `<div class="delta">변동 없음 (전일 대비)</div>`;
    return `<div class="delta ${d > 0 ? 'up' : 'down'}">${
      (d > 0 ? '+' : '') + d.toLocaleString() + unit} (전일 대비)</div>`;
  }

  function drawKpis(prof, ins, posts, hist) {
    // 최근 한 달 게시물만으로 평균 도달을 낸다
    const cut = new Date(Date.now() - 31*86400000).toISOString();
    const recent = posts.filter(p => (p.timestamp || '') >= cut);
    const reaches = recent.map(p => p.insights && p.insights.reach).filter(num);
    const avgReach = reaches.length ? Math.round(reaches.reduce((a,b)=>a+b,0)/reaches.length) : null;

    document.getElementById('kpis').innerHTML = `
      <div class="stat-tile"><div class="label">팔로워</div>
        <div class="value">${n(prof.followers_count)}</div>
        ${deltaLine(hist, 'followers_count', '명')}</div>
      <div class="stat-tile"><div class="label">게시물</div>
        <div class="value">${n(prof.media_count)}</div>
        ${deltaLine(hist, 'media_count', '개', '기록 쌓이는 중')}</div>
      <div class="stat-tile"><div class="label">오늘 도달</div>
        <div class="value">${n(ins.reach)}</div>
        ${deltaLine(hist, 'reach', '')}</div>
      <div class="stat-tile"><div class="label">최근 게시물 평균 도달</div>
        <div class="value">${n(avgReach)}</div>
        <div class="note">최근 한 달 · 게시물 ${reaches.length}개 평균</div></div>`;
  }

  // ---- 세로 막대 그래프 ----
  function drawBars(svg, rows) {
    const W = 860, H = 240, T = 30, B = 34, L = 6, R = 6;
    if (!rows.length) {
      svg.setAttribute('viewBox', '0 0 860 70');
      svg.innerHTML = `<text class="axis-label" x="430" y="40" text-anchor="middle">아직 기록이 없습니다</text>`;
      return;
    }
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
    const max = Math.max(...rows.map(r => r.value), 1);
    const plot = H - T - B, slot = (W - L - R) / rows.length;
    const bw = Math.min(64, slot * 0.6);
    let s = '';
    for (let g = 0; g <= 3; g++) {
      const y = T + (g/3)*plot;
      s += `<line class="gridline" x1="${L}" y1="${y.toFixed(1)}" x2="${W-R}" y2="${y.toFixed(1)}"/>`;
    }
    // 가장 큰 막대 하나만 노랑으로 칠한다 (나머지는 연한 베이지)
    let maxI = 0;
    rows.forEach((r,i) => { if (r.value > rows[maxI].value) maxI = i; });
    rows.forEach((r,i) => {
      const cx = L + slot*i + slot/2;
      const h = Math.max((r.value/max)*plot, r.value > 0 ? 2 : 0);
      const bc = (i === maxI && r.value > 0) ? 'bar hl' : 'bar';
      s += `<rect class="${bc}" x="${(cx-bw/2).toFixed(1)}" y="${(T+plot-h).toFixed(1)}" width="${bw.toFixed(1)}" height="${h.toFixed(1)}" rx="3"/>`;
      s += `<text class="val-label" x="${cx.toFixed(1)}" y="${(T+plot-h-7).toFixed(1)}" text-anchor="middle">${r.value.toLocaleString()}</text>`;
      s += `<text class="axis-label" x="${cx.toFixed(1)}" y="${H-B+20}" text-anchor="middle">${r.label}</text>`;
    });
    svg.innerHTML = s;
  }

  // ---- 꺾은선 그래프 ----
  function drawLine(svg, rows) {
    const tip = document.getElementById('tip');
    const W = 860, H = 240, T = 30, B = 34, PAD = 44;
    if (!rows.length) {
      svg.setAttribute('viewBox', '0 0 860 70');
      svg.innerHTML = `<text class="axis-label" x="430" y="40" text-anchor="middle">아직 기록이 없습니다</text>`;
      return;
    }
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
    if (rows.length === 1) {
      svg.innerHTML =
        `<circle class="dot" cx="${W/2}" cy="${H/2-10}" r="5"/>
         <text class="axis-label" x="${W/2}" y="${H/2+20}" text-anchor="middle">${rows[0].label} · ${rows[0].value.toLocaleString()}명 (구간이 하나뿐이라 선이 그려지지 않습니다)</text>`;
      return;
    }
    const vals = rows.map(r => r.value);
    const min = Math.min(...vals), max = Math.max(...vals), range = (max-min) || 1;
    const plot = H - T - B;
    const stepX = (W - PAD*2) / (rows.length - 1);
    const pts = rows.map((r,i) => ({
      x: PAD + i*stepX, y: T + plot - ((r.value-min)/range)*plot, ...r }));

    let s = '';
    for (let g = 0; g <= 3; g++) {
      const y = T + (g/3)*plot;
      s += `<line class="gridline" x1="${PAD}" y1="${y.toFixed(1)}" x2="${W-PAD}" y2="${y.toFixed(1)}"/>`;
    }
    s += `<text class="axis-label" x="${PAD-8}" y="${T+4}" text-anchor="end">${max.toLocaleString()}</text>`;
    s += `<text class="axis-label" x="${PAD-8}" y="${T+plot+4}" text-anchor="end">${min.toLocaleString()}</text>`;
    const dPath = pts.map((p,i)=>(i?'L':'M')+p.x.toFixed(1)+','+p.y.toFixed(1)).join(' ');
    // 선 아래 영역을 연노랑으로 채운다
    s += `<path class="area" d="${dPath} L${pts[pts.length-1].x.toFixed(1)},${(T+plot).toFixed(1)} L${pts[0].x.toFixed(1)},${(T+plot).toFixed(1)} Z"/>`;
    s += `<path class="line-path" d="${dPath}"/>`;
    const every = pts.length <= 8 ? 1 : Math.ceil(pts.length/7);
    pts.forEach((p,i) => {
      const isLast = i === pts.length-1;
      s += `<circle class="dot${isLast ? ' last' : ''}" cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="${isLast ? 4.5 : 3.5}" data-i="${i}"/>`;
      if (i === 0 || i === pts.length-1 || i % every === 0) {
        s += `<text class="axis-label" x="${p.x.toFixed(1)}" y="${H-B+20}" text-anchor="middle">${p.label}</text>`;
      }
      if (pts.length <= 8) {
        s += `<text class="val-label" x="${p.x.toFixed(1)}" y="${(p.y-10).toFixed(1)}" text-anchor="middle">${p.value.toLocaleString()}</text>`;
      }
    });
    svg.innerHTML = s;

    svg.querySelectorAll('circle.dot').forEach(c => {
      c.addEventListener('mouseenter', () => {
        const p = pts[+c.dataset.i];
        const r = svg.getBoundingClientRect();
        tip.textContent = `${p.full || p.label} · 팔로워 ${p.value.toLocaleString()}명`;
        tip.style.left = (p.x/W*r.width)+'px';
        tip.style.top  = (p.y/H*r.height-30)+'px';
        tip.style.opacity = 1;
      });
      c.addEventListener('mouseleave', () => tip.style.opacity = 0);
    });
  }

  // ---- 신규 팔로워 유입 ----
  function drawNewFollowers(hist, posts, ins) {
    const box = document.getElementById('newFollowers');
    const withNew = hist.filter(r => num(r.new_followers));
    const last = withNew.length ? withNew[withNew.length-1] : null;
    const prev = withNew.length >= 2 ? withNew[withNew.length-2] : null;
    const dl = (last && prev) ? last.new_followers - prev.new_followers : null;

    const head = last
      ? `<div class="big"><span class="n ${last.new_followers > 0 ? 'up' : last.new_followers < 0 ? 'down' : ''}">${last.new_followers > 0 ? '+' : ''}${n(last.new_followers)}</span>
           <span class="u">명 · ${last.date}</span>
           <span class="u ${dl>0?'delta up':dl<0?'delta down':''}">${
             (dl === null || dl === 0) ? '' : (dl>0?'+':'') + dl + '명 (전일 대비)'}</span></div>
         <p class="mini-s">인스타그램이 확정해 주는 어제까지의 값입니다.</p>`
      : `<p class="empty">신규 팔로워 기록이 아직 없습니다.</p>`;

    // ① 새 사람에게 닿았는가 — 신규 팔로워와 같은 "어제" 기준으로 맞춘다.
    // 오늘 값은 아직 쌓이는 중이라 두 숫자의 기준일이 달라지면 헷갈린다.
    const TITLE1 = `<div class="mini-t">어디까지 퍼졌나</div>`;
    // 신규 팔로워와 같은 날(어제)을 쓴다. 없으면 그 이전 중 가장 최근 날.
    const splitRows = hist.filter(r => num(r.reach_follower) && num(r.reach_non_follower)
                                    && (r.reach_follower + r.reach_non_follower) > 0);
    const target = last ? last.date : '';
    const dayRow = splitRows.filter(r => !target || r.date <= target).pop()
                || splitRows.pop();
    let left;
    if (dayRow) {
      const f = dayRow.reach_follower, nf = dayRow.reach_non_follower, tot = f + nf;
      const row = (k, v, gray) => `
        <div class="srow"><div class="srow-k">${k}</div>
          <div class="srow-b"><i class="${gray?'g':'hl'}" style="width:${(v/tot*100).toFixed(1)}%"></i></div>
          <div class="srow-v">${n(v)} · ${Math.round(v/tot*100)}%</div></div>`;
      left = TITLE1 +
        `<p class="mini-s">${dayRow.date} 계정을 본 사람. 비팔로워가 많을수록 새 사람에게 퍼진 것입니다.</p>
        ${row('비팔로워', nf, false)}${row('기존 팔로워', f, true)}`;
    } else {
      left = TITLE1 + `<p class="empty">아직 기록이 없습니다.</p>`;
    }

    // ② 오늘 팔로우를 만든 게시물
    // 인스타그램은 게시물별 팔로우 수를 "평생 누적"으로만 준다. 그래서 매일 적어 둔
    // 값(follows_log)의 전날 대비 증가분을 오늘치로 본다.
    const TITLE2 = `<div class="mini-t">어느 게시물이 데려왔나</div>`;
    const gain = [];
    let logged = 0, from = '', to = '';
    posts.forEach(p => {
      const lg = p.follows_log;
      if (!lg) return;
      const ds = Object.keys(lg).sort();
      if (!ds.length) return;
      logged++;
      if (ds.length < 2) return;
      const a = ds[ds.length-2], b = ds[ds.length-1];
      if (b > to) { from = a; to = b; }
      const d = lg[b] - lg[a];
      if (d > 0) gain.push({p, d});
    });
    gain.sort((x,y) => y.d - x.d);

    let right;
    if (gain.length) {
      const gap = Math.max(1, Math.round(
        (new Date(to) - new Date(from)) / 86400000));
      right = TITLE2 +
        `<p class="mini-s">${to} 기준${gap > 1 ? ` (${gap}일치)` : ''} · 그 글을 보고 팔로우한 수</p>
         <table><thead><tr><th>날짜</th><th>내용</th><th class="num">팔로워</th></tr></thead><tbody>` +
        gain.slice(0,5).map(({p, d}) => {
          const cap = esc((p.caption||'').replace(/\\s+/g,' ').trim()).slice(0,60) || '(내용 없음)';
          const link = p.permalink && p.permalink !== '#'
            ? `<a href="${p.permalink}" target="_blank" rel="noopener">${cap}</a>` : cap;
          return `<tr><td>${(p.timestamp||'').slice(5,10)}</td><td class="cap">${link}</td>
                  <td class="num">+${n(d)}</td></tr>`;
        }).join('') + `</tbody></table>`;
    } else if (to) {
      right = TITLE2 + `<p class="mini-s">${to} 기준 · 팔로우를 만든 글이 없습니다.</p>`;
    } else {
      right = TITLE2 + `<p class="mini-s">기록을 모으는 중입니다. 내일부터 값이 나옵니다.</p>`;
    }

    box.innerHTML = head + `<div class="split" style="margin-top:16px">
      <div>${left}</div><div>${right}</div></div>`;
  }

  // ---- 최근 게시물 표 ----
  function drawTable(acc, posts) {
    const body = document.getElementById('postsBody');
    const btn  = document.getElementById('morePosts');
    const days = acc.posts_recent_days || 31;
    const cut  = new Date(Date.now() - days*86400000).toISOString();
    const recent = posts.filter(p => (p.timestamp || '') >= cut);
    const rows = recent.length >= 5 ? recent : posts.slice(0, 5);

    if (!rows.length) {
      body.innerHTML = `<tr><td colspan="8" class="empty">게시물이 없습니다</td></tr>`;
      btn.hidden = true; return;
    }
    body.innerHTML = rows.map((p, i) => {
      const ii = p.insights || {};
      const cap = esc((p.caption||'').replace(/\\s+/g,' ').trim()) || '(내용 없음)';
      const link = p.permalink && p.permalink !== '#'
        ? `<a href="${p.permalink}" target="_blank" rel="noopener">${cap}</a>` : cap;
      const cls = i < 5 ? '' : (postsOpen ? 'extra on' : 'extra');
      return `<tr class="${cls}">
        <td>${(p.timestamp||'').slice(0,10)}</td>
        <td class="cap">${link}</td>
        <td class="num">${n(ii.reach)}</td>
        <td class="num">${n(ii.views)}</td>
        <td class="num">${n(ii.follows)}</td>
        <td class="num">${n(p.like_count)}</td>
        <td class="num">${n(p.comments_count)}</td>
        <td class="num">${n(ii.saved)}</td>
      </tr>`;
    }).join('');

    if (rows.length > 5) {
      btn.hidden = false;
      btn.textContent = postsOpen
        ? '접기'
        : `최근 ${days}일 게시물 전체 보기 (${rows.length}개)`;
    } else {
      btn.hidden = true;
    }
  }

  render();
})();
</script>
section h2::before, h3::before { content:"● "; color:#FFC800; font-size:11px; vertical-align:2px; }

"""


def render(report, history, is_sample):
    body = BODY
    banner = ('<div class="sample-banner">⚠️ 아직 실제 데이터가 없어 샘플로 만든 미리보기입니다. '
              'instagram_api.py 를 실행하면 실제 데이터로 바뀝니다.</div>') if is_sample else ""
    for k, v in {
        "__SAMPLE_BANNER__": banner,
        "__REPORT_JSON__": json.dumps(report, ensure_ascii=False),
        "__HISTORY_JSON__": json.dumps(history, ensure_ascii=False),
    }.items():
        body = body.replace(k, v)
    gen = report.get("generated_at", "")
    return layout.document("ig", "daily", "일일 리포트", body, PAGE_CSS,
                           updated=layout.fmt_updated(gen), generated_iso=gen,
                           tabs='<div class="tabs" id="tabs" role="tablist"></div>')


if __name__ == "__main__":
    report, history, is_sample = load_data()
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(render(report, history, is_sample))
    names = ", ".join("@" + a["profile"].get("username", "?") for a in report["accounts"])
    print(f"저장됨: {OUT_PATH} (계정: {names}, 샘플: {is_sample})")
