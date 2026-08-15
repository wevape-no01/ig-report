"""
네 페이지가 공유하는 껍데기(사이트 이름 / 상단 플랫폼 탭 / 왼쪽 세부 메뉴).

구조:
  WEVAPE SNS 운영 현황
  ├ 인스타그램 ─┬ 일일 리포트   (index.html)
  │             ├ 주간 리포트   (weekly.html)
  │             └ 콘텐츠 분석   (analysis.html)
  └ 스레드     ─┬ 일일 리포트   (threads.html)
                ├ 주간 리포트   (threads-weekly.html)
                └ 콘텐츠 분석   (threads-analysis.html)

각 페이지 생성기는 본문 HTML 과 자기 CSS 만 만들고 document() 로 감싼다.
"""

SITE = "WEVAPE SNS 운영 현황"

PLATFORMS = [
    ("ig", "인스타그램", "./"),
    ("th", "스레드", "./threads.html"),
]

SUBPAGES = {
    "ig": [("daily", "일일 리포트", "./"),
           ("weekly", "주간 리포트", "./weekly.html"),
           ("analysis", "콘텐츠 분석", "./analysis.html")],
    "th": [("daily", "일일 리포트", "./threads.html"),
           ("weekly", "주간 리포트", "./threads-weekly.html"),
           ("analysis", "콘텐츠 분석", "./threads-analysis.html")],
}

SHELL_CSS = """
:root { color-scheme: light only;
  --sh-text:#111; --sh-text2:#444; --sh-muted:#6b6b6b;
  --sh-line:#e6e6e6; --sh-border:rgba(17,17,17,.14); --sh-accent:#1f6fc7; }
* { box-sizing:border-box; }
html, body { background:#fff; }
body { margin:0; color:var(--sh-text);
       font-family:system-ui,-apple-system,"Segoe UI",sans-serif; }
.site-h { border-bottom:1px solid var(--sh-line); background:#fff;
          position:sticky; top:0; z-index:20; }
.site-h .inner { max-width:1180px; margin:0 auto; padding:16px 20px 0;
                 display:flex; flex-direction:column; gap:12px; }
.brand { font-size:15px; font-weight:750; letter-spacing:-0.01em; }
.brand span { color:var(--sh-muted); font-weight:400; font-size:12px; margin-left:8px; }
.plat { display:flex; gap:24px; }
.plat a { font-size:15px; font-weight:600; color:var(--sh-muted); text-decoration:none;
          padding:6px 2px 11px; border-bottom:2px solid transparent; }
.plat a:hover { color:var(--sh-text2); }
.plat a.on { color:var(--sh-accent); border-bottom-color:var(--sh-accent); }
.cols { max-width:1180px; margin:0 auto; padding:24px 20px 72px;
        display:grid; grid-template-columns:172px 1fr; gap:32px; align-items:start; }
.side { position:sticky; top:96px; display:flex; flex-direction:column; gap:3px; }
.side a { font-size:13.5px; color:var(--sh-text2); text-decoration:none;
          padding:9px 12px; border-radius:8px; }
.side a:hover { background:#f4f6f9; }
.side a.on { background:var(--sh-accent); color:#fff; font-weight:650; }
.main { min-width:0; }
.page-h { display:flex; justify-content:space-between; align-items:baseline;
          flex-wrap:wrap; gap:10px; margin-bottom:18px; }
.page-h h1 { font-size:22px; margin:0; letter-spacing:-0.01em; }
.page-h .updated { font-size:12px; color:var(--sh-muted); }
.stale { display:none; background:#fdecec; border:1px solid #f3b9b9; color:#8a1f1f;
  border-radius:10px; padding:12px 16px; font-size:13px; line-height:1.65; margin-bottom:18px; }
.stale.on { display:block; }
.stale b { color:#6b1414; }
.stale a { color:#8a1f1f; text-decoration:underline; }
/* ---------------- 알림 (오른쪽 위 종) ---------------- */
.site-h .top { display:flex; justify-content:space-between; align-items:center; gap:12px; }
.bell-wrap { position:relative; }
.bell { position:relative; border:1px solid var(--sh-border); background:#fff;
        border-radius:9px; width:36px; height:34px; cursor:pointer; padding:0;
        display:flex; align-items:center; justify-content:center; }
.bell:hover { background:#f4f6f9; }
.bell svg { width:17px; height:17px; stroke:var(--sh-text2); fill:none; stroke-width:1.7;
            stroke-linecap:round; stroke-linejoin:round; }
.bell.unread { border-color:#d33; }
.bell.unread svg { stroke:#d33; }
.bell .count { position:absolute; top:-6px; right:-6px; min-width:17px; height:17px;
  background:#d33; color:#fff; border-radius:99px; font-size:10.5px; font-weight:700;
  line-height:17px; text-align:center; padding:0 4px; display:none; }
.bell.unread .count { display:block; }
@keyframes bell-pulse { 0%,100%{ box-shadow:0 0 0 0 rgba(221,51,51,.45);} 55%{ box-shadow:0 0 0 7px rgba(221,51,51,0);} }
.bell.unread { animation:bell-pulse 2s ease-out 3; }
.panel { position:absolute; right:0; top:42px; width:330px; max-width:calc(100vw - 28px);
  background:#fff; border:1px solid var(--sh-border); border-radius:12px; z-index:90;
  box-shadow:0 10px 34px rgba(17,17,17,.16); display:none; overflow:hidden; }
.panel.on { display:block; }
.panel .p-h { display:flex; justify-content:space-between; align-items:center;
  padding:11px 14px; border-bottom:1px solid var(--sh-line); font-size:12.5px; font-weight:700; }
.panel .p-h button { border:0; background:none; color:var(--sh-accent); cursor:pointer;
  font-family:inherit; font-size:11.5px; font-weight:600; padding:2px 4px; }
.panel .p-b { max-height:min(60vh,420px); overflow-y:auto; }
.nt { display:flex; gap:9px; padding:12px 14px; border-bottom:1px solid var(--sh-line);
      cursor:pointer; }
.nt:last-child { border-bottom:0; }
.nt:hover { background:#f7f9fc; }
.nt .dot { width:7px; height:7px; border-radius:99px; margin-top:5px; flex:0 0 auto;
           background:var(--sh-accent); }
.nt.error .dot { background:#d33; } .nt.warn .dot { background:#d68000; }
.nt.ok .dot { background:#046a04; }
.nt.read .dot { background:#d3d3d3; }
.nt .tx { min-width:0; }
.nt .t { font-size:12.5px; font-weight:700; line-height:1.45; }
.nt.read .t { font-weight:500; color:var(--sh-text2); }
.nt .b { font-size:11.5px; color:var(--sh-muted); line-height:1.6; margin-top:3px;
         word-break:break-word; }
.nt .w { font-size:10.5px; color:var(--sh-muted); margin-top:5px; }
.nt-empty { padding:22px 14px; text-align:center; font-size:12px; color:var(--sh-muted); }
/* 팝업 (버튼을 누르지 않아도 바로 뜬다) */
.toasts { position:fixed; right:18px; top:74px; z-index:80;
          display:flex; flex-direction:column; gap:10px; width:330px;
          max-width:calc(100vw - 28px); }
.toast { background:#fff; border:1px solid var(--sh-border); border-left:4px solid var(--sh-accent);
  border-radius:11px; box-shadow:0 10px 30px rgba(17,17,17,.18); padding:12px 13px;
  animation:toast-in .28s ease-out; }
.toast.error { border-left-color:#d33; } .toast.warn { border-left-color:#d68000; }
.toast.ok { border-left-color:#046a04; }
@keyframes toast-in { from { opacity:0; transform:translateY(-8px); } to { opacity:1; transform:none; } }
.toast .t { font-size:12.5px; font-weight:700; line-height:1.45; padding-right:18px; }
.toast .b { font-size:11.5px; color:var(--sh-text2); line-height:1.6; margin-top:4px; }
.toast .r { display:flex; gap:8px; align-items:center; margin-top:10px; }
.toast .r button, .toast .r a { border:1px solid var(--sh-border); background:#fff;
  border-radius:7px; font-family:inherit; font-size:11.5px; font-weight:600; padding:5px 11px;
  cursor:pointer; color:var(--sh-text2); text-decoration:none; }
.toast .r button.on { background:var(--sh-accent); border-color:var(--sh-accent); color:#fff; }
.toast .x { position:absolute; }
.toast-close { float:right; border:0; background:none; cursor:pointer; color:var(--sh-muted);
  font-size:15px; line-height:1; padding:0 0 0 6px; font-family:inherit; }
@media (max-width:820px) {
  .toasts { right:10px; left:10px; width:auto; top:66px; }
  .panel { width:min(330px, calc(100vw - 20px)); }
  .cols { grid-template-columns:1fr; gap:18px; padding:18px 14px 64px; }
  .side { position:static; flex-direction:row; gap:6px; flex-wrap:wrap;
          border-bottom:1px solid var(--sh-line); padding-bottom:14px; }
  .side a { border:1px solid var(--sh-border); border-radius:999px; padding:7px 14px; }
  .side a.on { border-color:var(--sh-accent); }
  .site-h .inner { padding:14px 14px 0; }
  .plat { gap:18px; }
}
"""


def fmt_updated(iso):
    """2026-08-13T09:19:56+00:00 → "업데이트: 2026-08-13 18:19 (한국시간)" """
    if not iso:
        return ""
    from datetime import datetime, timedelta
    for f in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S"):
        try:
            dt = datetime.strptime(iso, f) + timedelta(hours=9)
            return f"업데이트: {dt:%Y-%m-%d %H:%M} (한국시간)"
        except ValueError:
            continue
    return f"업데이트: {iso}"


def _esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


STALE_JS = """<script>
(function () {
  // 수집이 실패하면 페이지가 다시 만들어지지 않는다.
  // 그래서 "마지막 갱신이 언제였는지"만 보면 실패를 알아챌 수 있다.
  var el = document.getElementById('stale');
  if (!el) return;
  var iso = el.dataset.generated;
  if (!iso) return;
  var t = new Date(iso);
  if (isNaN(t)) return;
  var hours = (Date.now() - t.getTime()) / 3600000;
  if (hours < 36) return;
  var days = Math.floor(hours / 24);
  var when = days >= 1 ? (days + '일') : (Math.floor(hours) + '시간');
  el.innerHTML = '\u26a0\ufe0f <b>' + when + '째 데이터가 갱신되지 않았습니다.</b> ' +
    '매일 아침 7시에 자동 수집되어야 하는데 실패한 것으로 보입니다. ' +
    '<a href="https://github.com/wevape-no01/ig-report/actions" target="_blank" rel="noopener">' +
    '실행 기록 확인</a> · 아래 숫자는 마지막으로 성공한 시점의 값입니다.';
  el.className = 'stale on';
})();
</script>"""


NOTICE_HTML = """
  <div class="bell-wrap">
    <button class="bell" id="bell" aria-label="알림" aria-expanded="false">
      <svg viewBox="0 0 24 24"><path d="M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"/>
        <path d="M13.7 21a2 2 0 0 1-3.4 0"/></svg>
      <span class="count" id="bellCount">0</span>
    </button>
    <div class="panel" id="panel">
      <div class="p-h"><span>알림</span><button id="markAll">모두 읽음</button></div>
      <div class="p-b" id="panelBody"></div>
    </div>
  </div>"""

# 읽음 여부는 이 브라우저에만 저장한다. 서버에 기록하지 않는다.
NOTICE_JS = """<script>
(function () {
  var KEY = 'wevape-sns-read';
  var bell = document.getElementById('bell');
  if (!bell) return;
  var panel = document.getElementById('panel');
  var body  = document.getElementById('panelBody');
  var count = document.getElementById('bellCount');
  var stack = document.getElementById('toasts');
  var items = [];

  function readIds() {
    try { return JSON.parse(localStorage.getItem(KEY) || '[]') || []; }
    catch (e) { return []; }
  }
  function saveIds(a) {
    try { localStorage.setItem(KEY, JSON.stringify(a.slice(-80))); } catch (e) {}
  }
  function isRead(id) { return readIds().indexOf(id) !== -1; }
  function markRead(id) {
    var a = readIds();
    if (a.indexOf(id) === -1) { a.push(id); saveIds(a); }
    paint();
  }
  function esc(t) {
    return (t || '').replace(/[<>&"]/g, function (c) {
      return ({'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;'})[c]; });
  }

  function paint() {
    var unread = items.filter(function (n) { return !isRead(n.id); });
    count.textContent = unread.length > 9 ? '9+' : String(unread.length);
    bell.classList.toggle('unread', unread.length > 0);
    if (!items.length) {
      body.innerHTML = '<div class="nt-empty">알림이 없습니다.</div>';
      return;
    }
    body.innerHTML = items.map(function (n) {
      var read = isRead(n.id);
      return '<div class="nt ' + esc(n.level) + (read ? ' read' : '') +
        '" data-id="' + esc(n.id) + '"><span class="dot"></span><div class="tx">' +
        '<div class="t">' + esc(n.title) + '</div>' +
        (n.body ? '<div class="b">' + esc(n.body) + '</div>' : '') +
        '<div class="w">' + esc(n.at) + (read ? '' : ' · 읽지 않음') + '</div>' +
        '</div></div>';
    }).join('');
    body.querySelectorAll('.nt').forEach(function (el) {
      el.onclick = function () {
        var n = items.filter(function (x) { return x.id === el.dataset.id; })[0];
        markRead(el.dataset.id);
        if (n && n.link) window.open(n.link, '_blank', 'noopener');
      };
    });
  }

  // 버튼을 누르지 않아도 안 읽은 알림은 팝업으로 바로 뜬다 (최대 3개)
  function popup() {
    if (!stack) return;
    items.filter(function (n) { return !isRead(n.id); }).slice(0, 3).forEach(function (n) {
      var d = document.createElement('div');
      d.className = 'toast ' + n.level;
      d.innerHTML = '<button class="toast-close" aria-label="닫기">&times;</button>' +
        '<div class="t">' + esc(n.title) + '</div>' +
        (n.body ? '<div class="b">' + esc(n.body) + '</div>' : '') +
        '<div class="r"><button class="ok on">읽음</button>' +
        (n.link ? '<a href="' + esc(n.link) + '">열어보기</a>' : '') + '</div>';
      // X 는 이번만 숨기기 — 안 읽은 상태는 그대로 남는다
      d.querySelector('.toast-close').onclick = function () { d.remove(); };
      d.querySelector('.ok').onclick = function () { markRead(n.id); d.remove(); };
      stack.appendChild(d);
    });
  }

  bell.onclick = function (e) {
    e.stopPropagation();
    var on = panel.classList.toggle('on');
    bell.setAttribute('aria-expanded', on ? 'true' : 'false');
    // 팝업과 목록이 같은 자리에 겹친다. 목록을 열면 팝업은 치운다.
    // (읽음 처리는 하지 않으므로 안 읽은 표시는 그대로 남는다)
    if (on && stack) stack.innerHTML = '';
  };
  document.addEventListener('click', function (e) {
    if (!panel.contains(e.target)) panel.classList.remove('on');
  });
  document.getElementById('markAll').onclick = function (e) {
    e.stopPropagation();
    saveIds(items.map(function (n) { return n.id; }));
    if (stack) stack.innerHTML = '';
    paint();
  };

  // 캐시를 피하려고 시각을 붙인다 (GitHub Pages 는 파일을 오래 물고 있다)
  fetch('./notices.json?t=' + Date.now(), {cache: 'no-store'})
    .then(function (r) { return r.ok ? r.json() : []; })
    .then(function (d) {
      items = Array.isArray(d) ? d : [];
      paint();
      popup();
    })
    .catch(function () { paint(); });
})();
</script>"""


def document(platform, page, page_title, inner, page_css="",
             updated="", body_end="", generated_iso=""):
    """platform: 'ig' | 'th'   page: 'daily' | 'analysis'"""
    plat_links = "".join(
        f'<a class="{"on" if k == platform else ""}" href="{href}">{name}</a>'
        for k, name, href in PLATFORMS)
    side_links = "".join(
        f'<a class="{"on" if k == page else ""}" href="{href}">{name}</a>'
        for k, name, href in SUBPAGES[platform])
    plat_name = next(n for k, n, _ in PLATFORMS if k == platform)

    return f"""<!doctype html>
<html lang="ko"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<title>{_esc(page_title)} · {_esc(plat_name)} · WEVAPE SNS</title>
<style>{SHELL_CSS}{page_css}</style>
</head><body>
<header class="site-h"><div class="inner">
  <div class="top">
    <div class="brand">{_esc(SITE)}</div>
{NOTICE_HTML}
  </div>
  <nav class="plat">{plat_links}</nav>
</div></header>
<div class="toasts" id="toasts"></div>
<div class="cols">
  <aside class="side">{side_links}</aside>
  <main class="main">
    <div class="page-h"><h1>{_esc(page_title)}</h1>
      <span class="updated">{_esc(updated)}</span></div>
    <div class="stale" id="stale" data-generated="{_esc(generated_iso)}"></div>
{inner}
  </main>
</div>
{body_end}
{STALE_JS}
{NOTICE_JS}
</body></html>"""
