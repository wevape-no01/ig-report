"""
threads_report.json + threads_history.json 을 읽어 스레드 리포트(threads.html)를 만든다.
데이터가 없으면 "설정 대기 중" 안내 페이지를 만든다 (링크가 깨지지 않게).

스레드에는 "도달"이 없다. 조회수(views)만 있고, 반응은 좋아요·답글·리포스트·인용이다.

실행: python3 build_threads.py
section h2::before, h3::before { content:"● "; color:#FFC800; font-size:11px; vertical-align:2px; }

"""

import json
import os

import layout

DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(DIR, "threads.html")


def load(name, default):
    p = os.path.join(DIR, name)
    if not os.path.exists(p):
        return default
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


CSS = """
:root {
  color-scheme: light only;
  --surface-1:#ffffff;
  --text-primary:#1A1A1A; --text-secondary:#54524B; --text-muted:#7a756a;
  --gridline:#E7E2D6; --border:#E7E2D6;
  --series-1:#1A1A1A; --gray:#cfc9ba;
  --good:#1F8A45; --critical:#C1392B;
}
* { box-sizing:border-box; }
html, body { background:#F4F1E8; }
/* 글꼴은 layout.py(SHELL_CSS)에서 한 곳으로 정한다. 여기서 다시 정하지 않는다. */
body { margin:0; color:#1A1A1A; }
.kpi-row { display:grid; grid-template-columns:repeat(auto-fit,minmax(155px,1fr));
           gap:12px; margin:0 0 20px; }
.stat-tile { background:#fff; border:1px solid var(--border); border-radius:10px; padding:14px 16px; }
.stat-tile .label { font-size:12px; color:var(--text-secondary); margin-bottom:6px; font-weight:600; }
.stat-tile .value { font-size:30px; font-weight:650; line-height:1.1; }
.stat-tile .note { font-size:11px; color:var(--text-muted); margin-top:5px; line-height:1.45; }
section { background:#fff; border:1px solid var(--border); border-radius:10px;
          padding:18px 18px 16px; margin-bottom:20px; }
.sec-h { display:flex; justify-content:space-between; align-items:flex-start;
         gap:12px; flex-wrap:wrap; margin-bottom:4px; }
section h2 { font-size:18px; margin:0; color:var(--text-primary); font-weight:700;
             letter-spacing:-0.01em; }
section .sub { font-size:11.5px; color:var(--text-muted); margin:0 0 14px; line-height:1.55; }
.seg { display:inline-flex; border:1px solid var(--border); border-radius:8px; overflow:hidden; }
.seg button { border:0; background:#fff; color:var(--text-secondary);
              font-family:inherit; font-size:12px; padding:6px 13px; cursor:pointer; }
.seg button + button { border-left:1px solid var(--border); }
.seg button[aria-pressed="true"] { background:var(--series-1); color:#FFC800; font-weight:650; }
svg { display:block; width:100%; height:auto; overflow:visible; }
.axis-label { fill:var(--text-muted); font-size:10.5px; }
.val-label { fill:var(--text-primary); font-size:11px; font-weight:600; }
.gridline { stroke:var(--gridline); stroke-width:1; }
/* 막대는 기본을 연한 베이지로 두고 가장 큰 것 하나만 노랑으로 강조 */
.bar { fill:#D9D2C2; }
.bar.hl { fill:#FFDE7A; }
/* 선 아래는 아주 옅게만 채운다 */
.area { fill:rgba(255,222,122,.16); stroke:none; }
/* 선은 검정 대신 연노랑 계열로. 너무 강조되지 않게 낮춘다. */
.line-path { fill:none; stroke:#E8C24A; stroke-width:2.4;
             stroke-linecap:round; stroke-linejoin:round; }
.dot { fill:#E8C24A; }
.dot.last { fill:#FFDE7A; stroke:#C9A227; stroke-width:1.6; }
.big { display:flex; align-items:baseline; gap:12px; flex-wrap:wrap; margin-bottom:2px; }
.big .n { font-size:36px; font-weight:650; line-height:1; }
/* 신규 팔로워 유입 — 늘면 초록, 줄면 빨강 */
.big .n.up { color:var(--good); }
.big .n.down { color:var(--critical); }
.big .u { font-size:14px; color:var(--text-muted); }
.up { color:var(--good); } .down { color:var(--critical); }
.mini-s { font-size:11.5px; color:var(--text-muted); margin:2px 0 14px; line-height:1.7; }
.dim { color:var(--text-muted); font-size:11px; }
.note-box { border:1px solid var(--border); border-left:3px solid var(--gray);
            border-radius:8px; padding:12px 14px; margin-top:15px; background:#FAF8F3;
            font-size:11.5px; line-height:1.75; color:var(--text-secondary); }
.note-box b { color:var(--text-primary); }
table { width:100%; border-collapse:collapse; font-size:12.5px; }
th, td { text-align:left; padding:8px 6px; border-bottom:1px solid var(--gridline); vertical-align:top; }
th { color:var(--text-muted); font-weight:500; font-size:10.5px;
     text-transform:uppercase; letter-spacing:.02em; white-space:nowrap; }
td.num { text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }
td.cap { max-width:300px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;
         color:var(--text-secondary); }
td.strong { font-weight:650; color:var(--text-primary); }
tr.extra { display:none; } tr.extra.on { display:table-row; }
a { color:#8A6A00; text-decoration:none; } a:hover { text-decoration:underline; }
.more { margin-top:12px; border:1px solid var(--border); background:#fff;
        color:var(--series-1); font-family:inherit; font-size:12.5px; font-weight:600;
        padding:8px 15px; border-radius:8px; cursor:pointer; }
.empty { color:var(--text-muted); font-size:12.5px; padding:10px 0; }
.foot { font-size:11.5px; color:var(--text-muted); line-height:1.8; }
.foot b { color:var(--text-secondary); }
details.tg { border:1px solid var(--border); border-radius:9px; margin-bottom:9px; }
details.tg summary { cursor:pointer; padding:11px 14px; font-size:13px; font-weight:600;
  color:var(--text-secondary); list-style:none; display:flex; align-items:center; gap:7px; }
details.tg summary::-webkit-details-marker { display:none; }
details.tg summary::before { content:"\\25b8"; color:var(--series-1); font-size:11px; }
details.tg[open] summary::before { content:"\\25be"; }
details.tg[open] summary { border-bottom:1px solid var(--gridline); }
.tg-body { padding:14px; }
.demos { display:grid; grid-template-columns:repeat(auto-fit,minmax(215px,1fr)); gap:16px; }
.dm-box { border:1px solid var(--border); border-radius:10px; padding:13px 14px; }
.dm-t { font-size:12px; font-weight:700; color:var(--text-primary); margin-bottom:10px; }
.dm { display:grid; grid-template-columns:74px 1fr 44px; align-items:center;
      gap:8px; margin-bottom:6px; font-size:11.5px; }
.dm-k { color:var(--text-secondary); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.dm-bar { background:var(--gridline); border-radius:3px; height:8px; overflow:hidden; }
.dm-bar i { display:block; height:100%; background:#D9D2C2; border-radius:3px; }
.dm-bar i.hl { background:#FFDE7A; }
.dm-v { text-align:right; font-variant-numeric:tabular-nums; }
.setup { border:1px solid #f0dca0; background:#fff8e1; color:#6b5300;
         border-radius:10px; padding:18px 20px; font-size:13.5px; line-height:1.75; }
.setup b { color:#4a3900; }
.setup ol { margin:10px 0 0; padding-left:20px; }
.setup li { margin-bottom:7px; }
"""

def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def page(inner, updated="", gen=""):
    return layout.document("th", "daily", "일일 리포트", inner, CSS,
                           updated=updated, generated_iso=gen)


SETUP = """
<div class="setup">
<b>아직 스레드 연결이 끝나지 않았습니다.</b> 아래 두 단계가 남아 있습니다.
<ol>
  <li>스레드 앱 → 프로필 → 설정 → <b>웹사이트 권한</b> 에서 "wevape analytics report" 초대를 <b>수락</b></li>
  <li>Meta 개발자 페이지에서 <b>장기 액세스 토큰</b>을 만들어 GitHub 시크릿 <b>THREADS_TOKEN</b> 에 저장</li>
</ol>
두 단계가 끝나고 리포트가 한 번 갱신되면 이 페이지가 자동으로 채워집니다.
</div>"""


def build():
    report = load("threads_report.json", None)
    hist = load("threads_history.json", [])

    if not report or not report.get("profile"):
        with open(OUT, "w", encoding="utf-8") as f:
            f.write(page(SETUP))
        print(f"저장됨: {OUT} (설정 대기 중 안내 페이지)")
        return

    prof = report["profile"]
    ins = dict(report.get("account_insights", {}))
    posts = report.get("posts", [])

    # 스레드 API 는 계정 단위 좋아요/답글/리포스트/인용을 0 으로 주는 경우가 있다.
    # 그럴 때는 캐시에 있는 전체 글의 인사이트를 더해서 채운다.
    cache = load("threads_cache.json", {})
    all_posts = list(cache.values()) if isinstance(cache, dict) else []
    from_posts = False
    for k in ("likes", "replies", "reposts", "quotes"):
        if not ins.get(k) and all_posts:
            ins[k] = sum((p.get("insights") or {}).get(k) or 0 for p in all_posts)
            from_posts = True

    # ---- 링크 클릭수
    clicks = ins.get("clicks") or []
    click_sec = ""
    if clicks:
        rows = "".join(
            f'<tr><td class="cap"><a href="{esc(c["url"])}" target="_blank" rel="noopener">'
            f'{esc(c["url"])}</a></td><td class="num strong">{c["value"]}</td></tr>'
            for c in clicks)
        click_sec = (f'<section><div class="sec-h"><h2>링크 클릭수</h2></div>'
                     f'<p class="sub">스레드 글에 넣은 링크를 누른 횟수입니다.</p>'
                     f'<table><thead><tr><th>링크</th><th class="num">클릭</th></tr></thead>'
                     f'<tbody>{rows}</tbody></table></section>')

    inner = """
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
  <svg id="followerChart" viewBox="0 0 860 240"></svg>
</section>

<section>
  <div class="sec-h"><h2>최근 글</h2></div>
  <table>
    <thead><tr>
      <th>날짜</th><th>내용</th>
      <th class="num">조회</th><th class="num">좋아요</th><th class="num">답글</th>
      <th class="num">리포스트</th><th class="num">인용</th><th class="num">공유</th>
    </tr></thead>
    <tbody id="postsBody"></tbody>
  </table>
  <button class="more" id="morePosts" hidden></button>
</section>

__CLICK_SEC__

<details class="tg"><summary>용어 설명</summary>
  <div class="tg-body foot">
    <b>조회</b> — 글이 화면에 표시된 횟수. 스레드는 사람 수를 주지 않습니다.<br>
    <b>답글</b> — 내 글에 달린 답글 수. 스레드에서 노출에 가장 크게 작용합니다.<br>
    <b>리포스트</b> — 내 글을 그대로 다시 올린 수. 답글 다음으로 강한 확산 신호입니다.<br>
    <b>인용</b> — 내 글에 의견을 붙여 새로 쓴 수.<br>
    <b>공유</b> — 스레드 밖으로 보낸 수.
  </div>
</details>

<script id="t-report" type="application/json">__REPORT__</script>
<script id="t-hist" type="application/json">__HIST__</script>
<script>
(function () {
  const report = JSON.parse(document.getElementById('t-report').textContent);
  const hist   = JSON.parse(document.getElementById('t-hist').textContent);
  const prof = report.profile || {};
  const ins  = report.account_insights || {};
  const posts = report.posts || [];
  let gran = 'day', granFol = 'day', open_ = false;
  hist.sort((a, b) => (a.date < b.date ? -1 : a.date > b.date ? 1 : 0));

  const n = v => (v === null || v === undefined) ? '-' : Number(v).toLocaleString();
  const num = v => (typeof v === 'number' && isFinite(v));
  const esc = t => (t||'').replace(/[<>&]/g, c => ({'<':'&lt;','>':'&gt;','&':'&amp;'}[c]));

  const GRAN_NOTE = { day:'최근 7일', week:'최근 4주 (월요일 시작)', month:'최근 12개월' };

  function bucket(key, g) {
    const rows = hist.filter(r => num(r[key]));
    if (!rows.length) return [];
    if (g === 'day') return rows.slice(-7).map(r =>
      ({label: r.date.slice(5).replace('-','/'), value: r[key]}));
    const m = new Map();
    if (g === 'week') {
      rows.forEach(r => {
        const d = new Date(r.date + 'T00:00:00Z');
        d.setUTCDate(d.getUTCDate() - ((d.getUTCDay() + 6) % 7));
        const k = d.toISOString().slice(0,10);
        if (!m.has(k)) m.set(k, []); m.get(k).push(r[key]);
      });
      return [...m.keys()].sort().slice(-4).map(k =>
        ({label: k.slice(5).replace('-','/') + ' 주',
          value: m.get(k).reduce((a,b)=>a+b,0)}));
    }
    const yr = rows[rows.length-1].date.slice(0,4);
    rows.filter(r => r.date.slice(0,4) === yr).forEach(r => {
      const k = r.date.slice(0,7);
      if (!m.has(k)) m.set(k, []); m.get(k).push(r[key]);
    });
    return [...m.keys()].sort().map(k =>
      ({label: (+k.slice(5)) + '월', value: m.get(k).reduce((a,b)=>a+b,0)}));
  }

  function drawBars(svg, rows) {
    const W = 860, H = 240, T = 30, B = 34, L = 6, R = 6;
    if (!rows.length) {
      svg.setAttribute('viewBox','0 0 860 70');
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

  // ---- 팔로워 -------------------------------------------------------------
  // 스레드 API 는 팔로워 수를 "지금 이 순간의 총합" 하나로만 준다 (since/until 미지원).
  // 그래서 매일 실행할 때 저장해 둔 스냅샷을 이어 붙여 추이를 만든다.
  const FOL_NOTE = { day:'최근 14일 기록', week:'최근 8주 (월요일 시작)', month:'최근 12개월' };

  function folRows() {
    return hist.filter(r => num(r.followers_count));
  }

  function folSeries(g) {
    const rows = folRows();
    if (!rows.length) return [];
    if (g === 'day') return rows.slice(-14).map(r =>
      ({label: r.date.slice(5).replace('-','/'), value: r.followers_count}));
    const m = new Map();                       // 같은 구간이면 나중 날짜가 덮어쓴다 = 구간 마지막 값
    if (g === 'week') {
      rows.forEach(r => {
        const d = new Date(r.date + 'T00:00:00Z');
        d.setUTCDate(d.getUTCDate() - ((d.getUTCDay() + 6) % 7));
        m.set(d.toISOString().slice(0,10), r.followers_count);
      });
      return [...m.keys()].sort().slice(-8).map(k =>
        ({label: k.slice(5).replace('-','/') + ' 주', value: m.get(k)}));
    }
    rows.forEach(r => m.set(r.date.slice(0,7), r.followers_count));
    return [...m.keys()].sort().slice(-12).map(k =>
      ({label: (+k.slice(5)) + '월', value: m.get(k)}));
  }

  function drawLine(svg, rows) {
    const W = 860, H = 240, T = 30, B = 34, PAD = 48;
    if (!rows.length) {
      svg.setAttribute('viewBox','0 0 860 70');
      svg.innerHTML = `<text class="axis-label" x="430" y="40" text-anchor="middle">아직 기록이 없습니다</text>`;
      return;
    }
    if (rows.length === 1) {
      svg.setAttribute('viewBox','0 0 860 110');
      svg.innerHTML =
        `<circle class="dot" cx="430" cy="45" r="5"/>
         <text class="val-label" x="430" y="30" text-anchor="middle">${rows[0].value.toLocaleString()}</text>
         <text class="axis-label" x="430" y="75" text-anchor="middle">${rows[0].label} · 기록이 하나뿐이라 선이 그려지지 않습니다</text>`;
      return;
    }
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
    const vals = rows.map(r => r.value);
    const min = Math.min(...vals), max = Math.max(...vals), range = (max - min) || 1;
    const plot = H - T - B, stepX = (W - PAD*2) / (rows.length - 1);
    const pts = rows.map((r,i) =>
      ({x: PAD + i*stepX, y: T + plot - ((r.value - min)/range)*plot, ...r}));
    let s = '';
    for (let g = 0; g <= 3; g++) {
      const y = T + (g/3)*plot;
      s += `<line class="gridline" x1="${PAD}" y1="${y.toFixed(1)}" x2="${W-PAD}" y2="${y.toFixed(1)}"/>`;
    }
    if (pts.length > 8) {          // 점마다 값을 적을 때는 축 숫자가 겹쳐서 생략한다
      s += `<text class="axis-label" x="${PAD-8}" y="${T+4}" text-anchor="end">${max.toLocaleString()}</text>`;
      s += `<text class="axis-label" x="${PAD-8}" y="${T+plot+4}" text-anchor="end">${min.toLocaleString()}</text>`;
    }
    const dPath = pts.map((p,i)=>(i?'L':'M')+p.x.toFixed(1)+','+p.y.toFixed(1)).join(' ');
    // 선 아래 영역을 연노랑으로 채운다
    s += `<path class="area" d="${dPath} L${pts[pts.length-1].x.toFixed(1)},${(T+plot).toFixed(1)} L${pts[0].x.toFixed(1)},${(T+plot).toFixed(1)} Z"/>`;
    s += `<path class="line-path" d="${dPath}"/>`;
    const every = pts.length <= 8 ? 1 : Math.ceil(pts.length/7);
    pts.forEach((p,i) => {
      const isLast = i === pts.length-1;
      s += `<circle class="dot${isLast ? ' last' : ''}" cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="${isLast ? 4.5 : 3.5}"/>`;
      if (i === 0 || i === pts.length-1 || i % every === 0)
        s += `<text class="axis-label" x="${p.x.toFixed(1)}" y="${H-B+20}" text-anchor="middle">${p.label}</text>`;
      if (pts.length <= 8)
        s += `<text class="val-label" x="${p.x.toFixed(1)}" y="${(p.y-10).toFixed(1)}" text-anchor="middle">${p.value.toLocaleString()}</text>`;
    });
    svg.innerHTML = s;
  }

  const FOL_LIMIT = `<details class="tg" style="margin-top:16px">
    <summary>스레드에서는 확인할 수 없는 것</summary>
    <div class="tg-body" style="font-size:11.5px;color:var(--text-muted);line-height:1.75">
      스레드는 "이 글을 보고 몇 명이 팔로우했다"를 주지 않습니다. 글 단위로 받을 수 있는 값은
      조회·좋아요·답글·리포스트·인용·공유 여섯 가지뿐입니다. 그래서 늘어난 사람 수까지만 알 수 있고,
      어느 글에서 왔는지는 알 수 없습니다. 어떤 사람들인지는
      <a href="./threads-detail.html">세부 분석</a>의 팔로워 구성에서 볼 수 있습니다.
    </div></details>`;

  function drawNewFollowers() {
    const box = document.getElementById('newFollowers');
    const rows = folRows();
    if (rows.length < 2) {
      box.innerHTML =
        `<p class="empty">기록이 ${rows.length}일치뿐이라 아직 증감을 계산할 수 없습니다. 내일부터 값이 나옵니다.</p>`
        + FOL_LIMIT;
      return;
    }
    const d = [];
    for (let i = 1; i < rows.length; i++) {
      const days = Math.max(1, Math.round(
        (new Date(rows[i].date) - new Date(rows[i-1].date)) / 86400000));
      d.push({date: rows[i].date, from: rows[i-1].date, days,
              delta: rows[i].followers_count - rows[i-1].followers_count,
              total: rows[i].followers_count});
    }
    const last = d[d.length-1];
    const recent = d.slice(-7);
    const sum = recent.reduce((a,r) => a + r.delta, 0);
    const span = recent.reduce((a,r) => a + r.days, 0);
    const sign = v => (v > 0 ? '+' : '') + n(v);
    const cls = v => (v > 0 ? 'up' : v < 0 ? 'down' : '');

    const head = `<div class="big">
        <span class="n ${cls(last.delta)}">${sign(last.delta)}</span>
        <span class="u">명 · ${last.from} → ${last.date}${last.days > 1 ? ` (${last.days}일치 합산)` : ''}</span>
      </div>
      <p class="mini-s">최근 ${span}일 <b>${sign(sum)}명</b> · 현재 총 ${n(last.total)}명</p>`;

    // 날짜별 증감 표는 바로 아래 [팔로워 수 추이] 그래프에서 같은 내용을 볼 수 있어 뺐다.
    box.innerHTML = head + FOL_LIMIT;
  }

  const iv = p => p.insights || {};

  function render() {
    // KPI
    const cut = new Date(Date.now() - 31*86400000).toISOString();
    const recent = posts.filter(p => (p.timestamp || '') >= cut);
    const rv = recent.map(p => iv(p).views).filter(num);
    const avg = rv.length ? Math.round(rv.reduce((a,b)=>a+b,0)/rv.length) : null;
    const last = hist.length ? hist[hist.length-1] : {};
    const monthViews = hist.slice(-31).reduce((a,r)=> a + (num(r.views) ? r.views : 0), 0);

    // 전일 대비 증감. 오르면 초록, 내리면 빨강.
    const dLine = (key, unit) => {
      const rs = hist.filter(r => num(r[key]));
      if (rs.length < 2) return `<div class="note">기록 쌓이는 중</div>`;
      const d = rs[rs.length-1][key] - rs[rs.length-2][key];
      if (d === 0) return `<div class="note">변동 없음 (전일 대비)</div>`;
      return `<div class="note ${d > 0 ? 'up' : 'down'}">${
        (d > 0 ? '+' : '') + d.toLocaleString() + unit} (전일 대비)</div>`;
    };

    document.getElementById('kpis').innerHTML = `
      <div class="stat-tile"><div class="label">팔로워</div>
        <div class="value">${n(ins.followers_count)}</div>
        ${dLine('followers_count', '명')}</div>
      <div class="stat-tile"><div class="label">글</div>
        <div class="value">${n(report.posts_total)}</div>
        <div class="note">인사이트 있는 글 ${n(report.posts_analyzable)}개</div></div>
      <div class="stat-tile"><div class="label">최근 한 달 조회수</div>
        <div class="value">${n(monthViews)}</div>
        <div class="note">일별 기록 합계</div></div>
      <div class="stat-tile"><div class="label">최근 글 평균 조회수</div>
        <div class="value">${n(avg)}</div>
        <div class="note">최근 한 달 · 글 ${rv.length}개 평균</div></div>`;

    // 누적 반응(좋아요·답글·리포스트·인용)은 하루 사이에 의미 있게 변하지 않아
    // 일일 리포트에서 뺐다. [콘텐츠 분석] > [세부 분석] 아래쪽에서 볼 수 있다.

    document.getElementById('subViews').textContent =
      GRAN_NOTE[gran];
    drawBars(document.getElementById('viewsChart'), bucket('views', gran));

    drawNewFollowers();
    document.getElementById('subFollowers').textContent =
      FOL_NOTE[granFol];
    drawLine(document.getElementById('followerChart'), folSeries(granFol));

    drawTable();
  }

  function row(p, cls) {
    const i = iv(p);
    const txt = esc((p.text||'').replace(/\\s+/g,' ').trim()) || '(내용 없음)';
    const link = p.permalink ? `<a href="${p.permalink}" target="_blank" rel="noopener">${txt}</a>` : txt;
    return `<tr class="${cls||''}">
      <td>${(p.timestamp||'').slice(0,10)}</td><td class="cap">${link}</td>
      <td class="num">${n(i.views)}</td><td class="num">${n(i.likes)}</td>
      <td class="num">${n(i.replies)}</td><td class="num">${n(i.reposts)}</td>
      <td class="num">${n(i.quotes)}</td><td class="num">${n(i.shares)}</td></tr>`;
  }

  function drawTable() {
    const body = document.getElementById('postsBody'), btn = document.getElementById('morePosts');
    const days = report.posts_recent_days || 31;
    const cut = new Date(Date.now() - days*86400000).toISOString();
    const recent = posts.filter(p => (p.timestamp || '') >= cut);
    const rows = recent.length >= 5 ? recent : posts.slice(0, 5);
    if (!rows.length) {
      body.innerHTML = `<tr><td colspan="8" class="empty">글이 없습니다</td></tr>`;
      btn.hidden = true; return;
    }
    body.innerHTML = rows.map((p,i) =>
      row(p, i < 5 ? '' : (open_ ? 'extra on' : 'extra'))).join('');
    if (rows.length > 5) {
      btn.hidden = false;
      btn.textContent = open_ ? '접기' : `최근 ${days}일 글 전체 보기 (${rows.length}개)`;
    } else btn.hidden = true;
  }

  document.getElementById('segViews').querySelectorAll('button').forEach(b => {
    b.onclick = () => {
      document.getElementById('segViews').querySelectorAll('button')
        .forEach(x => x.setAttribute('aria-pressed', x === b ? 'true' : 'false'));
      gran = b.dataset.g; render();
    };
  });
  document.getElementById('segFollowers').querySelectorAll('button').forEach(b => {
    b.onclick = () => {
      document.getElementById('segFollowers').querySelectorAll('button')
        .forEach(x => x.setAttribute('aria-pressed', x === b ? 'true' : 'false'));
      granFol = b.dataset.g; render();
    };
  });
  document.getElementById('morePosts').onclick = () => { open_ = !open_; render(); };

  render();
})();
</script>"""

    report = dict(report, account_insights=ins, totals_from_posts=from_posts)
    inner = (inner.replace("__CLICK_SEC__", click_sec)
                  .replace("__REPORT__", json.dumps(report, ensure_ascii=False))
                  .replace("__HIST__", json.dumps(hist, ensure_ascii=False)))
    gen = report.get("generated_at", "")
    html = page(inner, layout.fmt_updated(gen), gen)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"저장됨: {OUT} (@{prof.get('username','?')} · 글 {report.get('posts_total', 0)}개)")


if __name__ == "__main__":
    build()
