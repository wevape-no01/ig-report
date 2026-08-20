"""
네 페이지가 공유하는 껍데기(사이트 이름 / 상단 플랫폼 탭 / 왼쪽 세부 메뉴).

구조:
  WEVAPE SNS 운영 현황
  ├ 인스타그램 ─┬ 일일 리포트   (index.html)
  │             ├ 주간 리포트   (weekly.html)
  │             ├ 콘텐츠 분석   (analysis.html)
  │             └ 세부 분석     (analysis-detail.html)
  └ 스레드     ─┬ 일일 리포트   (threads.html)
                ├ 주간 리포트   (threads-weekly.html)
                ├ 콘텐츠 분석   (threads-analysis.html)
                └ 세부 분석     (threads-detail.html)

각 페이지 생성기는 본문 HTML 과 자기 CSS 만 만들고 document() 로 감싼다.
"""

SITE = "WEVAPE SNS 운영 현황"

PLATFORMS = [
    ("ig", "인스타그램", "./"),
    ("th", "스레드", "./threads.html"),
]

# 네 번째 자리는 하위 메뉴. 부모나 자기 자신을 보고 있을 때만 펼쳐 보인다.
SUBPAGES = {
    "ig": [("daily", "일일 리포트", "./"),
           ("weekly", "주간 리포트", "./weekly.html",
            [("past", "지난 리포트", "./weekly-past.html")]),
           ("analysis", "콘텐츠 분석", "./analysis.html",
            [("detail", "세부 분석", "./analysis-detail.html")])],
    "th": [("daily", "일일 리포트", "./threads.html"),
           ("weekly", "주간 리포트", "./threads-weekly.html",
            [("past", "지난 리포트", "./threads-weekly-past.html")]),
           ("analysis", "콘텐츠 분석", "./threads-analysis.html",
            [("detail", "세부 분석", "./threads-detail.html")])],
}

SHELL_CSS = """
:root {
  color-scheme: light only;
  --yellow:#FFC800; --yellow-dim:#FFF3C4;
  --ink:#1A1A1A; --ink-soft:#54524B; --paper:#FFFFFF;
  --line:#E7E2D6; --bg:#F4F1E8; --side:#1A1A1A; --side-text:#E8E2D3;
  --sh-text:#1A1A1A; --sh-text2:#54524B; --sh-muted:#7a756a;
  --sh-line:#E7E2D6; --sh-border:#E7E2D6; --sh-accent:#1A1A1A;
}
* { box-sizing:border-box; }
html, body { background:var(--bg); }
body { margin:0; color:var(--ink); font-size:14px;
       font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Pretendard,sans-serif; }

.shell { display:grid; grid-template-columns:210px 1fr; min-height:100vh; }

/* ---------------- 왼쪽: 브랜드 + 페이지 메뉴 ---------------- */
.side { background:var(--side); color:var(--side-text); position:sticky; top:0;
        height:100vh; padding:22px 12px; }
.brand { padding:0 6px 18px; border-bottom:1px solid #2e2e2e; margin-bottom:16px; }
.brand b { display:block; color:var(--yellow); font-weight:800; font-size:19px;
           letter-spacing:-.02em; line-height:1.25; }
.brand span { display:block; color:#c4beb0; font-weight:650; font-size:13.5px;
              margin-top:5px; letter-spacing:-.01em; }
.menu a { display:block; font-size:13px; color:var(--side-text); text-decoration:none;
          padding:9px 11px; border-radius:7px; margin-bottom:2px; }
.menu a::before { content:"● "; color:#4a4a4a; font-size:9px; vertical-align:2px; }
.menu a:hover { background:#232323; }
.menu a.on { background:#262626; color:var(--yellow); font-weight:700; }
.menu a.on::before { color:var(--yellow); }
.menu a.sub { margin-left:13px; font-size:12px; color:#a9a396; padding:6px 11px; }
.menu a.sub::before { content:"- "; color:#5a5a5a; }
.menu a.sub.on { background:#262626; color:var(--yellow); }

/* ---------------- 맨 위: 상위 메뉴(플랫폼) ---------------- */
.topbar { background:var(--side); position:sticky; top:0; z-index:20; padding:0 30px;
          display:flex; justify-content:space-between; align-items:center; gap:16px; }
.plat { display:flex; gap:26px; }
.plat a { font-size:14.5px; font-weight:650; color:#a9a396; text-decoration:none;
          padding:16px 2px 14px; border-bottom:3px solid transparent; letter-spacing:-.01em; }
.plat a:hover { color:var(--side-text); }
.plat a.on { color:var(--yellow); border-bottom-color:var(--yellow); font-weight:750; }
/* 오른쪽: 외부 링크 버튼 + 알림 종 */
.top-right { display:flex; align-items:center; gap:12px; }
.ext { display:inline-flex; align-items:center; gap:5px; font-size:13px; font-weight:650;
       color:var(--side-text); text-decoration:none; border:1px solid #3a3a3a;
       border-radius:999px; padding:7px 14px; white-space:nowrap; }
.ext span { font-size:11px; color:#8f8a7e; }
.ext:hover { border-color:var(--yellow); color:var(--yellow); }
.ext:hover span { color:var(--yellow); }

.col { min-width:0; }   /* 넓은 표·그래프가 폰에서 화면 밖으로 밀지 않게 */
.main { padding:24px 30px 64px; max-width:1120px; min-width:0; }
.page-h { display:flex; justify-content:space-between; align-items:baseline;
          flex-wrap:wrap; gap:10px; border-bottom:1px solid var(--line);
          padding-bottom:12px; margin-bottom:6px; }
.page-h h1 { font-size:24px; font-weight:700; margin:0; letter-spacing:-.02em; }
.page-h .updated { font-size:12px; color:var(--ink-soft); }
/* 제목 아래 한 줄 — 내용이 없어도 자리를 지켜 첫 카드 높이가 안 바뀐다 */
/* 제목 아래 두 줄은 내용이 없어도 자리를 지킨다. 그래야 어느 페이지를 눌러도
   첫 카드가 같은 높이에서 시작한다. */
.scope, .period { font-size:12px; color:var(--ink-soft); line-height:1.6;
                  min-height:38px; margin:0 0 10px; }   /* 두 줄 자리 확보 */
.tabslot { min-height:34px; margin-bottom:12px; display:flex; align-items:center; }
.tabslot > * { margin:0 !important; }
.stale { display:none; background:#fdecec; border:1px solid #f3b9b9; color:#8a1f1f;
  border-radius:10px; padding:12px 16px; font-size:13px; line-height:1.65; margin-bottom:16px; }
.stale.on { display:block; }
.stale b { color:#6b1414; }
.stale a { color:#8a1f1f; text-decoration:underline; }

/* 접었다 펴는 상자 */
details.tg { border:1px solid var(--line); border-radius:10px; margin-bottom:16px;
             background:var(--paper); }
details.tg > summary { cursor:pointer; padding:13px 16px; font-size:13.5px; font-weight:700;
  color:var(--ink-soft); list-style:none; display:flex; align-items:center; gap:8px; }
details.tg > summary::-webkit-details-marker { display:none; }
details.tg > summary::before { content:"▸"; color:var(--yellow); font-size:11px; }
details.tg[open] > summary::before { content:"▾"; }
details.tg[open] > summary { border-bottom:1px solid var(--line); }
details.tg .tg-body { padding:15px 16px 16px; }

/* ---------------- 알림 (오른쪽 위 종) ---------------- */
.bell-wrap { position:relative; }
.bell { position:relative; border:1px solid #3a3a3a; background:#262626;
        border-radius:9px; width:36px; height:34px; cursor:pointer; padding:0;
        display:flex; align-items:center; justify-content:center; }
.bell:hover { background:#333; }
.bell svg { width:17px; height:17px; stroke:#c4beb0; fill:none; stroke-width:1.7;
            stroke-linecap:round; stroke-linejoin:round; }
.bell.unread { border-color:var(--yellow); }
.bell.unread svg { stroke:var(--yellow); }
.bell .count { position:absolute; top:-6px; right:-6px; min-width:17px; height:17px;
  background:#d33; color:#fff; border-radius:99px; font-size:10.5px; font-weight:700;
  line-height:17px; text-align:center; padding:0 4px; display:none; }
.bell.unread .count { display:block; }
@keyframes bell-pulse { 0%,100%{ box-shadow:0 0 0 0 rgba(255,200,0,.45);} 55%{ box-shadow:0 0 0 7px rgba(255,200,0,0);} }
.bell.unread { animation:bell-pulse 2s ease-out 3; }
.panel { position:absolute; right:0; top:44px; width:330px; max-width:calc(100vw - 28px);
  background:var(--paper); border:1px solid var(--line); border-radius:12px; z-index:90;
  box-shadow:0 10px 34px rgba(26,26,26,.22); display:none; overflow:hidden; }
.panel.on { display:block; }
.panel .p-h { display:flex; justify-content:space-between; align-items:center;
  padding:11px 14px; border-bottom:1px solid var(--line); font-size:12.5px; font-weight:700; }
.panel .p-h button { border:0; background:none; color:#8A6A00; cursor:pointer;
  font-family:inherit; font-size:11.5px; font-weight:700; padding:2px 4px; }
.panel .p-b { max-height:min(60vh,420px); overflow-y:auto; }
.nt { display:flex; gap:9px; padding:12px 14px; border-bottom:1px solid var(--line);
      cursor:pointer; }
.nt:last-child { border-bottom:0; }
.nt:hover { background:#faf8f3; }
.nt .dot { width:7px; height:7px; border-radius:99px; margin-top:5px; flex:0 0 auto;
           background:var(--yellow); }
.nt.error .dot { background:#C1392B; } .nt.warn .dot { background:#d68000; }
.nt.ok .dot { background:#1F8A45; }
.nt.read .dot { background:#d8d3c6; }
.nt .tx { min-width:0; }
.nt .t { font-size:12.5px; font-weight:700; line-height:1.45; }
.nt.read .t { font-weight:500; color:var(--ink-soft); }
.nt .b { font-size:11.5px; color:var(--sh-muted); line-height:1.6; margin-top:3px;
         word-break:break-word; }
.nt .w { font-size:10.5px; color:var(--sh-muted); margin-top:5px; }
.nt-empty { padding:22px 14px; text-align:center; font-size:12px; color:var(--sh-muted); }
.toasts { position:fixed; right:18px; top:74px; z-index:80;
          display:flex; flex-direction:column; gap:10px; width:330px;
          max-width:calc(100vw - 28px); }
.toast { background:var(--paper); border:1px solid var(--line); border-left:4px solid var(--yellow);
  border-radius:11px; box-shadow:0 10px 30px rgba(26,26,26,.2); padding:12px 13px;
  animation:toast-in .28s ease-out; }
.toast.error { border-left-color:#C1392B; } .toast.warn { border-left-color:#d68000; }
.toast.ok { border-left-color:#1F8A45; }
@keyframes toast-in { from { opacity:0; transform:translateY(-8px); } to { opacity:1; transform:none; } }
.toast .t { font-size:12.5px; font-weight:700; line-height:1.45; padding-right:18px; }
.toast .b { font-size:11.5px; color:var(--ink-soft); line-height:1.6; margin-top:4px; }
.toast .r { display:flex; gap:8px; align-items:center; margin-top:10px; }
.toast .r button, .toast .r a { border:1px solid var(--line); background:var(--paper);
  border-radius:7px; font-family:inherit; font-size:11.5px; font-weight:650; padding:5px 11px;
  cursor:pointer; color:var(--ink-soft); text-decoration:none; }
.toast .r button.on { background:var(--ink); border-color:var(--ink); color:var(--yellow); }
.toast-close { float:right; border:0; background:none; cursor:pointer; color:var(--sh-muted);
  font-size:15px; line-height:1; padding:0 0 0 6px; font-family:inherit; }

@media (max-width:820px) {
  .shell { grid-template-columns:1fr; }
  .side { position:static; height:auto; padding:16px 14px; }
  .brand { padding-bottom:14px; margin-bottom:12px; }
  .menu { display:flex; flex-wrap:wrap; gap:5px; }
  .menu a { margin:0; padding:7px 12px; border:1px solid #333; border-radius:999px; }
  .menu a.sub { margin-left:0; }
  .topbar { padding:0 14px; }
  .plat { gap:18px; }
  .ext { padding:6px 11px; font-size:12px; }
  .main { padding:18px 14px 56px; }
  .toasts { right:10px; left:10px; width:auto; top:66px; }
  /* 폰에서 넓은 표는 표 안에서만 옆으로 밀리게 한다 (페이지 전체가 밀리지 않도록) */
  table { display:block; width:100%; overflow-x:auto; -webkit-overflow-scrolling:touch; }
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


# 상단 오른쪽 외부 링크 (SNS 발행 관리 페이지)
EXT_NAME = "발행 관리"
EXT_LINK = "https://znsl132-lang.github.io/wevape-web/"

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
  var KEY  = 'wevape-sns-read';   // 읽은 알림
  var SKEY = 'wevape-sns-shown';  // 팝업으로 이미 띄운 알림 (기기별)
  var POPUP_DAYS = 7;             // 이보다 오래된 알림은 팝업으로 띄우지 않는다
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
  function shownIds() {
    try { return JSON.parse(localStorage.getItem(SKEY) || '[]') || []; }
    catch (e) { return []; }
  }
  function markShown(id) {
    var a = shownIds();
    if (a.indexOf(id) === -1) {
      a.push(id);
      try { localStorage.setItem(SKEY, JSON.stringify(a.slice(-80))); } catch (e) {}
    }
  }
  // '2026-08-17 07:50' 형태를 날짜로 읽는다. 못 읽으면 오래된 것으로 보지 않는다.
  function tooOld(n) {
    var t = Date.parse(String(n.at || '').replace(' ', 'T'));
    if (isNaN(t)) return false;
    return (Date.now() - t) > POPUP_DAYS * 86400000;
  }
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
        if (n && n.link) {
          // 폰에서 window.open 이 막히는 경우가 있어 링크를 직접 만들어 연다
          var a = document.createElement('a');
          a.href = n.link; a.target = '_blank'; a.rel = 'noopener';
          document.body.appendChild(a); a.click(); a.remove();
        }
      };
    });
  }

  // 버튼을 누르지 않아도 안 읽은 알림은 팝업으로 바로 뜬다 (최대 3개)
  function popup() {
    if (!stack) return;
    items.filter(function (n) {
      // 안 읽었고, 이 기기에서 아직 안 띄웠고, 7일이 지나지 않은 것만 팝업으로 띄운다.
      return !isRead(n.id) && shownIds().indexOf(n.id) === -1 && !tooOld(n);
    }).slice(0, 3).forEach(function (n) {
      markShown(n.id);
      var d = document.createElement('div');
      d.className = 'toast ' + n.level;
      d.innerHTML = '<button class="toast-close" aria-label="닫기">&times;</button>' +
        '<div class="t">' + esc(n.title) + '</div>' +
        (n.body ? '<div class="b">' + esc(n.body) + '</div>' : '') +
        '<div class="r"><button class="ok on">읽음</button>' +
        (n.link ? '<a href="' + esc(n.link) + '" target="_blank" rel="noopener">열어보기</a>' : '') + '</div>';
      // X 는 이번만 숨기기 — 안 읽은 상태는 그대로 남는다
      d.querySelector('.toast-close').onclick = function () { d.remove(); };
      d.querySelector('.ok').onclick = function () { markRead(n.id); d.remove(); };
      // '열어보기'로 넘어갈 때도 읽음으로 처리한다 (이게 빠져 있어서 계속 안 읽음이었다)
      var go = d.querySelector('.r a');
      if (go) go.onclick = function () { markRead(n.id); d.remove(); };
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
             updated="", body_end="", generated_iso="", lead="", tabs=""):
    """platform: 'ig' | 'th'   page: 'daily' | 'analysis'"""
    plat_links = "".join(
        f'<a class="{"on" if k == platform else ""}" href="{href}">{name}</a>'
        for k, name, href in PLATFORMS)
    parts = []
    for item in SUBPAGES[platform]:
        k, name, href = item[0], item[1], item[2]
        kids = item[3] if len(item) > 3 else []
        parts.append(f'<a class="{"on" if k == page else ""}" href="{href}">{name}</a>')
        # 하위 메뉴는 부모를 보고 있거나 하위 자신을 보고 있을 때만 펼친다
        if kids and (k == page or any(c[0] == page for c in kids)):
            for ck, cname, chref in kids:
                parts.append(f'<a class="sub {"on" if ck == page else ""}" '
                             f'href="{chref}">{cname}</a>')
    side_links = "".join(parts)
    plat_name = next(n for k, n, _ in PLATFORMS if k == platform)

    return f"""<!doctype html>
<html lang="ko"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<title>{_esc(page_title)} · {_esc(plat_name)} · WEVAPE SNS</title>
<style>{SHELL_CSS}{page_css}</style>
</head><body>
<div class="toasts" id="toasts"></div>
<div class="shell">
  <aside class="side">
    <div class="brand"><b>WEVAPE SNS</b><span>운영 현황</span></div>
    <nav class="menu">{side_links}</nav>
  </aside>
  <div class="col">
    <header class="topbar">
      <nav class="plat">{plat_links}</nav>
      <div class="top-right">
        <a class="ext" href="{EXT_LINK}" target="_blank" rel="noopener">{EXT_NAME}<span>↗</span></a>
{NOTICE_HTML}
      </div>
    </header>
    <main class="main">
      <div class="page-h"><h1>{_esc(page_title)}</h1>
        <span class="updated">{_esc(updated)}</span></div>
      <div class="stale" id="stale" data-generated="{_esc(generated_iso)}"></div>
      <p class="scope">{lead}</p>
      <div class="tabslot">{tabs}</div>
{inner}
    </main>
  </div>
</div>
{body_end}
{STALE_JS}
{NOTICE_JS}
</body></html>"""
