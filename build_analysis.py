"""
posts_cache.json 을 읽어 성과 분석 페이지(analysis.html)를 만든다.

구성:
  종합 판정 / 핵심 지표 / 포맷별 / 해시태그 성과 / 캡션 길이 / 신규 유입 /
  팔로워 구성 / 게시물 랭킹(상위 3 노출, 하위는 토글, 전체 10위까지) /
  언어별·시각별(토글로 숨김) / 자동 해석 / 한계

실행: python3 build_analysis.py
"""

import json
import os
import re
from datetime import datetime, timedelta, timezone

DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(DIR, "analysis.html")

BENCH_ER_FOLLOWERS = 0.48          # 2026 업계 평균 참여율(팔로워 기준), Socialinsider
BENCH_FORMAT = {"CAROUSEL_ALBUM": 0.55, "IMAGE": 0.37, "VIDEO": 0.52, "REELS": 0.52}
RANK_LIMIT = 10                    # 랭킹은 10위까지만
TOP_VISIBLE = 3                    # 상위 3개만 펼쳐서 보여줌
MIN_N = 5                          # 이 미만이면 "표본 부족" 경고

# 오래된 게시물은 인스타그램이 도달을 과소 집계해 좋아요보다 도달이 작아지는 경우가 있다
# (예: 2019년 게시물 도달 27 · 좋아요 42 → 참여율 150%). 그래서 최근 기간만 분석한다.
ANALYSIS_MONTHS = 24
MIN_POSTS = 10          # 이보다 적으면 비율 분석이 무의미해 요약만 보여준다

TYPE_KO = {"IMAGE": "단일 이미지", "CAROUSEL_ALBUM": "캐러셀",
           "VIDEO": "동영상", "REELS": "릴스"}
DOW = ["월", "화", "수", "목", "금", "토", "일"]
HASHTAG_RX = re.compile(r"#([^\s#​]+)")


# ------------------------------------------------------------ 데이터 준비

def load(name, default):
    p = os.path.join(DIR, name)
    if not os.path.exists(p):
        return default
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


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


def prep(cache, report):
    """분석 대상 계정 목록을 만든다. 인사이트 있는 게시물만 사용."""
    accounts = []
    for acc in report.get("accounts", []):
        # posts_cache 의 키는 ig_id 이고, profile 에도 id 가 함께 내려온다
        ig = str(acc["profile"].get("id") or "")
        slot = cache.get(ig)
        if slot is None:
            slot = list(cache.values())[0] if len(cache) == 1 else {}
        posts = []
        excluded_old = excluded_bad = 0
        cutoff = (datetime.now(timezone.utc) + timedelta(hours=9)
                  - timedelta(days=int(ANALYSIS_MONTHS * 30.44)))
        for p in slot.values():
            ins = p.get("insights") or {}
            if ins.get("reach") is None:
                continue
            ts = p.get("timestamp", "")
            try:
                dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S%z") + timedelta(hours=9)
            except ValueError:
                continue
            if dt < cutoff:                       # 분석 기간 밖
                excluded_old += 1
                continue
            _inter = ((p.get("like_count") or 0) + (p.get("comments_count") or 0)
                      + (ins.get("saved") or 0) + (ins.get("shares") or 0))
            # 도달이 0이거나 반응보다 작으면 비율 계산이 불가능/무의미하다
            if not ins["reach"] or _inter > ins["reach"]:
                excluded_bad += 1
                continue
            cap = p.get("caption") or ""
            tags = list(dict.fromkeys(t.lower() for t in HASHTAG_RX.findall(cap)))
            body = HASHTAG_RX.sub("", cap).strip()
            inter = ((p.get("like_count") or 0) + (p.get("comments_count") or 0)
                     + (ins.get("saved") or 0) + (ins.get("shares") or 0))
            reach = ins["reach"] or 0
            posts.append({
                "dt": dt, "date": dt.strftime("%Y-%m-%d"), "md": dt.strftime("%m-%d"),
                "dow": DOW[dt.weekday()], "hour": dt.hour,
                "type": p.get("media_type") or "IMAGE",
                "permalink": p.get("permalink") or "",
                "caption": cap, "body": body, "tags": tags,
                "cap_len": len(body), "tag_n": len(tags),
                "lang": guess_lang(body),
                "likes": p.get("like_count") or 0,
                "comments": p.get("comments_count") or 0,
                "saved": ins.get("saved") or 0,
                "shares": ins.get("shares") or 0,
                "views": ins.get("views") or 0,
                "profile_visits": ins.get("profile_visits") or 0,
                "follows": ins.get("follows") or 0,
                "reach": reach, "inter": inter,
                "er": inter / reach * 100 if reach else 0,
            })
        posts.sort(key=lambda x: x["dt"], reverse=True)
        if posts:
            accounts.append({"acc": acc, "posts": posts,
                             "excluded_old": excluded_old, "excluded_bad": excluded_bad})
    return accounts


# ------------------------------------------------------------ 집계 도구

def avg(rows, f):
    rows = [r for r in rows if f(r) is not None]
    return sum(f(r) for r in rows) / len(rows) if rows else 0


def group_stats(posts, keyfn):
    out = {}
    for p in posts:
        for k in (keyfn(p) if isinstance(keyfn(p), list) else [keyfn(p)]):
            out.setdefault(k, []).append(p)
    stats = []
    for k, rows in out.items():
        r = avg(rows, lambda x: x["reach"])
        stats.append({
            "key": k, "n": len(rows), "reach": r,
            "inter": avg(rows, lambda x: x["inter"]),
            "er": (avg(rows, lambda x: x["inter"]) / r * 100) if r else 0,
        })
    return sorted(stats, key=lambda s: -s["er"])


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def bars(rows, label, sub, emphasize_first=False, max_rows=None, narrow=False):
    """수평 막대 SVG. rows = [{key,n,er,...}]
    narrow=True 는 2단 배치용 (좁은 칸에서도 글자가 뭉개지지 않게 좌표계를 줄임)."""
    rows = rows[:max_rows] if max_rows else rows
    if not rows:
        return '<p class="empty">데이터가 없습니다</p>'
    if narrow:
        BH, GAP, L, R, W = 26, 10, 78, 104, 400
    else:
        BH, GAP, L, R, W = 28, 11, 150, 200, 860
    bw = W - L - R
    mx = max(r["er"] for r in rows) or 1
    out = []
    for i, r in enumerate(rows):
        y = i * (BH + GAP) + 6
        w = max(r["er"] / mx * bw, 2)
        cls = "bar" if (not emphasize_first or i == 0) else "bar muted"
        out.append(f'<text class="cat" x="0" y="{y+BH/2+4:.0f}">{esc(label(r))}</text>')
        out.append(f'<rect class="{cls}" x="{L}" y="{y}" width="{w:.1f}" height="{BH}" rx="4"/>')
        out.append(f'<text class="val" x="{L+w+8:.1f}" y="{y+BH/2+4:.0f}">{r["er"]:.1f}%'
                   f'<tspan class="dim2"> {esc(sub(r))}</tspan></text>')
    h = len(rows) * (BH + GAP) + 8
    return f'<svg viewBox="0 0 {W} {h}">' + "".join(out) + "</svg>"


def warn(n_min, what):
    return (f'<div class="warn">⚠️ {what} 표본이 {n_min}개뿐인 항목이 있습니다. '
            f'우연일 가능성이 높아 판단 근거로 쓰기엔 부족합니다 (권장 {MIN_N}개 이상).</div>')


def toggle(title, inner, open_=False):
    o = " open" if open_ else ""
    return (f'<details class="tg"{o}><summary>{esc(title)}</summary>'
            f'<div class="tg-body">{inner}</div></details>')


def line_chart(rows, key, label):
    """history 기반 추이 선그래프. rows=[{date, value}]"""
    rows = [r for r in rows if r.get(key) is not None]
    if len(rows) < 2:
        n = len(rows)
        txt = (f"{rows[0]['date']} · {rows[0][key]} (내일부터 선이 그려집니다)"
               if n == 1 else "기록이 아직 없습니다")
        return f'<svg viewBox="0 0 860 120"><text class="cat" x="430" y="60" text-anchor="middle">{esc(txt)}</text></svg>'
    W, H, PAD = 860, 200, 38
    vals = [r[key] for r in rows]
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1
    step = (W - PAD * 2) / (len(rows) - 1)
    pts = [(PAD + i * step, H - PAD - (v - lo) / rng * (H - PAD * 2))
           for i, v in enumerate(vals)]
    s = [f'<line class="grid" x1="{PAD}" y1="{PAD+(g/3)*(H-PAD*2):.0f}" '
         f'x2="{W-PAD}" y2="{PAD+(g/3)*(H-PAD*2):.0f}"/>' for g in range(4)]
    s.append(f'<text class="ax" x="{PAD-6}" y="{PAD+4}" text-anchor="end">{hi}</text>')
    s.append(f'<text class="ax" x="{PAD-6}" y="{H-PAD+4}" text-anchor="end">{lo}</text>')
    s.append('<path class="ln" d="' +
             " ".join(("M" if i == 0 else "L") + f"{x:.1f},{y:.1f}" for i, (x, y) in enumerate(pts)) + '"/>')
    every = max(1, len(pts) // 6)
    for i, (x, y) in enumerate(pts):
        if i in (0, len(pts) - 1) or i % every == 0:
            s.append(f'<circle class="dot" cx="{x:.1f}" cy="{y:.1f}" r="3.5"/>')
            s.append(f'<text class="ax" x="{x:.1f}" y="{H-12}" text-anchor="middle">{rows[i]["date"][5:]}</text>')
    return f'<svg viewBox="0 0 {W} {H}">' + "".join(s) + "</svg>"


# ------------------------------------------------------------ 섹션 렌더

def render_thin(a):
    """게시물이 너무 적어 비율 분석이 무의미한 계정 — 원시 숫자만 보여준다."""
    acc, posts = a["acc"], a["posts"]
    prof = acc["profile"]
    uname = prof.get("username", "?")
    rows = "".join(
        f'<tr><td class="nw">{p["date"]}</td>'
        f'<td><span class="chip">{TYPE_KO.get(p["type"], p["type"])}</span></td>'
        f'<td class="cap">{esc(p["body"][:34] or "(내용 없음)")}</td>'
        f'<td class="num">{p["reach"]}</td><td class="num">{p["likes"]}</td>'
        f'<td class="num">{p["comments"]}</td></tr>'
        for p in posts)
    return f"""
<section class="acct">
  <div class="acct-h">
    <h2>@{esc(uname)}</h2>
    <span class="dim">분석 가능 게시물 {len(posts)}개 · 팔로워 {prof.get("followers_count", 0):,}명</span>
  </div>
  <div class="warn">게시물이 {MIN_POSTS}개 미만이라 참여율·저장률 같은 비율 지표를 계산하지 않았습니다.
  도달이 한 자릿수라 비율로 바꾸면 수치가 크게 튀어 잘못된 판단을 유도합니다.
  게시물이 {MIN_POSTS}개 이상 쌓이면 자동으로 전체 분석이 표시됩니다.</div>
  <table><thead><tr><th>게시일</th><th>포맷</th><th>내용</th>
    <th class="num">도달</th><th class="num">좋아요</th><th class="num">댓글</th></tr></thead>
    <tbody>{rows}</tbody></table>
</section>"""


def render_account(a, hist):
    acc, posts = a["acc"], a["posts"]
    prof = acc["profile"]
    F = prof.get("followers_count") or 1
    uname = prof.get("username", "?")
    ins = acc.get("account_insights", {})
    demo = acc.get("demographics", {})
    rows_hist = hist.get(uname, [])

    n = len(posts)
    a_reach = avg(posts, lambda p: p["reach"])
    a_inter = avg(posts, lambda p: p["inter"])
    er_reach = a_inter / a_reach * 100 if a_reach else 0
    er_fol = a_inter / F * 100
    tot_reach = sum(p["reach"] for p in posts) or 1
    save_rate = sum(p["saved"] for p in posts) / tot_reach * 100
    share_rate = sum(p["shares"] for p in posts) / tot_reach * 100
    bench_x = er_fol / BENCH_ER_FOLLOWERS if BENCH_ER_FOLLOWERS else 0

    # ---- 포맷별
    fmt = group_stats(posts, lambda p: p["type"])
    fmt_html = bars(fmt, lambda r: TYPE_KO.get(r["key"], r["key"]),
                    lambda r: f'· {r["n"]}개 · 도달 {r["reach"]:.0f}', emphasize_first=True)
    fmt_read = ""
    if len(fmt) >= 2 and fmt[1]["er"]:
        top, snd = fmt[0], fmt[1]
        fmt_read = (f'<p><b>{TYPE_KO.get(top["key"],top["key"])}가 '
                    f'{TYPE_KO.get(snd["key"],snd["key"])}보다 참여율 '
                    f'{top["er"]/snd["er"]:.1f}배 높습니다.</b> '
                    f'각각 게시물 {top["n"]}개 / {snd["n"]}개 기준입니다. '
                    f'업계 벤치마크도 캐러셀 {BENCH_FORMAT["CAROUSEL_ALBUM"]}% / '
                    f'이미지 {BENCH_FORMAT["IMAGE"]}%로 같은 방향입니다.</p>')

    # ---- 해시태그 (5회 이상 사용된 것만)
    tag_stats = [t for t in group_stats(posts, lambda p: p["tags"] or ["(태그 없음)"])
                 if t["n"] >= MIN_N]
    tag_html = bars(tag_stats, lambda r: "#" + r["key"] if r["key"] != "(태그 없음)" else r["key"],
                    lambda r: f'· {r["n"]}개', max_rows=15)
    tagged = [p for p in posts if p["tag_n"]]
    tag_read = (f'<p>해시태그가 있는 게시물은 {len(tagged)}개, 없는 게시물은 {n-len(tagged)}개입니다. '
                f'게시물당 평균 {avg(posts, lambda p: p["tag_n"]):.1f}개를 사용했습니다 '
                f'(인스타그램 허용 한도는 30개).</p>')

    # ---- 해시태그 개수 구간별
    def tag_bucket(p):
        k = p["tag_n"]
        return "0개" if k == 0 else ("1–3개" if k <= 3 else ("4–7개" if k <= 7 else "8개 이상"))
    tagn = group_stats(posts, tag_bucket)
    tagn_html = bars(tagn, lambda r: r["key"], lambda r: f'· {r["n"]}개', narrow=True)

    # ---- 캡션 길이 구간별
    def cap_bucket(p):
        k = p["cap_len"]
        return "~50자" if k <= 50 else ("51–150자" if k <= 150 else ("151–400자" if k <= 400 else "400자 초과"))
    capb = group_stats(posts, cap_bucket)
    capb_html = bars(capb, lambda r: r["key"], lambda r: f'· {r["n"]}개', narrow=True)

    # ---- 랭킹
    ranked = sorted(posts, key=lambda p: -p["er"])[:RANK_LIMIT]

    def rank_row(i, p):
        link = (f'<a href="{esc(p["permalink"])}" target="_blank" rel="noopener">{esc(p["body"][:34] or "(내용 없음)")}</a>'
                if p["permalink"] else esc(p["body"][:34] or "(내용 없음)"))
        return (f'<tr><td class="num">{i+1}</td>'
                f'<td class="nw">{p["md"]}<span class="dim"> {p["dow"]} {p["hour"]}시</span></td>'
                f'<td><span class="chip">{TYPE_KO.get(p["type"], p["type"])}</span></td>'
                f'<td class="cap">{link}</td>'
                f'<td class="num strong">{p["er"]:.1f}%</td>'
                f'<td class="num">{p["reach"]}</td>'
                f'<td class="num">{p["inter"]}</td>'
                f'<td class="num">{(p["saved"]+p["shares"]) or "–"}</td></tr>')

    head = ('<thead><tr><th>#</th><th>게시일</th><th>포맷</th><th>내용</th>'
            '<th class="num">참여율</th><th class="num">도달</th>'
            '<th class="num">반응</th><th class="num">저장+공유</th></tr></thead>')
    top_rows = "".join(rank_row(i, p) for i, p in enumerate(ranked[:TOP_VISIBLE]))
    rest_rows = "".join(rank_row(i + TOP_VISIBLE, p) for i, p in enumerate(ranked[TOP_VISIBLE:]))
    rank_html = f'<table>{head}<tbody>{top_rows}</tbody></table>'
    if rest_rows:
        rank_html += toggle(f"{TOP_VISIBLE+1}위 ~ {len(ranked)}위 보기",
                            f'<table>{head}<tbody>{rest_rows}</tbody></table>')

    # ---- 참고용 (토글)
    lang = group_stats(posts, lambda p: p["lang"])
    hour = group_stats(posts, lambda p: p["hour"])
    dow = group_stats(posts, lambda p: p["dow"])
    lang_inner = (warn(min(l["n"] for l in lang), "언어별") if lang and min(l["n"] for l in lang) < MIN_N else "") \
        + bars(lang, lambda r: r["key"], lambda r: f'· {r["n"]}개')
    hour_inner = (warn(min(h["n"] for h in hour), "시각별") if hour and min(h["n"] for h in hour) < MIN_N else "") \
        + bars(sorted(hour, key=lambda r: -r["er"]), lambda r: f'{r["key"]}시',
               lambda r: f'· {r["n"]}개', max_rows=12)
    dow_inner = bars(dow, lambda r: f'{r["key"]}요일', lambda r: f'· {r["n"]}개')

    # ---- 신규 유입
    nf = ins.get("reach_non_follower")
    nf_total = (ins.get("reach") or 0)
    nf_pct = (nf / nf_total * 100) if (nf is not None and nf_total) else None
    inflow = (f'<div class="kpis">'
              f'<div class="kpi"><div class="lbl">오늘 도달</div><div class="v">{nf_total or "–"}</div></div>'
              f'<div class="kpi"><div class="lbl">비팔로워 도달</div><div class="v">{nf if nf is not None else "–"}</div>'
              f'<div class="cmp">{f"전체 도달의 {nf_pct:.0f}%" if nf_pct is not None else "수집 대기"}</div></div>'
              f'<div class="kpi"><div class="lbl">누적 프로필 방문</div><div class="v">{sum(p["profile_visits"] for p in posts)}</div>'
              f'<div class="cmp">게시물 {n}개 합계</div></div>'
              f'<div class="kpi"><div class="lbl">게시물發 팔로우</div><div class="v">{sum(p["follows"] for p in posts)}</div>'
              f'<div class="cmp">게시물 {n}개 합계</div></div></div>'
              f'<p class="sub" style="margin-top:14px">비팔로워 도달은 해시태그·탐색탭·공유를 타고 새로 들어온 사람입니다. '
              f'이 비율이 오르면 신규 유입이 늘고 있다는 뜻입니다.</p>'
              + line_chart(rows_hist, "reach_non_follower", "비팔로워 도달"))

    # ---- 팔로워 구성
    def demo_block(title, d, top=6):
        if not d:
            return ""
        items = sorted(d.items(), key=lambda kv: -kv[1])[:top]
        mx = max(v for _, v in items) or 1
        rows = "".join(
            f'<div class="dm"><span class="dm-k">{esc(k)}</span>'
            f'<span class="dm-bar"><i style="width:{v/mx*100:.0f}%"></i></span>'
            f'<span class="dm-v">{v}</span></div>' for k, v in items)
        return f'<div class="dm-box"><div class="dm-t">{esc(title)}</div>{rows}</div>'
    demo_html = ("".join([demo_block("연령", demo.get("age")),
                          demo_block("성별", demo.get("gender")),
                          demo_block("도시", demo.get("city")),
                          demo_block("국가", demo.get("country"))])
                 or '<p class="empty">인구통계 데이터가 아직 없습니다</p>')

    # ---- 자동 해석
    best = ranked[0] if ranked else None
    reads = []
    if best:
        reads.append(f'<p>1위는 <b>{best["md"]} {TYPE_KO.get(best["type"], best["type"])}</b>로 참여율 '
                     f'{best["er"]:.1f}%입니다. 도달 {best["reach"]}명 중 {best["inter"]}명이 반응했고, '
                     f'전체 평균({er_reach:.1f}%)의 {best["er"]/er_reach:.1f}배입니다.</p>')
    if fmt:
        cnt = sum(1 for p in ranked[:TOP_VISIBLE] if p["type"] == fmt[0]["key"])
        reads.append(f'<p>상위 {TOP_VISIBLE}개 중 <b>{cnt}개가 '
                     f'{TYPE_KO.get(fmt[0]["key"], fmt[0]["key"])}</b>입니다.</p>')
    mx_reach = max(posts, key=lambda p: p["reach"])
    mx_rank = sorted(posts, key=lambda p: -p["er"]).index(mx_reach) + 1
    reads.append(f'<p>도달이 가장 높았던 게시물({mx_reach["md"]}, 도달 {mx_reach["reach"]})은 '
                 f'참여율로는 {mx_rank}위입니다. <b>도달과 참여율은 별개</b>이므로 도달만 보면 판단을 틀리게 됩니다.</p>')
    reads.append(f'<p>저장 {sum(p["saved"] for p in posts)}건, 공유 {sum(p["shares"] for p in posts)}건입니다 '
                 f'(게시물 {n}개 합계). 알고리즘이 가중치를 크게 주는 신호입니다. '
                 f'제품 비교, 사용법, 매장 정보처럼 <b>다시 꺼내볼 이유가 있는 콘텐츠</b>가 저장을 만듭니다.</p>')

    period = f'{posts[-1]["date"]} ~ {posts[0]["date"]}'
    ex_old, ex_bad = a.get("excluded_old", 0), a.get("excluded_bad", 0)
    ex_parts = []
    if ex_old:
        ex_parts.append(f"{ANALYSIS_MONTHS}개월 이전 {ex_old}개")
    if ex_bad:
        ex_parts.append(f"도달 집계 오류 {ex_bad}개")
    ex_note = (f'<div class="warn" style="margin-top:12px">제외된 게시물: {" · ".join(ex_parts)}. '
               f'오래된 게시물은 인스타그램이 도달을 과소 집계해 참여율이 비정상으로 나오므로 '
               f'최근 {ANALYSIS_MONTHS}개월만 분석합니다.</div>') if ex_parts else ""

    return f"""
<section class="acct">
  <div class="acct-h">
    <h2>@{esc(uname)}</h2>
    <span class="dim">{esc(period)} · 분석 게시물 {n}개 · 팔로워 {F:,}명</span>
  </div>
  {ex_note}

  <div class="verdict">
    <div class="hero">{er_fol:.2f}<span class="hu">%</span></div>
    <span class="badge {'good' if bench_x >= 1 else 'warn'}">업계 평균의 {bench_x:.1f}배</span>
    <span class="badge {'warn' if save_rate < 0.5 else 'good'}">저장률 {save_rate:.2f}%</span>
  </div>
  <p class="sub">참여율(팔로워 기준). 2026년 인스타그램 유기적 참여율 평균은 {BENCH_ER_FOLLOWERS}%입니다.</p>

  <div class="kpis">
    <div class="kpi"><div class="lbl">참여율 (도달 기준)</div><div class="v">{er_reach:.1f}%</div>
      <div class="cmp">본 사람 100명 중 {er_reach:.0f}명이 반응</div></div>
    <div class="kpi"><div class="lbl">참여율 (팔로워 기준)</div><div class="v">{er_fol:.2f}%</div>
      <div class="cmp {'good' if er_fol >= BENCH_ER_FOLLOWERS else 'bad'}">업계 평균 대비 {(er_fol-BENCH_ER_FOLLOWERS)/BENCH_ER_FOLLOWERS*100:+.0f}%</div></div>
    <div class="kpi"><div class="lbl">도달률</div><div class="v">{a_reach/F*100:.1f}%</div>
      <div class="cmp">평균 {a_reach:.0f}명에게 노출</div></div>
    <div class="kpi"><div class="lbl">저장률</div><div class="v">{save_rate:.2f}%</div>
      <div class="cmp">합계 {sum(p['saved'] for p in posts)}건</div></div>
    <div class="kpi"><div class="lbl">공유율</div><div class="v">{share_rate:.2f}%</div>
      <div class="cmp">합계 {sum(p['shares'] for p in posts)}건</div></div>
  </div>

  <h3>자동 해석</h3>
  <p class="sub">갱신될 때마다 데이터에 맞춰 다시 쓰입니다</p>
  <div class="reads reads-box">{''.join(reads)}</div>

  <h3>포맷별 성과</h3>
  <p class="sub">참여율(도달 기준) — 본 사람 대비 반응 비율</p>
  {fmt_html}
  <div class="legend"><span><i class="sw"></i>가장 성과가 좋은 포맷</span>
    <span><i class="sw g"></i>비교군</span></div>
  <div class="reads">{fmt_read}</div>

  <h3>해시태그별 성과</h3>
  <p class="sub">{MIN_N}회 이상 사용한 해시태그만 · 참여율(도달 기준) 순</p>
  {tag_html}
  <div class="reads">{tag_read}</div>

  <h3>해시태그 개수 · 캡션 길이</h3>
  <p class="sub">참여율(도달 기준)</p>
  <div class="two">
    <div><div class="mini-t">해시태그 개수</div>{tagn_html}</div>
    <div><div class="mini-t">캡션 길이(해시태그 제외)</div>{capb_html}</div>
  </div>

  <h3>신규 유입</h3>
  {inflow}

  <h3>팔로워 구성</h3>
  <p class="sub">인스타그램이 추정한 값입니다</p>
  <div class="demos">{demo_html}</div>

  <h3>게시물 랭킹</h3>
  <p class="sub">참여율(도달 기준) 순 · 상위 {RANK_LIMIT}위까지</p>
  {rank_html}

  <h3>참고 지표</h3>
  <p class="sub">표본이 적어 참고용입니다. 필요할 때 펼쳐 보세요.</p>
  {toggle("언어별 성과", lang_inner)}
  {toggle("게시 시각별 성과", hour_inner)}
  {toggle("요일별 성과", dow_inner)}
</section>"""


CSS = """
:root { color-scheme: light only;
  --text:#111; --text2:#444; --muted:#6b6b6b; --grid:#e6e6e6; --border:rgba(17,17,17,.14);
  --accent:#1f6fc7; --accent-soft:#cde2fb; --gray:#c9c9c9;
  --good:#046a04; --warnc:#8a5a00; --bad:#b32626; }
* { box-sizing:border-box; }
html, body { background:#fff; }
body { margin:0; color:var(--text); font-family:system-ui,-apple-system,"Segoe UI",sans-serif; }
.wrap { max-width:960px; margin:0 auto; padding:26px 18px 80px; }
.nav { display:flex; gap:10px; align-items:center; font-size:13px; margin-bottom:22px; }
.nav a { color:var(--accent); text-decoration:none; padding:6px 12px; border:1px solid var(--border); border-radius:999px; }
.nav a.on { background:var(--accent); border-color:var(--accent); color:#fff; font-weight:600; }
h1 { font-size:22px; margin:0 0 4px; }
.updated { font-size:12px; color:var(--muted); margin-bottom:26px; }
section.acct { border:1px solid var(--border); border-radius:12px; padding:20px 22px; margin-bottom:26px; }
.acct-h { display:flex; align-items:baseline; gap:12px; flex-wrap:wrap; margin-bottom:16px;
  padding-bottom:12px; border-bottom:1px solid var(--grid); }
.acct-h h2 { font-size:19px; margin:0; }
h3 { font-size:15px; margin:30px 0 3px; }
.sub { font-size:12px; color:var(--muted); margin:0 0 14px; }
.dim { color:var(--muted); } .nw { white-space:nowrap; }
.verdict { display:flex; align-items:baseline; gap:13px; flex-wrap:wrap; margin-bottom:4px; }
.hero { font-size:44px; font-weight:650; line-height:1; }
.hu { font-size:16px; color:var(--muted); font-weight:400; }
.badge { font-size:12px; font-weight:600; padding:4px 10px; border-radius:999px; }
.badge.good { background:#e6f4e6; color:var(--good); }
.badge.warn { background:#fdf1dc; color:var(--warnc); }
.kpis { display:grid; grid-template-columns:repeat(auto-fit,minmax(158px,1fr)); gap:11px; }
.kpi { border:1px solid var(--border); border-radius:10px; padding:13px 14px; }
.kpi .lbl { font-size:12px; color:var(--text2); margin-bottom:7px; }
.kpi .v { font-size:24px; font-weight:620; line-height:1; }
.kpi .cmp { font-size:11px; margin-top:6px; color:var(--muted); }
.kpi .cmp.good { color:var(--good); } .kpi .cmp.bad { color:var(--bad); }
svg { display:block; width:100%; height:auto; overflow:visible; }
.bar { fill:var(--accent); } .bar.muted { fill:var(--gray); }
.cat { fill:var(--text2); font-size:12px; }
.val { fill:var(--text); font-size:12px; font-weight:600; }
.dim2 { fill:var(--muted); font-weight:400; font-size:11px; }
.ax { fill:var(--muted); font-size:10px; }
.grid { stroke:var(--grid); stroke-width:1; }
.ln { fill:none; stroke:var(--accent); stroke-width:2; stroke-linecap:round; stroke-linejoin:round; }
.dot { fill:var(--accent); }
.legend { display:flex; gap:16px; font-size:11.5px; color:var(--text2); margin-top:11px; }
.sw { display:inline-block; width:10px; height:10px; border-radius:2px; background:var(--accent); margin-right:5px; }
.sw.g { background:var(--gray); }
table { width:100%; border-collapse:collapse; font-size:12.5px; }
th, td { text-align:left; padding:8px 7px; border-bottom:1px solid var(--grid); }
th { font-size:10.5px; color:var(--muted); text-transform:uppercase; letter-spacing:.03em; font-weight:500; }
td.num { text-align:right; font-variant-numeric:tabular-nums; }
td.strong { font-weight:650; color:var(--accent); }
td.cap { color:var(--text2); max-width:260px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
td.cap a { color:var(--text2); text-decoration:none; }
td.cap a:hover { color:var(--accent); text-decoration:underline; }
.chip { display:inline-block; font-size:10.5px; padding:2px 7px; border-radius:5px;
  background:var(--accent-soft); color:#164a86; white-space:nowrap; }
.reads p { font-size:13.5px; line-height:1.65; margin:12px 0 0; }
.reads p:first-child { margin-top:0; }
.reads b { color:var(--accent); }
.reads-box { border:1px solid var(--border); border-left:3px solid var(--accent);
  border-radius:9px; padding:14px 16px; background:#fbfcfe; }
.warn { background:#fdf6e6; border:1px solid #f0dca0; color:#6b5300;
  border-radius:8px; padding:9px 12px; font-size:12px; margin-bottom:12px; }
.empty { color:var(--muted); font-size:13px; }
details.tg { border:1px solid var(--border); border-radius:9px; margin-bottom:9px; }
details.tg summary { cursor:pointer; padding:11px 14px; font-size:13px; font-weight:600;
  color:var(--text2); list-style:none; display:flex; align-items:center; gap:7px; }
details.tg summary::-webkit-details-marker { display:none; }
details.tg summary::before { content:"▸"; color:var(--accent); font-size:11px; }
details.tg[open] summary::before { content:"▾"; }
details.tg[open] summary { border-bottom:1px solid var(--grid); }
.tg-body { padding:14px; }
.two { display:grid; grid-template-columns:1fr 1fr; gap:22px; }
@media (max-width:700px) { .two { grid-template-columns:1fr; } }
.mini-t { font-size:12px; color:var(--text2); font-weight:600; margin-bottom:9px; }
.demos { display:grid; grid-template-columns:repeat(auto-fit,minmax(215px,1fr)); gap:16px; }
.dm-box { border:1px solid var(--border); border-radius:10px; padding:13px 14px; }
.dm-t { font-size:12px; font-weight:600; color:var(--text2); margin-bottom:10px; }
.dm { display:grid; grid-template-columns:74px 1fr 40px; align-items:center; gap:8px; margin-bottom:6px; font-size:11.5px; }
.dm-k { color:var(--text2); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.dm-bar { background:var(--grid); border-radius:3px; height:8px; overflow:hidden; }
.dm-bar i { display:block; height:100%; background:var(--accent); border-radius:3px; }
.dm-v { text-align:right; font-variant-numeric:tabular-nums; color:var(--text); }
.limits { font-size:12.5px; color:var(--text2); line-height:1.75; }
"""


def build():
    cache = load("posts_cache.json", {})
    report = load("report_data.json", {"accounts": []})
    hist = load("history.json", {})
    accounts = prep(cache, report)

    gen = report.get("generated_at", "")
    body = "".join(render_account(a, hist) if len(a["posts"]) >= MIN_POSTS
                   else render_thin(a) for a in accounts) or \
        '<section class="acct"><p class="empty">분석할 데이터가 없습니다. instagram_api.py 를 먼저 실행하세요.</p></section>'

    total = sum(a["acc"].get("posts_total", 0) for a in accounts)
    anal = sum(len(a["posts"]) for a in accounts)

    html = f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<title>성과 분석</title>
<style>{CSS}</style></head><body><div class="wrap">
<div class="nav"><a href="./">일일 리포트</a><a class="on" href="./analysis.html">성과 분석</a></div>
<h1>성과 분석</h1>
<div class="updated">업데이트: {esc(gen)} · 전체 게시물 {total}개 중 인사이트 있는 {anal}개 분석</div>
{body}
<section class="acct">
  <h2 style="font-size:15px;margin:0 0 12px">이 분석의 한계</h2>
  <div class="limits">
    인사이트(도달·조회·저장)는 계정을 프로페셔널로 전환한 이후 게시물에만 존재합니다. 그 이전 게시물은 좋아요·댓글·해시태그만 남아 분석에서 제외됩니다.<br>
    표본이 {MIN_N}개 미만인 항목은 경고를 붙였습니다. 우연일 가능성이 높아 판단 근거로 쓰지 마세요.<br>
    게시물별로 "해시태그를 타고 들어왔는지"는 API가 제공하지 않습니다. 비팔로워 도달로 신규 유입 총량만 알 수 있고, 경로별 구분은 인스타그램 앱에서 직접 확인해야 합니다.<br>
    "왜 좋았는지"의 진짜 원인(이미지의 매력, 소재의 시의성)은 숫자로 나오지 않습니다.
  </div>
</section>
</div></body></html>"""

    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"저장됨: {OUT} (계정 {len(accounts)}개 · 분석 게시물 {anal}개)")


if __name__ == "__main__":
    build()
