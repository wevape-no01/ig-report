"""
주간 리포트 두 페이지를 만든다.
  weekly.html          인스타그램 (왼쪽 메뉴: 일일 / 주간 / 콘텐츠 분석)
  threads-weekly.html  스레드

weekly.py 가 계산한 숫자만 그린다. API 는 부르지 않는다.
실행: python3 build_weekly.py
"""

import os

import layout
import weekly

DIR = os.path.dirname(os.path.abspath(__file__))

# 업계 벤치마크 — 콘텐츠 분석(build_analysis.py)과 같은 값을 쓴다. 한쪽만 고치지 말 것.
#   출처: Socialinsider "Instagram Benchmarks 2026"
#   실제 기간은 2025-01~12 · 계정 447,613개 · 게시물 3,500만 개 · 전 세계 전 산업
#   계산식: (좋아요 + 댓글) ÷ 팔로워 × 100   ← 저장·공유는 넣지 않는다
BENCH_ER_FOLLOWERS = 0.48
BENCH_SOURCE = "Socialinsider 2026 벤치마크"
BENCH_NOTE = ("실제로는 2025년 1~12월 값 · 계정 447,613개 · 게시물 3,500만 개 · "
              "전 세계 전 산업 기준")

CSS = """
:root {
  color-scheme: light only;
  --text-primary:#1A1A1A; --text-secondary:#54524B; --text-muted:#7a756a;
  --gridline:#E7E2D6; --border:#E7E2D6;
  --series-1:#1A1A1A; --good:#1F8A45; --critical:#C1392B;
}
* { box-sizing:border-box; }
html, body { background:#F4F1E8; }
/* 글꼴은 layout.py(SHELL_CSS)에서 한 곳으로 정한다. 여기서 다시 정하지 않는다. */
body { margin:0; color:#1A1A1A; }
.period { font-size:13px; color:var(--text-secondary); margin:2px 0 20px; }
.period b { color:var(--text-primary); }
.period-s { font-size:11.5px; color:var(--text-muted); }
.hero-box { display:flex; align-items:baseline; gap:12px; flex-wrap:wrap; margin:0 0 4px; }
.hero-box .hn { font-size:38px; font-weight:650; line-height:1; letter-spacing:-0.02em; }
.hero-box .hu { font-size:17px; color:var(--text-muted); font-weight:600; }
.hero-box .hl { font-size:13px; color:var(--text-secondary); font-weight:600; }
.hero-s { font-size:11.5px; color:var(--text-muted); margin:0 0 16px; }
section { background:#fff; border:1px solid var(--border); border-radius:10px;
          padding:18px 18px 16px; margin-bottom:20px; }
section h2 { font-size:20px; margin:0 0 3px; font-weight:700; letter-spacing:-0.01em; }
section .sub { font-size:11.5px; color:var(--text-muted); margin:0 0 14px; line-height:1.6; }
.kpi-row { display:grid; grid-template-columns:repeat(auto-fit,minmax(158px,1fr)); gap:12px; }
.stat-tile { background:#fff; border:1px solid var(--border); border-radius:10px; padding:14px 16px; }
.stat-tile .label { font-size:12px; color:var(--text-secondary); margin-bottom:6px; font-weight:600; }
.stat-tile .value { font-size:30px; font-weight:650; line-height:1.1; }
.stat-tile .note { font-size:11px; color:var(--text-muted); margin-top:6px; line-height:1.5; }
.up { color:var(--good); } .down { color:var(--critical); }
table { width:100%; border-collapse:collapse; font-size:12.5px; margin-top:14px; }
th, td { text-align:left; padding:8px 6px; border-bottom:1px solid var(--gridline); vertical-align:top; }
th { color:var(--text-muted); font-weight:500; font-size:10.5px;
     text-transform:uppercase; letter-spacing:.02em; white-space:nowrap; }
td.num { text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }
td.cap { max-width:340px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;
         color:var(--text-secondary); }
td.strong { font-weight:650; color:var(--text-primary); }
a { color:#8A6A00; text-decoration:none; } a:hover { text-decoration:underline; }
.empty { color:var(--text-muted); font-size:12.5px; padding:8px 0; margin:0; }
.foot { font-size:11.5px; color:var(--text-muted); line-height:1.8; }
.foot b { color:var(--text-secondary); }
section h2::before, h3::before { content:"● "; color:#FFC800; font-size:11px; vertical-align:2px; }
/* 반응률 근거·계산식 — 본문보다 작고 흐리게. 콘텐츠 분석의 .basis 와 같은 모양 */
.basis { margin:0 0 16px; padding:10px 12px; border:1px solid #EEE0B8; border-radius:8px;
  background:#FDFBF4; font-size:12px; color:var(--text-secondary); line-height:1.65; }
.basis .eq { font-variant-numeric:tabular-nums; color:var(--text-primary); font-weight:600; }
.basis .src { display:block; margin-top:5px; font-size:11px; color:var(--text-muted);
  line-height:1.55; }
.basis .cmp { font-weight:700; }
.basis .cmp.good { color:var(--good); } .basis .cmp.bad { color:var(--critical); }

"""


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def n(v, unit=""):
    return "기록 없음" if v is None else f"{v:,}{unit}"


def delta_note(d, pct, unit=""):
    """지난주 대비 한 줄. 값이 없으면 안내 문구."""
    if d is None:
        return "지난주 비교값 없음"
    if d == 0:
        return "지난주와 같음"
    cls = "up" if d > 0 else "down"
    body = f"{'+' if d > 0 else ''}{d:,}{unit}"
    if pct is not None:
        body += f" · {'+' if d > 0 else ''}{pct}%"
    return f'<span class="{cls}">{body}</span> (지난주 대비)'


def hero(rate, note):
    """반응률을 맨 위에 크게. 값이 없으면 아무것도 안 그린다."""
    if rate is None:
        return ""
    return (f'<div class="hero-box"><span class="hn">{rate:.2f}</span>'
            f'<span class="hu">%</span><span class="hl">반응률</span></div>'
            f'<p class="hero-s">{note}</p>')


def basis_ig(m):
    """반응률 바로 아래 붙는 근거 한 칸 — 어떤 식으로 냈고 업계 평균의 몇 배인지.

    반응률 자체를 업계 벤치마크와 같은 식으로 내므로, "그대로 견줄 수 없다"는 설명은
    필요 없다. 식 한 줄과 배수만 남긴다.
    도달 대비 반응은 성격이 다른 지표(소재의 힘)라 보조로만 덧붙인다.
    """
    br = m.get("bench_rate")
    if br is None:
        return ""
    x = br / BENCH_ER_FOLLOWERS if BENCH_ER_FOLLOWERS else 0
    cls = "good" if br >= BENCH_ER_FOLLOWERS else "bad"
    out = ('<div class="basis">'
           f'근거 · <span class="eq">(좋아요+댓글) ÷ 팔로워 × 100</span> 으로 냈습니다. '
           f'최근 {m.get("bench_n") or 0}개 게시물 평균, 팔로워 {n(m.get("followers"), "명")} 기준 '
           f'(콘텐츠 분석 페이지와 같은 값). '
           f'<span class="cmp {cls}">업계 평균 {BENCH_ER_FOLLOWERS}%의 {x:.1f}배</span>입니다.')
    if m.get("react_rate") is not None:
        out += (f'<br>참고 · 도달 대비 반응은 <b>{m["react_rate"]:.2f}%</b>입니다 '
                f'<span class="eq">((좋아요+댓글+저장+공유) ÷ 도달 × 100)</span>. '
                f'본 사람이 얼마나 움직였는지를 보는 값이라 업계 평균과는 비교하지 않습니다.')
    out += (f'<span class="src">출처 {BENCH_SOURCE} · {BENCH_NOTE}. '
            '전 세계 전 산업 평균이라 인천 지역 소형 계정과는 조건이 달라 방향만 참고합니다.</span>')
    return out + "</div>"


def tile(label, value, note=""):
    return (f'<div class="stat-tile"><div class="label">{label}</div>'
            f'<div class="value">{value}</div>'
            f'<div class="note">{note}</div></div>')


def top_table(rows, col, unit):
    if not rows:
        return '<p class="empty">이 기간에 올린 글이 없습니다.</p>'
    body = ""
    for r in rows:
        txt = esc(" ".join((r["text"] or "").split())) or "(내용 없음)"
        link = (f'<a href="{esc(r["permalink"])}" target="_blank" rel="noopener">{txt}</a>'
                if r.get("permalink") else txt)
        body += (f'<tr><td>{r["date"]}</td><td class="cap">{link}</td>'
                 f'<td class="num strong">{n(r["value"])}</td></tr>')
    return (f'<table><thead><tr><th>날짜</th><th>내용</th>'
            f'<th class="num">{col}</th></tr></thead><tbody>{body}</tbody></table>')


ISSUE_NOTE = """
<section>
  <div class="foot">
    이 페이지는 <b>어제까지의 7일</b>을 지난 7일과 견줍니다. 인스타그램은 어제까지의 값만
    확정해서 주기 때문에 오늘은 넣지 않습니다.<br>
    같은 내용이 <b>매주 월요일 아침 GitHub 이슈</b>로도 올라옵니다. GitHub 모바일 앱을
    깔고 이 저장소를 Watch 해두면 휴대폰으로 알림을 받습니다.
  </div>
</section>"""


def build_ig():
    accs = weekly.instagram()
    if not accs:
        lead = ''
        inner = '<p class="empty">아직 주간 요약을 만들 기록이 없습니다.</p>'
    else:
        a, b = accs[0]["start"], accs[0]["end"]
        lead = (f'<b>{a} ~ {b}</b> · 지난 7일을 그 앞 7일과 비교합니다.<br>'
                '숫자는 매일 아침 갱신되고, 매주 월요일 아침에 한 주 요약이 알림으로 옵니다.')
        inner = ''
        for m in accs:
            nf = delta_note(m["followers_delta"], m["followers_pct"], "명")
            inner += f"""
<section>
  <h2>{esc(m['label'])}</h2>
  <p class="sub">@{esc(m['user'])} · 이번 주 올린 게시물 {m['posted']}개</p>
  {hero(m['bench_rate'] if m.get('bench_rate') is not None else m['react_rate'],
        '업계 평균과 같은 식으로 낸 값 · 최근 게시물 기준')}
  {basis_ig(m)}
  <div class="kpi-row">
    {tile('신규 팔로워', n(m['new_followers'], '명'),
          delta_note(m['new_followers_delta'], m['new_followers_pct'], '명'))}
    {tile('도달', n(m['reach']), delta_note(m['reach_delta'], m['reach_pct']))}
    {tile('조회수', n(m['views']), delta_note(m['views_delta'], m['views_pct']))}
    {tile('현재 팔로워', n(m['followers'], '명'), nf)}
  </div>
  {top_table(m['top'], '도달', '')}
</section>"""
        inner += ISSUE_NOTE
    html = layout.document("ig", "weekly", "주간 리포트", inner, CSS, lead=lead)
    with open(os.path.join(DIR, "weekly.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print(f"저장됨: weekly.html (계정 {len(accs)}개)")


def build_th():
    m = weekly.threads()
    if not m:
        lead = ''
        inner = '<p class="empty">아직 스레드 주간 요약을 만들 기록이 없습니다.</p>'
    else:
        fd = ("증감 기록을 모으는 중입니다" if m["followers_delta"] is None
              else delta_note(m["followers_delta"], None, "명"))
        lead = (f"<b>{m['start']} ~ {m['end']}</b> · 지난 7일을 그 앞 7일과 비교합니다.<br>"
                "숫자는 매일 아침 갱신되고, 매주 월요일 아침에 한 주 요약이 알림으로 옵니다.")
        inner = f"""<section>
  <h2>스레드</h2>
  <p class="sub">@{esc(m.get('username') or '?')} · 이번 주 올린 글 {m['posted']}개</p>
  {hero(m['react_rate'], '조회 100회당 반응 수 · 스레드는 조회수보다 반응이 노출을 만듭니다')}
  <div class="kpi-row">
    {tile('조회수', n(m['views']), delta_note(m['views_delta'], m['views_pct']))}
    {tile('현재 팔로워', n(m['followers'], '명'), fd)}
    {tile('좋아요', n(m['likes']), '전체 기간 누적')}
    {tile('리포스트', n(m['reposts']), '전체 기간 누적')}
    {tile('답글', n(m['replies']), '전체 기간 누적')}
  </div>
  {top_table(m['top'], '조회', '')}
</section>{ISSUE_NOTE}"""
    html = layout.document("th", "weekly", "주간 리포트", inner, CSS, lead=lead)
    with open(os.path.join(DIR, "threads-weekly.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("저장됨: threads-weekly.html")


# ------------------------------------------------------- 지난 리포트 (주차 목록)
# 왼쪽 목록 / 오른쪽 리포트. 누르면 오른쪽만 바뀌므로 화면이 움직이지 않는다.
PAST_CSS = """
.two { display:grid; grid-template-columns:236px 1fr; gap:18px; align-items:start; }
@media (max-width:760px) { .two { grid-template-columns:1fr; } }
.wk-list { display:flex; flex-direction:column; gap:7px; }
.wk { border:1px solid var(--border); border-radius:9px; padding:11px 13px;
      cursor:pointer; background:#fff; }
.wk:hover { background:#FAF8F3; }
.wk.on { border-color:var(--series-1); background:#FFF9E3; }
.wk .t { font-size:13px; font-weight:700; }
.wk .d { font-size:11px; color:var(--text-muted); margin-top:2px; }
.wk .s { font-size:11px; color:var(--text-secondary); margin-top:5px; }
.pager { display:flex; justify-content:center; gap:5px; margin-top:11px; }
.pager button { border:1px solid var(--border); background:#fff; border-radius:7px;
  font-family:inherit; font-size:11px; min-width:26px; height:26px; cursor:pointer;
  color:var(--text-secondary); }
.pager button[aria-current="true"] { background:var(--series-1); border-color:var(--series-1);
  color:#FFC800; font-weight:700; }
.pager button:disabled { opacity:.35; cursor:default; }
.dim { color:var(--text-muted); }
/* 지나간 주를 훑어보는 용도라 오른쪽 리포트는 작게 줄인다 */
#wkCard .period { font-size:12px; margin:0 0 12px; }
#wkCard section { padding:14px 15px 13px; margin-bottom:13px; }
#wkCard section h2 { font-size:20px; }
#wkCard section .sub { font-size:11px; margin:0 0 11px; }
#wkCard .kpi-row { grid-template-columns:repeat(auto-fit,minmax(128px,1fr)); gap:9px; }
#wkCard .stat-tile { padding:10px 12px; border-radius:9px; }
#wkCard .stat-tile .label { font-size:11px; margin-bottom:4px; }
#wkCard .stat-tile .value { font-size:19px; }
#wkCard .stat-tile .note { font-size:10px; margin-top:4px; line-height:1.45; }
"""

PAST_JS = """<script>
(function () {
  const WEEKS = JSON.parse(document.getElementById('weeks').textContent);
  const KIND = document.getElementById('weeks').dataset.kind;
  const PER = 5;
  let page = 0, sel = 0;

  const n = (v, u) => (v === null || v === undefined) ? '-' : v.toLocaleString() + (u || '');
  function dl(d, pct, u) {
    if (d === null || d === undefined) return '<span class="dim">비교값 없음</span>';
    if (d === 0) return '<span class="dim">지난주와 같음</span>';
    const c = d > 0 ? 'up' : 'down';
    let s = (d > 0 ? '+' : '') + d.toLocaleString() + (u || '');
    if (pct !== null && pct !== undefined) s += ' · ' + (d > 0 ? '+' : '') + pct + '%';
    return '<span class="' + c + '">' + s + '</span> <span class="dim">(전주 대비)</span>';
  }
  const md = a => a.slice(5).replace('-', '/');
  const tile = (l, v, note) =>
    `<div class="stat-tile"><div class="label">${l}</div><div class="value">${v}</div>
     <div class="note">${note}</div></div>`;

  function summary(w) {
    if (KIND === 'th') {
      const t = w.th;
      if (!t) return '기록 없음';
      return '조회 ' + n(t.views) + ' · 팔로워 ' + n(t.followers, '명');
    }
    const m = (w.ig || [])[0];
    if (!m) return '기록 없음';
    return '신규 ' + n(m.new_followers, '명') + ' · 도달 ' + n(m.reach);
  }

  function card(w) {
    let h = `<p class="period"><b>${w.start} ~ ${w.end}</b> · 그 앞 7일과 비교합니다.</p>`;
    if (KIND === 'th') {
      const t = w.th;
      if (!t) return h + '<p class="empty">이 주는 기록이 없습니다.</p>';
      h += `<section><h2>스레드</h2>
        <p class="sub">@${t.username || '?'} · 이 주에 올린 글 ${t.posted}개</p>
        <div class="kpi-row">
          ${tile('조회수', n(t.views), dl(t.views_delta, t.views_pct))}
          ${tile('주말 기준 팔로워', n(t.followers, '명'), dl(t.followers_delta, null, '명'))}
          ${tile('좋아요', n(t.likes), '전체 기간 누적')}
          ${tile('리포스트', n(t.reposts), '전체 기간 누적')}
        </div></section>`;
      return h;
    }
    (w.ig || []).forEach(m => {
      h += `<section><h2>${m.label}</h2>
        <p class="sub">@${m.user} · 이 주에 올린 게시물 ${m.posted}개</p>
        <div class="kpi-row">
          ${tile('신규 팔로워', n(m.new_followers, '명'),
                 dl(m.new_followers_delta, m.new_followers_pct, '명'))}
          ${tile('도달', n(m.reach), dl(m.reach_delta, m.reach_pct))}
          ${tile('조회수', n(m.views), dl(m.views_delta, m.views_pct))}
          ${tile('주말 기준 팔로워', n(m.followers, '명'),
                 dl(m.followers_delta, m.followers_pct, '명'))}
        </div></section>`;
    });
    return h;
  }

  function draw() {
    const s = page * PER, part = WEEKS.slice(s, s + PER);
    document.getElementById('wkList').innerHTML = part.map((w, i) => `
      <div class="wk ${s + i === sel ? 'on' : ''}" data-i="${s + i}">
        <div class="t">${w.label}</div>
        <div class="d">${md(w.start)} ~ ${md(w.end)}</div>
        <div class="s">${summary(w)}</div></div>`).join('');
    document.querySelectorAll('.wk').forEach(el => el.onclick = () => {
      sel = +el.dataset.i; draw();
    });
    const pages = Math.ceil(WEEKS.length / PER);
    let p = `<button ${page === 0 ? 'disabled' : ''} data-p="${page - 1}">‹</button>`;
    for (let i = 0; i < pages; i++)
      p += `<button data-p="${i}" aria-current="${i === page}">${i + 1}</button>`;
    p += `<button ${page >= pages - 1 ? 'disabled' : ''} data-p="${page + 1}">›</button>`;
    document.getElementById('pager').innerHTML = pages > 1 ? p : '';
    document.querySelectorAll('#pager button').forEach(b => b.onclick = () => {
      page = +b.dataset.p; draw();
    });
    document.getElementById('wkCard').innerHTML = card(WEEKS[sel]);
  }
  draw();
})();
</script>"""


def build_past(platform, out_name):
    import json
    weeks = weekly.past_weeks()
    if not weeks:
        inner = '<p class="empty">아직 지난 리포트를 만들 기록이 없습니다.</p>'
        lead, body_end = "", ""
    else:
        lead = f'주차를 누르면 오른쪽에 그 주 리포트가 나옵니다 · 모두 {len(weeks)}주'
        inner = (
                 '<div class="two">'
                 '<div><div class="wk-list" id="wkList"></div>'
                 '<div class="pager" id="pager"></div></div>'
                 '<div id="wkCard"></div></div>'
                 f'<script id="weeks" type="application/json" data-kind="{platform}">'
                 f'{json.dumps(weeks, ensure_ascii=False)}</script>')
        body_end = PAST_JS
    html = layout.document(platform, "past", "지난 리포트", inner, CSS + PAST_CSS,
                           body_end=body_end, lead=lead)
    with open(os.path.join(DIR, out_name), "w", encoding="utf-8") as f:
        f.write(html)
    print(f"저장됨: {out_name} ({len(weeks)}주)")


if __name__ == "__main__":
    build_ig()
    build_th()
    build_past("ig", "weekly-past.html")
    build_past("th", "threads-weekly-past.html")
