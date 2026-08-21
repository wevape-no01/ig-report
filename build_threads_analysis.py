"""
threads_cache.json + threads_report.json 을 읽어 스레드 콘텐츠 분석(threads-analysis.html)을 만든다.

인스타와 방향이 다르다:
  - 스레드에는 "도달"이 없다 → 조회수(views)가 유일한 노출 지표다
  - 그래서 "무엇이 노출되는가(조회수)"를 중심으로 짠다
  - 반응(좋아요·답글·리포스트·인용)이 하나라도 있으면 반응 랭킹 섹션이 자동으로 켜진다

실행: python3 build_threads_analysis.py
section h2::before, h3::before { content:"● "; color:#FFC800; font-size:11px; vertical-align:2px; }

"""

import json
import os
import re
from datetime import datetime, timedelta, timezone

import layout

DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(DIR, "threads-analysis.html")

ANALYSIS_MONTHS = 24
MIN_POSTS = 10          # 이보다 적으면 비율 분석을 하지 않는다
MIN_N = 5               # 표본이 이보다 적으면 경고
RANK_LIMIT = 5
TOP_VISIBLE = 5

LIMITS_HTML = """
<details class="tg"><summary>이 분석의 한계</summary>
  <div class="tg-body limits">
    스레드에는 "도달"이 없습니다. 조회수는 화면에 표시된 <b>횟수</b>라 같은 사람이 여러 번 보면 그만큼 올라갑니다.<br>
    답글의 답글은 집계되지 않습니다. 리포스트로 올라간 글은 인사이트가 비어 있어 분석에서 빠집니다.<br>
    어떤 경로로 들어왔는지는 API가 주지 않습니다.
  </div>
</details>"""
MINI_RANK = 5

TYPE_KO = {"TEXT_POST": "텍스트만", "IMAGE": "이미지", "VIDEO": "동영상",
           "CAROUSEL_ALBUM": "여러 장", "AUDIO": "오디오",
           "REPOST_FACADE": "리포스트"}
DOW = ["월", "화", "수", "목", "금", "토", "일"]
HASHTAG_RX = re.compile(r"#([^\s#​]+)")


def load(name, default):
    p = os.path.join(DIR, name)
    if not os.path.exists(p):
        return default
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def guess_lang(text):
    if re.search(r"[가-힣]", text):
        return "한국어"
    if re.search(r"[ぁ-んァ-ヶ]", text):
        return "일본어"
    if re.search(r"[一-鿿]", text):
        return "중국어"
    if re.search(r"[A-Za-z]", text):
        return "영문"
    return "기타"


def avg(rows, f):
    rows = [r for r in rows if f(r) is not None]
    return sum(f(r) for r in rows) / len(rows) if rows else 0


# ------------------------------------------------------------ 데이터 준비

def prep():
    cache = load("threads_cache.json", {})
    cutoff = (datetime.now(timezone.utc) + timedelta(hours=9)
              - timedelta(days=int(ANALYSIS_MONTHS * 30.44)))
    posts, excluded_old = [], 0
    for p in cache.values():
        ins = p.get("insights") or {}
        if ins.get("views") is None:
            continue
        try:
            dt = datetime.strptime(p.get("timestamp", ""), "%Y-%m-%dT%H:%M:%S%z") + timedelta(hours=9)
        except ValueError:
            continue
        if dt < cutoff:
            excluded_old += 1
            continue
        text = p.get("text") or ""
        tags = list(dict.fromkeys(t.lower() for t in HASHTAG_RX.findall(text)))
        body = HASHTAG_RX.sub("", text).strip()
        react = sum((ins.get(k) or 0) for k in
                    ("likes", "replies", "reposts", "quotes", "shares"))
        views = ins.get("views") or 0
        posts.append({
            "dt": dt, "date": dt.strftime("%Y-%m-%d"), "md": dt.strftime("%m-%d"),
            "dow": DOW[dt.weekday()], "hour": dt.hour,
            "type": p.get("media_type") or "TEXT_POST",
            "permalink": p.get("permalink") or "",
            "text": text, "body": body, "tags": tags,
            "len": len(body), "tag_n": len(tags), "lang": guess_lang(body),
            "views": views,
            "likes": ins.get("likes") or 0, "replies": ins.get("replies") or 0,
            "reposts": ins.get("reposts") or 0, "quotes": ins.get("quotes") or 0,
            "shares": ins.get("shares") or 0,
            "react": react,
            "rr": react / views * 100 if views else 0,
        })
    posts.sort(key=lambda x: x["dt"], reverse=True)
    return posts, excluded_old


def group_views(posts, keyfn):
    """키별 평균 조회수. 반환은 조회수 내림차순."""
    out = {}
    for p in posts:
        keys = keyfn(p)
        for k in (keys if isinstance(keys, list) else [keys]):
            out.setdefault(k, []).append(p)
    rows = [{"key": k, "n": len(v),
             "views": avg(v, lambda x: x["views"]),
             "react": avg(v, lambda x: x["react"])} for k, v in out.items()]
    return sorted(rows, key=lambda r: -r["views"])


# ------------------------------------------------------------ 렌더 도구

def bars(rows, label, sub, max_rows=None, narrow=False, emphasize_first=False):
    """가로 막대 — 값은 평균 조회수(절대값)."""
    rows = rows[:max_rows] if max_rows else rows
    if not rows:
        return '<p class="empty">데이터가 없습니다</p>'
    if narrow:
        BH, GAP, L, R, W = 26, 10, 84, 116, 400
    else:
        BH, GAP, L, R, W = 28, 11, 150, 200, 860
    bw = W - L - R
    mx = max(r["views"] for r in rows) or 1
    best_i = max(range(len(rows)), key=lambda i: rows[i]["views"]) if rows else -1
    out = []
    for i, r in enumerate(rows):
        y = i * (BH + GAP) + 6
        w = max(r["views"] / mx * bw, 2)
        # 가장 큰 막대 하나만 노랑으로 강조하고 나머지는 연한 베이지로 둔다.
        cls = "bar hl" if i == best_i else "bar"
        out.append(f'<text class="cat" x="0" y="{y+BH/2+4:.0f}">{esc(label(r))}</text>')
        out.append(f'<rect class="{cls}" x="{L}" y="{y}" width="{w:.1f}" height="{BH}" rx="4"/>')
        out.append(f'<text class="val" x="{L+w+8:.1f}" y="{y+BH/2+4:.0f}">{r["views"]:.0f}회'
                   f'<tspan class="dim2"> {esc(sub(r))}</tspan></text>')
    return f'<svg viewBox="0 0 {W} {len(rows)*(BH+GAP)+8}">' + "".join(out) + "</svg>"


def toggle(title, inner, open_=False):
    return (f'<details class="tg"{" open" if open_ else ""}><summary>{esc(title)}</summary>'
            f'<div class="tg-body">{inner}</div></details>')


def warn(n, what):
    return (f'<div class="warn">⚠️ {what} 표본이 {n}개뿐인 항목이 있습니다. '
            f'우연일 가능성이 높아 판단 근거로 쓰기엔 부족합니다 (권장 {MIN_N}개 이상).</div>')


def short(p, w=40):
    return p["body"][:w] or p["text"][:w] or "(내용 없음)"


def linked(p, w=40):
    t = esc(short(p, w))
    return (f'<a href="{esc(p["permalink"])}" target="_blank" rel="noopener">{t}</a>'
            if p["permalink"] else t)


def label_of(p):
    return f'{p["md"]} {TYPE_KO.get(p["type"], p["type"])}'


# ------------------------------------------------------------ 분석 문장

def build_insights(posts, ranked, followers, has_react, types, tags, excluded_old):
    ins, chk = [], []
    n = len(posts)
    a_views = avg(posts, lambda p: p["views"])
    tot_views = sum(p["views"] for p in posts)
    tot_react = sum(p["react"] for p in posts)
    rr = tot_react / tot_views * 100 if tot_views else 0

    top = ranked[0] if ranked else None
    if top:
        ins.append(
            f'<b>가장 많이 노출된 글은 {label_of(top)}({top["views"]:,}회)입니다.</b> '
            f'글당 평균 {a_views:.0f}회의 {top["views"]/a_views:.1f}배이고, 반응이 {top["react"]}건 붙었습니다. '
            f'{"해시태그 " + str(top["tag_n"]) + "개, " if top["tag_n"] else "해시태그 없이 "}'
            f'본문 {top["len"]}자였습니다.')

    if len(types) >= 2 and types[1]["views"]:
        t0, t1 = types[0], types[1]
        ins.append(
            f'<b>{TYPE_KO.get(t0["key"], t0["key"])} 글이 가장 많이 노출됩니다.</b> '
            f'{TYPE_KO.get(t1["key"], t1["key"])}보다 평균 조회수가 {t0["views"]/t1["views"]:.1f}배 높습니다'
            f'(각각 {t0["n"]}개 / {t1["n"]}개). 스레드는 텍스트 중심이라 '
            f'인스타용 이미지 글을 그대로 넘기면 같은 성과가 나오지 않습니다.')

    # 스레드 전용 글(해시태그 없음) vs 인스타에서 넘어온 글(해시태그 많음) 비교
    native = [p for p in posts if p["tag_n"] == 0]
    cross = [p for p in posts if p["tag_n"] >= 3]
    if len(native) >= MIN_N and len(cross) >= MIN_N:
        nv, cv = avg(native, lambda p: p["views"]), avg(cross, lambda p: p["views"])
        nr = sum(p["react"] for p in native) / max(sum(p["views"] for p in native), 1) * 100
        cr = sum(p["react"] for p in cross) / max(sum(p["views"] for p in cross), 1) * 100
        if cv and nv / cv >= 1.3:
            ins.append(
                f'<b>해시태그 없이 쓴 글({len(native)}개)이 해시태그를 3개 이상 붙인 글({len(cross)}개)보다 '
                f'평균 조회수가 {nv/cv:.1f}배 높습니다</b>({nv:.0f}회 vs {cv:.0f}회, 반응률 {nr:.1f}% vs {cr:.1f}%). '
                f'해시태그가 많은 글은 대개 인스타에서 그대로 넘어온 글입니다 — '
                f'스레드에서는 스레드용으로 새로 쓴 글이 훨씬 잘 먹힙니다.')

    # --- 확인 필요
    if not has_react:
        chk.append(
            f'분석 대상 {n}개 글에서 좋아요·답글·리포스트·인용·공유가 한 건도 없습니다. '
            f'대화형 짧은 글로 바꿔 며칠만 직접 올려보고 숫자가 달라지는지 확인해보세요.')
    else:
        if followers and a_views / followers * 100 < 15:
            chk.append(
                f'반응률은 {rr:.1f}%로 높은 편인데, 글 하나가 팔로워 {followers:,}명 중 평균 '
                f'{a_views:.0f}명분(팔로워의 {a_views/followers*100:.1f}%)에게만 노출됩니다. '
                f'즉 본 사람은 잘 반응하는데 애초에 보여지는 양이 적습니다 — 글 자체보다 게시 빈도와 '
                f'초반 답글 유도가 병목일 가능성이 큽니다.')

    long_posts = [p for p in posts if p["len"] > 300]
    if len(long_posts) >= MIN_N and len(long_posts) / n > 0.25:
        lv = avg(long_posts, lambda p: p["views"])
        chk.append(
            f'본문 300자 초과 글이 {len(long_posts)}개({len(long_posts)/n*100:.0f}%)이고 '
            f'평균 조회수는 {lv:.0f}회로 전체 평균({a_views:.0f}회)보다 '
            f'{"낮습니다" if lv < a_views else "높습니다"}. '
            f'스레드는 500자 제한에 짧은 글이 도는 곳이라 긴 글은 접힌 채 지나가기 쉽습니다.')

    return ins[:3], chk[:2]


# ------------------------------------------------------------ CSS

CSS = """
:root { --text:#1A1A1A; --text2:#54524B; --muted:#7a756a; --grid:#E7E2D6;
  --border:#E7E2D6; --accent:#1A1A1A; --accent-soft:#FFF3C4; --gray:#cfc9ba;
  --good:#1F8A45; --warnc:#8a5a00; --bad:#C1392B; }
/* .scope 여백은 layout.py 에서 한 곳으로 정한다 (페이지마다 위치가 어긋나던 원인) */
.scope { color:var(--muted); }
section.acct { background:#fff; border:1px solid var(--border); border-radius:12px;
               padding:20px 22px; margin-bottom:26px; }
.acct-h { display:flex; align-items:baseline; gap:12px; flex-wrap:wrap; margin-bottom:16px;
  padding-bottom:12px; border-bottom:1px solid var(--grid); }
.acct-h h2 { font-size:20px; margin:0; }
h3 { font-size:18px; margin:30px 0 3px; }
.sub { font-size:12px; color:var(--muted); margin:0 0 14px; }
.dim { color:var(--muted); } .nw { white-space:nowrap; }
.verdict { display:flex; align-items:baseline; gap:13px; flex-wrap:wrap; margin-bottom:4px; }
.hero { font-size:40px; font-weight:650; line-height:1; }
.hu { font-size:16px; color:var(--muted); font-weight:400; }
.badge { font-size:12px; font-weight:600; padding:4px 10px; border-radius:999px; }
.badge.good { background:#e6f4e6; color:var(--good); }
.badge.warn { background:#fdf1dc; color:var(--warnc); }
.kpis { display:grid; grid-template-columns:repeat(auto-fit,minmax(158px,1fr)); gap:11px; }
.kpi { border:1px solid var(--border); border-radius:10px; padding:13px 14px; }
.kpi .lbl { font-size:12px; color:var(--text2); margin-bottom:7px; }
.kpi .v { font-size:24px; font-weight:620; line-height:1; }
.kpi .cmp { font-size:11px; margin-top:6px; color:var(--muted); }
svg { display:block; width:100%; height:auto; overflow:visible; }
.bar { fill:#D9D2C2; } .bar.hl { fill:#FFDE7A; } .bar.muted { fill:#D9D2C2; }
.cat { fill:var(--text2); font-size:12px; }
.val { fill:var(--text); font-size:12px; font-weight:600; }
.dim2 { fill:var(--muted); font-weight:400; font-size:11px; }
table { width:100%; border-collapse:collapse; font-size:12.5px; }
th, td { text-align:left; padding:8px 7px; border-bottom:1px solid var(--grid); }
th { font-size:10.5px; color:var(--muted); text-transform:uppercase; letter-spacing:.03em; font-weight:500; }
td.num { text-align:right; font-variant-numeric:tabular-nums; }
td.strong { font-weight:650; color:var(--accent); }
td.cap { color:var(--text2); max-width:300px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
td.cap a { color:var(--text2); text-decoration:none; }
td.cap a:hover { color:var(--accent); text-decoration:underline; }
.chip { display:inline-block; font-size:10.5px; padding:2px 7px; border-radius:5px;
  background:var(--accent-soft); color:#164a86; white-space:nowrap; }
.warn { background:#fdf6e6; border:1px solid #f0dca0; color:#6b5300;
  border-radius:8px; padding:9px 12px; font-size:12px; margin-bottom:12px; }
.empty { color:var(--muted); font-size:13px; }
details.tg { border:1px solid var(--border); border-radius:9px; margin-bottom:9px; }
details.tg summary { cursor:pointer; padding:11px 14px; font-size:13px; font-weight:600;
  color:var(--text2); list-style:none; display:flex; align-items:center; gap:7px; }
details.tg summary::-webkit-details-marker { display:none; }
details.tg summary::before { content:"\\25b8"; color:var(--accent); font-size:11px; }
details.tg[open] summary::before { content:"\\25be"; }
details.tg[open] summary { border-bottom:1px solid var(--grid); }
.tg-body { padding:14px; }
.two { display:grid; grid-template-columns:1fr 1fr; gap:22px; }
@media (max-width:700px) { .two { grid-template-columns:1fr; } }
.mini-t { font-size:12px; color:var(--text2); font-weight:600; margin-bottom:9px; }
.demos { display:grid; grid-template-columns:repeat(auto-fit,minmax(215px,1fr)); gap:16px; }
.dm-box { border:1px solid var(--border); border-radius:10px; padding:13px 14px; }
.dm-t { font-size:12px; font-weight:600; color:var(--text2); margin-bottom:10px; }
.dm { display:grid; grid-template-columns:74px 1fr 44px; align-items:center; gap:8px;
      margin-bottom:6px; font-size:11.5px; }
.dm-k { color:var(--text2); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.dm-bar { background:var(--grid); border-radius:3px; height:8px; overflow:hidden; }
/* 팔로워 구성은 참고용이라 연하게. 가장 큰 항목만 연노랑으로 표시한다. */
.dm-bar i { display:block; height:100%; background:#D9D2C2; border-radius:3px; }
.dm-bar i.hl { background:#FFDE7A; }
.dm-v { text-align:right; font-variant-numeric:tabular-nums; }
.limits { font-size:12.5px; color:var(--text2); line-height:1.75; }
.ins-box, .chk-box { border-radius:10px; padding:15px 17px; margin-bottom:11px; }
.ins-box { background:#FFFBEF; border:1px solid #F2E4B4; border-left:5px solid #FFC800; }
.chk-box { background:#FFF6F4; border:1px solid #F0D6CF; border-left:5px solid #C1392B; }
.ins-t, .chk-t { font-size:14px; font-weight:700; margin-bottom:10px; }
.ins-t { color:var(--accent); } .chk-t { color:#A33224; }
.ins-box p, .chk-box p { font-size:14px; line-height:1.75; margin:0 0 10px; color:#2B2924; }
.ins-box p:last-child, .chk-box p:last-child { margin-bottom:0; }
/* 핵심 문장은 노랑 형광펜으로 — 검은 글씨 사이에서 바로 눈에 띄게 */
.ins-box b { font-weight:700; color:var(--accent);
  background:linear-gradient(transparent 58%, #FFE788 58%); padding:0 2px; }
.chk-box b { font-weight:700; color:#A33224; }
.champ { border:1px solid var(--border); border-left:3px solid var(--accent);
  border-radius:10px; padding:14px 16px; margin-bottom:14px; background:#fbfcfe; }
.champ-h { display:flex; align-items:baseline; gap:10px; flex-wrap:wrap; font-size:14px; }
.champ-v { color:var(--accent); font-weight:700; font-size:15px; }
.champ-cap { font-size:13px; color:var(--text2); margin:10px 0 8px; line-height:1.6; }
.champ-cap a { color:var(--text2); text-decoration:none; }
.champ-k { font-size:11.5px; color:var(--muted); font-variant-numeric:tabular-nums;
  line-height:1.6; padding-bottom:10px; border-bottom:1px solid var(--grid); }
.champ-note { font-size:13px; line-height:1.7; margin:10px 0 0; }
"""

SETUP = """<div class="warn" style="font-size:13.5px;padding:16px 18px">
<b>아직 스레드 데이터가 없습니다.</b> 스레드 연결이 끝나고 리포트가 한 번 갱신되면
이 페이지가 자동으로 채워집니다.</div>"""


def build():
    report = load("threads_report.json", None)
    if not report or not report.get("profile"):
        with open(OUT, "w", encoding="utf-8") as f:
            f.write(layout.document("th", "analysis", "콘텐츠 분석", SETUP, CSS))
        print(f"저장됨: {OUT} (설정 대기 중)")
        return

    posts, excluded_old = prep()
    prof = report["profile"]
    uname = prof.get("username", "?")
    followers = (report.get("account_insights") or {}).get("followers_count") or 0
    demo = report.get("demographics", {})

    if len(posts) < MIN_POSTS:
        inner = (f'<section class="acct"><div class="acct-h"><h2>@{esc(uname)}</h2>'
                 f'<span class="dim">분석 가능 글 {len(posts)}개</span></div>'
                 f'<div class="warn">글이 {MIN_POSTS}개 미만이라 비율 분석을 하지 않았습니다. '
                 f'글이 쌓이면 자동으로 전체 분석이 표시됩니다.</div></section>')
        with open(OUT, "w", encoding="utf-8") as f:
            f.write(layout.document("th", "analysis", "콘텐츠 분석", inner, CSS,
                                    updated=layout.fmt_updated(report.get("generated_at", ""))))
        print(f"저장됨: {OUT} (글 {len(posts)}개 · 요약만)")
        return

    n = len(posts)
    a_views = avg(posts, lambda p: p["views"])
    tot_views = sum(p["views"] for p in posts)
    tot_react = sum(p["react"] for p in posts)
    # 반응 종류별 누적 — 일일 리포트에서 옮겨 온 값 (세부 분석 아래쪽에 둔다)
    react_kinds = [("좋아요", "likes"), ("답글", "replies"),
                   ("리포스트", "reposts"), ("인용", "quotes"), ("공유", "shares")]
    react_tot = {k: sum(p.get(k) or 0 for p in posts) for _, k in react_kinds}
    react_tot_html = "".join(
        f'<div class="kpi"><div class="lbl">{ko}</div>'
        f'<div class="v">{react_tot[k]:,}</div></div>' for ko, k in react_kinds)
    has_react = tot_react > 0
    rr = tot_react / tot_views * 100 if tot_views else 0
    exposure = a_views / followers * 100 if followers else 0

    ranked = sorted(posts, key=lambda p: -p["views"])
    types = group_views(posts, lambda p: p["type"])
    tags = [t for t in group_views(posts, lambda p: p["tags"] or ["(태그 없음)"])
            if t["n"] >= MIN_N and t["key"] != "(태그 없음)"]

    ins_list, chk_list = build_insights(posts, ranked, followers, has_react,
                                        types, tags, excluded_old)
    ins_html = ('<div class="ins-box"><div class="ins-t">💡 오늘의 인사이트</div>'
                + "".join(f"<p>{t}</p>" for t in ins_list) + '</div>') if ins_list else ""
    chk_html = ('<div class="chk-box"><div class="chk-t">⚠️ 확인 필요</div>'
                + "".join(f"<p>{t}</p>" for t in chk_list) + '</div>') if chk_list else ""

    # ---- 1위 카드
    champ = ranked[0]
    rr_all = rr
    parts = [f'글당 평균 조회수 {a_views:.0f}회의 {champ["views"]/a_views:.1f}배입니다.']
    same = next((t for t in types if t["key"] == champ["type"]), None)
    if same and same["n"] >= 2:
        parts.append(f'{TYPE_KO.get(champ["type"], champ["type"])} 평균({same["views"]:.0f}회)보다도 높습니다.')
    if champ["react"] == 0:
        parts.append('반응은 0건이었습니다. 노출은 됐지만 아무도 움직이지 않았다는 뜻이라, '
                     '소재는 통했지만 행동을 부르는 문장이 없었을 가능성이 큽니다.')
    else:
        cr = champ["react"] / champ["views"] * 100 if champ["views"] else 0
        parts.append(f'반응은 {champ["react"]}건(반응률 {cr:.1f}%)으로 '
                     f'전체 평균({rr_all:.1f}%)보다 '
                     f'{"높습니다 — 노출과 반응이 같이 터진 글입니다." if cr >= rr_all else "낮습니다 — 많이 보이긴 했지만 움직임은 평소만 못했습니다."}')
    champ_html = f'''
  <div class="champ">
    <div class="champ-h"><span class="badge good">조회 1위</span>
      <b>{TYPE_KO.get(champ["type"], champ["type"])}</b>
      <span class="champ-v">조회 {champ["views"]:,}회</span>
      <span class="dim">{champ["date"]} {champ["dow"]}요일 {champ["hour"]}시</span></div>
    <p class="champ-cap">{linked(champ, 120)}</p>
    <div class="champ-k">조회 {champ["views"]:,} · 좋아요 {champ["likes"]} · 답글 {champ["replies"]} ·
      리포스트 {champ["reposts"]} · 인용 {champ["quotes"]} · 공유 {champ["shares"]} ·
      해시태그 {champ["tag_n"]}개 · 본문 {champ["len"]}자</div>
    <p class="champ-note">{" ".join(parts)}</p>
  </div>'''

    # ---- 전체 랭킹
    def rank_row(i, p):
        return (f'<tr><td class="num">{i+1}</td>'
                f'<td class="nw">{p["md"]}<span class="dim"> {p["dow"]} {p["hour"]}시</span></td>'
                f'<td><span class="chip">{TYPE_KO.get(p["type"], p["type"])}</span></td>'
                f'<td class="cap">{linked(p)}</td>'
                f'<td class="num strong">{p["views"]:,}</td>'
                f'<td class="num">{p["react"] or "–"}</td>'
                f'<td class="num">{p["len"]}자</td></tr>')

    head = ('<thead><tr><th>#</th><th>게시일</th><th>유형</th><th>내용</th>'
            '<th class="num">조회</th><th class="num">반응</th><th class="num">길이</th></tr></thead>')
    top10 = ranked[:RANK_LIMIT]
    rank_html = f'<table>{head}<tbody>' + \
        "".join(rank_row(i, p) for i, p in enumerate(top10[:TOP_VISIBLE])) + '</tbody></table>'
    rest = "".join(rank_row(i + TOP_VISIBLE, p) for i, p in enumerate(top10[TOP_VISIBLE:]))
    if rest:
        rank_html += toggle(f"{TOP_VISIBLE+1}위 ~ {len(top10)}위 보기",
                            f'<table>{head}<tbody>{rest}</tbody></table>')

    # ---- 반응 랭킹 (반응이 생기면 자동으로 켜진다)
    react_html = ""
    if has_react:
        def mini(key, unit):
            rows = sorted([p for p in posts if p[key]], key=lambda p: -p[key])[:MINI_RANK]
            if not rows:
                return '<p class="empty">아직 기록이 없습니다</p>'
            h = ('<thead><tr><th>#</th><th>게시일</th><th>내용</th>'
                 f'<th class="num">{esc(unit)}</th><th class="num">조회</th></tr></thead>')
            b = "".join(
                f'<tr><td class="num">{i+1}</td><td class="nw">{p["md"]}</td>'
                f'<td class="cap">{linked(p)}</td>'
                f'<td class="num strong">{p[key]:,}</td>'
                f'<td class="num">{p["views"]:,}</td></tr>' for i, p in enumerate(rows))
            return f'<table>{h}<tbody>{b}</tbody></table>'
        react_html = ('<h3>반응 랭킹</h3><p class="sub">반응이 생긴 뒤부터 표시됩니다</p>'
                      + toggle(f"좋아요 TOP {MINI_RANK}", mini("likes", "좋아요"))
                      + toggle(f"답글 TOP {MINI_RANK}", mini("replies", "답글"))
                      + toggle(f"리포스트 TOP {MINI_RANK}", mini("reposts", "리포스트")))

    # ---- 유형별 / 해시태그별 / 길이별
    type_html = bars(types, lambda r: TYPE_KO.get(r["key"], r["key"]),
                     lambda r: f'· {r["n"]}개', emphasize_first=True)
    tag_html = bars(tags, lambda r: "#" + r["key"], lambda r: f'· {r["n"]}개', max_rows=15)

    def len_bucket(p):
        k = p["len"]
        return "~50자" if k <= 50 else ("51–150자" if k <= 150 else
                                        ("151–300자" if k <= 300 else "300자 초과"))
    len_html = bars(group_views(posts, len_bucket), lambda r: r["key"],
                    lambda r: f'· {r["n"]}개', narrow=True)

    def tag_bucket(p):
        k = p["tag_n"]
        return "0개" if k == 0 else ("1–3개" if k <= 3 else ("4–7개" if k <= 7 else "8개 이상"))
    tagn_html = bars(group_views(posts, tag_bucket), lambda r: r["key"],
                     lambda r: f'· {r["n"]}개', narrow=True)

    # ---- 참고 지표
    lang = group_views(posts, lambda p: p["lang"])
    hour = group_views(posts, lambda p: p["hour"])
    dow = group_views(posts, lambda p: p["dow"])
    lang_inner = (warn(min(l["n"] for l in lang), "언어별") if lang and min(l["n"] for l in lang) < MIN_N else "") \
        + bars(lang, lambda r: r["key"], lambda r: f'· {r["n"]}개')
    hour_inner = (warn(min(h["n"] for h in hour), "시각별") if hour and min(h["n"] for h in hour) < MIN_N else "") \
        + bars(hour, lambda r: f'{r["key"]}시', lambda r: f'· {r["n"]}개', max_rows=12)
    dow_inner = bars(dow, lambda r: f'{r["key"]}요일', lambda r: f'· {r["n"]}개')

    # ---- 팔로워 구성
    def demo_block(title, d, top=6):
        if not d:
            return ""
        items = sorted(d.items(), key=lambda kv: -(kv[1] or 0))[:top]
        mx = max((v or 0) for _, v in items) or 1
        rows = "".join(
            f'<div class="dm"><span class="dm-k">{esc(k)}</span>'
            f'<span class="dm-bar"><i class="{"hl" if i == 0 else ""}" '
            f'style="width:{(v or 0)/mx*100:.0f}%"></i></span>'
            f'<span class="dm-v">{v}</span></div>' for i, (k, v) in enumerate(items))
        return f'<div class="dm-box"><div class="dm-t">{esc(title)}</div>{rows}</div>'
    demo_html = ("".join([demo_block("연령", demo.get("age")), demo_block("성별", demo.get("gender")),
                          demo_block("도시", demo.get("city")), demo_block("국가", demo.get("country"))])
                 or '<p class="empty">인구통계 데이터가 아직 없습니다</p>')

    period = f'{posts[-1]["date"]} ~ {posts[0]["date"]}'
    ex_note = (f'<div class="warn">{ANALYSIS_MONTHS}개월 이전 글 {excluded_old}개는 제외했습니다.</div>'
               if excluded_old else "")

    lead_ig = f'전체 글 {report.get("posts_total", 0)}개 중 인사이트 있는 {n}개 분석'
    inner = f"""<section class="acct">
  <div class="acct-h">
    <h2>@{esc(uname)}</h2>
    <span class="dim">{esc(period)} · 분석 글 {n}개 · 팔로워 {followers:,}명</span>
  </div>
  {ex_note}

  <div class="verdict">
    <div class="hero">{rr:.2f}<span class="hu">%</span></div>
    <span class="badge {'good' if has_react else 'warn'}">반응 {tot_react}건</span>
    <span class="badge {'good' if exposure >= 10 else 'warn'}">팔로워의 {exposure:.1f}%에 노출</span>
  </div>
  <p class="sub">반응률 · 조회 100회당 반응 {rr:.1f}건. 스레드는 조회수보다 반응이 노출을 만듭니다.</p>

  <h3>핵심 지표</h3>
  <p class="sub">기간 내 글 {n}개 기준</p>
  <div class="kpis">
    <div class="kpi"><div class="lbl">글당 평균 조회수</div><div class="v">{a_views:.0f}</div>
      <div class="cmp">합계 {tot_views:,}회</div></div>
    <div class="kpi"><div class="lbl">노출 범위</div><div class="v">{exposure:.1f}%</div>
      <div class="cmp">팔로워 {followers:,}명 대비</div></div>
    <div class="kpi"><div class="lbl">반응 합계</div><div class="v">{tot_react}</div>
      <div class="cmp">좋아요+답글+리포스트+인용+공유</div></div>
    <div class="kpi"><div class="lbl">분석 글</div><div class="v">{n}</div>
      <div class="cmp">최근 {ANALYSIS_MONTHS}개월</div></div>
  </div>

  <h3>분석</h3>
  {ins_html}
  {chk_html}

  <h3>종합 랭킹</h3>
  <p class="sub">조회수 순 · 상위 {RANK_LIMIT}위까지</p>
  {champ_html}
  {rank_html}
  {react_html}
</section>

{LIMITS_HTML}"""

    detail = f"""<section class="acct">
  <div class="acct-h">
    <h2>@{esc(uname)}</h2>
    <span class="dim">{esc(period)} · 분석 글 {n}개</span>
  </div>

  <h3>유형별 노출</h3>
  <p class="sub">글당 평균 조회수</p>
  {type_html}

  <h3>해시태그별 노출</h3>
  <p class="sub">{MIN_N}회 이상 사용한 해시태그만 · 글당 평균 조회수</p>
  {tag_html}

  <h3>본문 길이 · 해시태그 개수</h3>
  <p class="sub">글당 평균 조회수</p>
  <div class="two">
    <div><div class="mini-t">본문 길이(해시태그 제외)</div>{len_html}</div>
    <div><div class="mini-t">해시태그 개수</div>{tagn_html}</div>
  </div>

  <h3>팔로워 구성</h3>
  <p class="sub">스레드가 추정한 값입니다</p>
  <div class="demos">{demo_html}</div>

  <h3>누적 반응</h3>
  <p class="sub">분석 글 {n}개 · 전체 기간 합계 {tot_react:,}건. 계속 쌓이기만 하는 값이라
    그날그날의 성과보다는 계정 규모를 가늠할 때 봅니다.</p>
  <div class="kpis">{react_tot_html}</div>

  <h3>참고 지표</h3>
  <p class="sub">표본이 적어 참고용입니다.</p>
  {toggle("언어별 노출", lang_inner)}
  {toggle("게시 시각별 노출", hour_inner)}
  {toggle("요일별 노출", dow_inner)}
</section>"""

    gen = report.get("generated_at", "")
    for body, key, name, title in (
            (inner, "analysis", "threads-analysis.html", "콘텐츠 분석"),
            (detail, "detail", "threads-detail.html", "세부 분석")):
        lead = lead_ig if key == "analysis" else "자주 볼 지표는 아니지만, 방향을 정할 때 참고합니다."
        with open(os.path.join(DIR, name), "w", encoding="utf-8") as f:
            f.write(layout.document("th", key, title, body, CSS,
                                    updated=layout.fmt_updated(gen), generated_iso=gen,
                                    lead=lead))
        print(f"저장됨: {name}")
    print(f"(@{uname} · 분석 글 {n}개 · 반응 {tot_react}건)")


if __name__ == "__main__":
    build()
