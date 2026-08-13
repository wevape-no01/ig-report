"""
네 페이지가 공유하는 껍데기(사이트 이름 / 상단 플랫폼 탭 / 왼쪽 세부 메뉴).

구조:
  WEVAPE SNS 운영 현황
  ├ 인스타그램 ─┬ 일일 리포트   (index.html)
  │             └ 콘텐츠 분석   (analysis.html)
  └ 스레드     ─┬ 일일 리포트   (threads.html)
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
           ("analysis", "콘텐츠 분석", "./analysis.html")],
    "th": [("daily", "일일 리포트", "./threads.html"),
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
@media (max-width:820px) {
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
  <div class="brand">{_esc(SITE)}</div>
  <nav class="plat">{plat_links}</nav>
</div></header>
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
</body></html>"""
