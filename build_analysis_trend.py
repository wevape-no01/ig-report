"""지난 분석 페이지(analysis-trend.html)를 만든다.

analysis_history.json 에 주 단위로 적힌 콘텐츠 분석 수치를 시간순으로 보여준다.
콘텐츠 분석 페이지가 "지금 어떤가"라면 여기는 "어느 쪽으로 가고 있나"를 본다.

화면 구성
  지금 값과 4주·12주 전 대비  →  지표별 추세 선 그래프(버튼으로 전환)  →  주간 기록표

그래프·카드 모양은 layout.COMPONENT_CSS 를 그대로 쓴다. 여기서 새로 정하지 않는다.
(일일 리포트와 위치·글꼴이 어긋나면 안 된다)

실행: python3 build_analysis_trend.py
"""

import json
import os

import analysis_history
import layout

DIR = os.path.dirname(os.path.abspath(__file__))

# 화면에 보여줄 지표. (열쇠, 이름, 단위, 소수 자리, 클수록 좋은가, 설명)
METRICS = [
    ("er_bench", "반응률", "(%)", 2, True,
     "(좋아요+댓글) ÷ 팔로워 × 100 · 업계 평균과 같은 식"),
    ("posted_4w", "최근 4주 발행 수", "(개)", 0, True,
     "그 시점 기준 직전 4주에 올린 게시물 수"),
    ("reach_median", "도달 중앙값", "(명)", 0, True,
     "게시물 하나가 닿은 사람 수의 가운데 값"),
    ("follow_per100", "도달 100당 팔로우", "(건)", 2, True,
     "노출이 사람으로 바뀌는 비율"),
    ("er_reach", "도달 대비 반응", "(%)", 1, True,
     "(좋아요+댓글+저장+공유) ÷ 도달 × 100 · 소재의 힘"),
    ("save_rate", "저장률", "(%)", 2, True,
     "저장 ÷ 도달 × 100 · 알고리즘이 크게 보는 신호"),
]

PAGE_CSS = layout.COMPONENT_CSS + """
.trend-h { display:flex; justify-content:space-between; align-items:flex-start;
           gap:12px; flex-wrap:wrap; margin-bottom:12px; }
.mini { display:grid; grid-template-columns:repeat(auto-fit,minmax(158px,1fr)); gap:12px;
        margin-bottom:4px; }
.mini .stat-tile .value { font-size:26px; }
.chips { display:flex; flex-wrap:wrap; gap:6px; margin:0 0 14px; }
.chips button { border:1px solid var(--border); background:var(--surface-1);
  color:var(--text-secondary); font-family:inherit; font-size:12px; padding:6px 12px;
  border-radius:8px; cursor:pointer; }
.chips button[aria-pressed="true"] { background:var(--series-1); color:#FFC800; font-weight:650;
  border-color:var(--series-1); }
.est { display:inline-block; font-size:10.5px; color:#8A6A00; background:#FFF3C4;
       border-radius:5px; padding:1px 6px; margin-left:6px; vertical-align:1px; }
.note-box { border:1px solid #EEE0B8; background:#FDFBF4; border-radius:8px;
  padding:10px 12px; font-size:12px; color:var(--text-secondary); line-height:1.7;
  margin:0 0 16px; }
table.trend { width:100%; border-collapse:collapse; font-size:12.5px; margin-top:6px; }
table.trend th, table.trend td { text-align:right; padding:7px 6px;
  border-bottom:1px solid var(--gridline); white-space:nowrap; }
table.trend th:first-child, table.trend td:first-child { text-align:left; }
table.trend th { color:var(--text-muted); font-weight:500; font-size:10.5px;
  text-transform:uppercase; letter-spacing:.02em; }
table.trend td { font-variant-numeric:tabular-nums; }
table.trend tr.now td { font-weight:700; background:#FFFBEE; }
.wrap-x { overflow-x:auto; }
"""

JS = """<script>
(function () {
  const RAW = JSON.parse(document.getElementById('trend-data').textContent);
  const META = JSON.parse(document.getElementById('trend-meta').textContent);
  let user = Object.keys(RAW)[0];
  let key = META[0].key;

  const num = (v, d) => (v === null || v === undefined) ? '–'
    : v.toLocaleString(undefined, {minimumFractionDigits: d, maximumFractionDigits: d});
  const md = s => s.slice(5).replace('-', '/');

  function niceTicks(mn, mx, n) {
    const raw = (mx - mn) / n || 1;
    const e = Math.pow(10, Math.floor(Math.log10(raw)));
    const f = raw / e;
    const step = (f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10) * e;
    const lo = Math.floor(mn / step) * step;
    let hi = Math.ceil(mx / step) * step;
    if (hi === lo) hi = lo + step;
    const ticks = [];
    for (let v = lo; v <= hi + step * 1e-6; v += step) ticks.push(+v.toFixed(6));
    return { lo, hi, ticks };
  }

  // 일일 리포트의 drawLine 과 같은 좌표계·같은 클래스를 쓴다. 모양이 달라지면 안 된다.
  function drawLine(svg, rows, dec, unit, yUnit) {
    const W = 860, H = 240, T = 30, B = 46, PAD = 44;
    if (rows.length < 2) {
      svg.setAttribute('viewBox', '0 0 860 70');
      svg.innerHTML = '<text class="axis-label" x="430" y="40" text-anchor="middle">'
        + '기록이 2주치 이상 쌓이면 선이 그려집니다</text>';
      return;
    }
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
    const vals = rows.map(r => r.v);
    const ax = niceTicks(Math.min(...vals), Math.max(...vals), 3);
    const min = ax.lo, range = (ax.hi - ax.lo) || 1;
    const plot = H - T - B;
    const stepX = (W - PAD * 2) / (rows.length - 1);
    const yOf = v => T + plot - ((v - min) / range) * plot;
    const pts = rows.map((r, i) => ({ x: PAD + i * stepX, y: yOf(r.v), ...r }));

    let s = '';
    ax.ticks.forEach(t => {
      const y = yOf(t);
      s += `<line class="gridline" x1="${PAD}" y1="${y.toFixed(1)}" x2="${W - PAD}" y2="${y.toFixed(1)}"/>`;
      s += `<text class="axis-label" x="${PAD - 8}" y="${(y + 3.5).toFixed(1)}" text-anchor="end">${num(t, dec)}</text>`;
    });
    if (yUnit) s += `<text class="unit-label" x="${PAD - 8}" y="${T - 18.6}" text-anchor="end">${yUnit}</text>`;
    const d = pts.map((p, i) => (i ? 'L' : 'M') + p.x.toFixed(1) + ',' + p.y.toFixed(1)).join(' ');
    s += `<path class="area" d="${d} L${pts[pts.length-1].x.toFixed(1)},${(T+plot).toFixed(1)} L${pts[0].x.toFixed(1)},${(T+plot).toFixed(1)} Z"/>`;
    s += `<path class="line-path" d="${d}"/>`;
    const every = pts.length <= 8 ? 1 : Math.ceil(pts.length / 7);
    pts.forEach((p, i) => {
      const last = i === pts.length - 1;
      // 소급 계산분은 속을 비운 점으로 그린다 — 실측과 눈으로 구분되게.
      // fill 은 속성이 아니라 style 로 줘야 한다 (.dot 의 CSS 가 속성을 이긴다).
      const est = p.est && !last;
      s += `<circle class="dot${last ? ' last' : ''}" cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}"`
         + ` r="${last ? 4.5 : 3.5}"`
         + (est ? ' style="fill:#FFFDF6;stroke:#E8C24A;stroke-width:1.6"' : '') + '/>';
      if (i === 0 || last || i % every === 0) {
        s += `<text class="axis-label" x="${p.x.toFixed(1)}" y="${H - B + 20}" text-anchor="middle">${md(p.d)}</text>`;
      }
    });
    if (unit) s += `<text class="unit-label" x="${W - 6}" y="${H - 6}" text-anchor="end">${unit}</text>`;
    svg.innerHTML = s;
  }

  function delta(rows, key, back, dec) {
    const i = rows.length - 1, j = i - back;
    if (j < 0 || rows[i][key] === null || rows[j][key] === null) return '기록 부족';
    const d = rows[i][key] - rows[j][key];
    if (Math.abs(d) < Math.pow(10, -dec) / 2) return '거의 같음';
    const cls = d > 0 ? 'up' : 'down';
    return `<span class="${cls}">${d > 0 ? '+' : ''}${num(d, dec)}</span>`;
  }

  function draw() {
    const rows = RAW[user];
    const m = META.find(x => x.key === key);
    const pts = rows.filter(r => r[key] !== null && r[key] !== undefined)
                    .map(r => ({ d: r.date, v: r[key], est: r.estimated }));
    document.getElementById('metricName').textContent = m.name;
    document.getElementById('metricWhy').textContent = m.why;
    drawLine(document.getElementById('sv'), pts, m.dec, m.unit, m.unit);

    const last = rows[rows.length - 1];
    document.getElementById('mini').innerHTML = META.slice(0, 4).map(x => `
      <div class="stat-tile"><div class="label">${x.name}</div>
        <div class="value">${num(last[x.key], x.dec)}</div>
        <div class="note">4주 전 대비 ${delta(rows, x.key, 4, x.dec)}
          · 12주 전 ${delta(rows, x.key, 12, x.dec)}</div></div>`).join('');

    document.querySelectorAll('.chips button').forEach(b =>
      b.setAttribute('aria-pressed', b.dataset.k === key));

    const head = '<tr><th>기준 주</th>' + META.map(x => `<th>${x.name}</th>`).join('')
               + '<th>분석 글</th></tr>';
    const body = rows.slice().reverse().map((r, i) => `
      <tr class="${i === 0 ? 'now' : ''}"><td>${r.date}${r.estimated ? '<span class="est">소급</span>' : ''}</td>`
      + META.map(x => `<td>${num(r[x.key], x.dec)}</td>`).join('')
      + `<td>${r.n}</td></tr>`).join('');
    document.getElementById('tbl').innerHTML = '<thead>' + head + '</thead><tbody>' + body + '</tbody>';
  }

  document.querySelectorAll('.chips button').forEach(b =>
    b.onclick = () => { key = b.dataset.k; draw(); });
  const sel = document.getElementById('userSel');
  if (sel) sel.onchange = () => { user = sel.value; draw(); };
  draw();
})();
</script>"""


def build():
    store = analysis_history._load(analysis_history.STORE, {})
    store = {u: r for u, r in (store or {}).items() if r}
    if not store:
        inner = ('<section><p class="sub">아직 기록이 없습니다. '
                 '내일 아침 수집이 돌면 첫 스냅샷이 남습니다.</p></section>')
        html = layout.document("ig", "trend", "지난 분석", inner, PAGE_CSS,
                               lead="콘텐츠 분석 수치가 어떻게 변해 왔는지 봅니다.")
        with open(os.path.join(DIR, "analysis-trend.html"), "w", encoding="utf-8") as f:
            f.write(html)
        print("저장됨: analysis-trend.html (기록 없음)")
        return

    meta = [{"key": k, "name": nm, "unit": u, "dec": d, "why": why}
            for k, nm, u, d, _, why in METRICS]
    users = list(store)
    picker = ""
    if len(users) > 1:
        opts = "".join(f'<option value="{layout._esc(u)}">@{layout._esc(u)}</option>'
                       for u in users)
        picker = f'<select id="userSel" class="seg">{opts}</select>'

    chips = "".join(f'<button data-k="{m["key"]}" aria-pressed="false">{m["name"]}</button>'
                    for m in meta)
    n_est = sum(1 for r in store[users[0]] if r.get("estimated"))
    n_real = len(store[users[0]]) - n_est
    first = store[users[0]][0]["date"]

    inner = f"""
<section>
  <div class="trend-h">
    <div><h2>지금 어디쯤인가</h2>
      <p class="sub">가장 최근 기록 기준 · 4주 전, 12주 전과 견줍니다</p></div>
    {picker}
  </div>
  <div class="mini" id="mini"></div>
</section>

<section>
  <h2 id="metricName">추세</h2>
  <p class="sub" id="metricWhy"></p>
  <div class="chips">{chips}</div>
  <svg id="sv"></svg>
</section>

<section>
  <h2>주간 기록</h2>
  <p class="sub">매주 월요일 아침 한 줄씩 쌓입니다 · 모두 {len(store[users[0]])}주</p>
  <div class="note-box">
    <b>소급</b> 표시가 붙은 줄은 지금 데이터로 과거를 거슬러 계산한 값입니다
    ({first}부터 {n_est}주). 게시물 지표는 한 달만 지나면 거의 변하지 않아 오차가 작지만,
    <b>그 시절 팔로워 수를 모르기 때문에 현재 팔로워 수로 나눴습니다</b> —
    팔로워가 늘고 있다면 과거 반응률은 실제보다 낮게 보입니다.
    실제로 그 주에 재서 남긴 기록은 {n_real}주치이고, 앞으로 매주 한 줄씩 늘어납니다.
    그래프에서 속이 빈 점이 소급분입니다.
  </div>
  <div class="wrap-x"><table class="trend" id="tbl"></table></div>
</section>

<script id="trend-data" type="application/json">{json.dumps(store, ensure_ascii=False)}</script>
<script id="trend-meta" type="application/json">{json.dumps(meta, ensure_ascii=False)}</script>"""

    html = layout.document(
        "ig", "trend", "지난 분석", inner, PAGE_CSS, body_end=JS,
        lead="콘텐츠 분석 수치가 어떻게 변해 왔는지 봅니다. "
             "숫자 하나가 아니라 방향을 보는 화면입니다.")
    with open(os.path.join(DIR, "analysis-trend.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print(f"저장됨: analysis-trend.html (계정 {len(users)}개 · "
          f"{len(store[users[0]])}주 · 소급 {n_est} / 실측 {n_real})")


if __name__ == "__main__":
    build()
