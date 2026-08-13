"""
posts_cache.json 을 읽어 콘텐츠 분석 페이지(analysis.html)를 만든다.

구성:
  종합 판정 / 핵심 지표 / 분석(인사이트·확인 필요) /
  게시물 랭킹(전체 1위 카드 + 전체 랭킹 + 도달·저장·공유 랭킹) /
  포맷별 / 해시태그 성과 / 해시태그 개수·캡션 길이 / 팔로워 구성 /
  참고 지표(언어별·시각별·요일별, 토글) / 한계

용어: 참여율→반응률, 참여율(팔로워)→팔로워 반응률(참고용), 도달률→노출 범위

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
RANK_LIMIT = 10                    # 전체 랭킹은 10위까지만
MINI_RANK = 5                      # 도달·저장·공유 랭킹은 5위까지만
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


def short(p, w=34):
    return p["body"][:w] or "(내용 없음)"


def linked(p, w=34):
    t = esc(short(p, w))
    return (f'<a href="{esc(p["permalink"])}" target="_blank" rel="noopener">{t}</a>'
            if p["permalink"] else t)


def label_of(p):
    return f'{p["md"]} {TYPE_KO.get(p["type"], p["type"])}'


# ------------------------------------------------------------ 분석 문장

def rank_of(ranked_all, p):
    for i, q in enumerate(ranked_all):
        if q is p:
            return i + 1
    return len(ranked_all)


def build_insights(posts, ranked_all, fmt, tag_stats, er_reach, er_fol,
                   save_rate, share_rate, F, n):
    """마케팅 담당자가 읽고 바로 움직일 수 있는 문장으로 뽑는다.
    반환: (인사이트 문장 리스트, 확인 필요 문장 리스트)"""
    ins, chk = [], []

    # --- 인사이트 ---
    if len(fmt) >= 2 and fmt[1]["er"] and fmt[0]["n"] >= 3:
        top, snd = fmt[0], fmt[1]
        ins.append(
            f'<b>{TYPE_KO.get(top["key"], top["key"])}가 가장 잘 먹힙니다.</b> '
            f'{TYPE_KO.get(snd["key"], snd["key"])}보다 반응률이 {top["er"]/snd["er"]:.1f}배 높습니다'
            f'(각각 {top["n"]}개 / {snd["n"]}개 기준). 다음에 올릴 소재부터 이 포맷으로 맞추는 게 안전합니다.')

    fol_posts = [p for p in posts if p["follows"]]
    tot_fol = sum(p["follows"] for p in posts)
    if fol_posts and tot_fol >= 5:
        tp = max(fol_posts, key=lambda p: p["follows"])
        rk = rank_of(ranked_all, tp)
        ins.append(
            f'<b>팔로워를 실제로 데려온 건 {label_of(tp)}입니다.</b> '
            f'이 게시물 하나가 전체 신규 팔로우 {tot_fol}건 중 {tp["follows"]}건'
            f'({tp["follows"]/tot_fol*100:.0f}%)을 만들었는데, 반응률로는 {rk}위입니다. '
            f'좋아요가 많은 게시물과 팔로워를 만드는 게시물은 다릅니다 — 이 게시물의 소재와 구성을 다시 쓰세요.')

    mx_reach = max(posts, key=lambda p: p["reach"])
    mx_rank = rank_of(ranked_all, mx_reach)
    if mx_rank > 3:
        tail = ('많이 노출됐지만 본 사람 대비 반응은 평균 이하였습니다. '
                if mx_reach["er"] < er_reach else
                '반응률 자체는 나쁘지 않았지만 1위는 아니었습니다. ')
        ins.append(
            f'<b>가장 널리 퍼진 게시물({label_of(mx_reach)}, 도달 {mx_reach["reach"]:,}명)은 '
            f'반응률로는 {mx_rank}위입니다.</b> {tail}'
            f'노출은 알고리즘이 밀어준 결과이고, 반응률은 소재의 힘입니다. 둘을 같이 봐야 합니다.')

    tot_save, tot_share = sum(p["saved"] for p in posts), sum(p["shares"] for p in posts)
    if tot_save or tot_share:
        best_save = max(posts, key=lambda p: p["saved"])
        if best_save["saved"]:
            ins.append(
                f'<b>저장이 가장 많았던 건 {label_of(best_save)}({best_save["saved"]}건)입니다.</b> '
                f'저장은 알고리즘이 좋아요보다 크게 보는 신호이고, "나중에 다시 꺼내볼 이유"가 있을 때 생깁니다 — '
                f'제품 비교, 액상 추천, 매장 위치·영업시간처럼 정보가 담긴 게시물을 늘리면 이 숫자가 올라갑니다.')

    if tag_stats and len(tag_stats) >= 2:
        bt = tag_stats[0]
        ins.append(
            f'<b>#{esc(bt["key"])} 를 붙인 게시물의 반응률이 가장 높습니다</b>'
            f'({bt["er"]:.1f}% · {bt["n"]}개 기준, 전체 평균 {er_reach:.1f}%). '
            f'이 태그와 같은 결의 소재를 더 밀어볼 여지가 있습니다.')

    # --- 확인 필요 ---
    if er_fol < BENCH_ER_FOLLOWERS:
        chk.append(
            f'팔로워 반응률이 {er_fol:.2f}%로 업계 평균 {BENCH_ER_FOLLOWERS}%의 '
            f'{er_fol/BENCH_ER_FOLLOWERS:.1f}배 수준입니다. 팔로워 {F:,}명 중 실제로 반응하는 사람이 적다는 뜻이라, '
            f'게시물 자체보다 팔로워 구성(오래 전 유입·비활성 계정)을 먼저 의심해야 합니다.')

    if save_rate < 0.5:
        chk.append(
            f'저장률 {save_rate:.2f}%는 낮습니다. 지금 게시물이 "보고 지나가는" 콘텐츠에 가깝다는 신호입니다.')

    if share_rate < 0.2:
        chk.append(
            f'공유율 {share_rate:.2f}%도 낮습니다. 공유는 새 사람에게 닿는 가장 싼 경로인데 거의 발생하지 않고 있습니다.')

    recent, older = posts[:10], posts[10:]
    if older:
        rt, ot = avg(recent, lambda p: p["tag_n"]), avg(older, lambda p: p["tag_n"])
        if ot >= 1 and rt < ot * 0.7:
            chk.append(
                f'최근 10개 게시물의 해시태그가 평균 {rt:.1f}개인데, 그 이전은 {ot:.1f}개였습니다. '
                f'태그를 줄이면 팔로워에게는 도달하지만 새 사람에게 발견될 통로가 좁아집니다.')

    if not fol_posts:
        chk.append('분석 기간 게시물 중 팔로우를 만든 게시물이 하나도 없습니다. '
                   '노출은 되는데 프로필까지 넘어오지 않는다는 뜻이라, 캡션 끝에 계정을 팔로우할 이유를 한 줄 넣어보세요.')

    if n < MIN_N * 3:
        chk.append(f'분석 게시물이 {n}개뿐입니다. 아래 비율들은 게시물 하나에 크게 흔들리니 방향만 참고하세요.')

    return ins[:3], chk[:2]


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
  <div class="warn">게시물이 {MIN_POSTS}개 미만이라 반응률·저장률 같은 비율 지표를 계산하지 않았습니다.
  도달이 한 자릿수라 비율로 바꾸면 수치가 크게 튀어 잘못된 판단을 유도합니다.
  게시물이 {MIN_POSTS}개 이상 쌓이면 자동으로 전체 분석이 표시됩니다.</div>
  <table><thead><tr><th>게시일</th><th>포맷</th><th>내용</th>
    <th class="num">도달<br>(본 사람 수)</th><th class="num">좋아요</th><th class="num">댓글</th></tr></thead>
    <tbody>{rows}</tbody></table>
</section>"""


def render_account(a):
    acc, posts = a["acc"], a["posts"]
    prof = acc["profile"]
    F = prof.get("followers_count") or 1
    uname = prof.get("username", "?")
    demo = acc.get("demographics", {})

    n = len(posts)
    a_reach = avg(posts, lambda p: p["reach"])
    a_inter = avg(posts, lambda p: p["inter"])
    er_reach = a_inter / a_reach * 100 if a_reach else 0
    er_fol = a_inter / F * 100
    tot_reach = sum(p["reach"] for p in posts) or 1
    tot_save = sum(p["saved"] for p in posts)
    tot_share = sum(p["shares"] for p in posts)
    save_rate = tot_save / tot_reach * 100
    share_rate = tot_share / tot_reach * 100
    bench_x = er_fol / BENCH_ER_FOLLOWERS if BENCH_ER_FOLLOWERS else 0

    fmt = group_stats(posts, lambda p: p["type"])
    tag_stats = [t for t in group_stats(posts, lambda p: p["tags"] or ["(태그 없음)"])
                 if t["n"] >= MIN_N and t["key"] != "(태그 없음)"]

    ranked_all = sorted(posts, key=lambda p: -p["er"])
    ranked = ranked_all[:RANK_LIMIT]

    # ---- 분석 (인사이트 / 확인 필요)
    ins_list, chk_list = build_insights(posts, ranked_all, fmt, tag_stats,
                                        er_reach, er_fol, save_rate, share_rate, F, n)
    ins_html = ('<div class="ins-box"><div class="ins-t">💡 오늘의 인사이트</div>'
                + "".join(f"<p>{t}</p>" for t in ins_list) + '</div>') if ins_list else ""
    chk_html = ('<div class="chk-box"><div class="chk-t">⚠️ 확인 필요</div>'
                + "".join(f"<p>{t}</p>" for t in chk_list) + '</div>') if chk_list else ""

    # ---- 전체 1위 카드 + 분석 코멘트
    champ = ranked_all[0] if ranked_all else None
    champ_html = ""
    if champ:
        parts = []
        parts.append(f'전체 평균 반응률 {er_reach:.1f}%의 '
                     f'{champ["er"]/er_reach:.1f}배입니다.' if er_reach else "")
        same_fmt = next((f for f in fmt if f["key"] == champ["type"]), None)
        if same_fmt and same_fmt["n"] >= 2:
            parts.append(f'{TYPE_KO.get(champ["type"], champ["type"])} 평균'
                         f'({same_fmt["er"]:.1f}%)보다도 높습니다.')
        drivers = []
        if champ["saved"]:
            drivers.append(f'저장 {champ["saved"]}건')
        if champ["shares"]:
            drivers.append(f'공유 {champ["shares"]}건')
        if champ["follows"]:
            drivers.append(f'팔로우 {champ["follows"]}건')
        if drivers:
            parts.append('단순 좋아요가 아니라 ' + ' · '.join(drivers) +
                         '이 함께 나왔습니다 — 알고리즘이 크게 보는 신호입니다.')
        else:
            parts.append('다만 저장·공유는 없었습니다. 좋아요 위주의 반응이라 '
                         '노출이 더 퍼지는 힘까지는 만들지 못했습니다.')
        if champ["tag_n"]:
            parts.append(f'해시태그 {champ["tag_n"]}개, 캡션 {champ["cap_len"]}자 구성입니다.')
        else:
            parts.append(f'해시태그 없이 캡션 {champ["cap_len"]}자만으로 나온 결과입니다.')

        champ_html = f'''
  <div class="champ">
    <div class="champ-h"><span class="badge good">전체 1위</span>
      <b>{TYPE_KO.get(champ["type"], champ["type"])}</b>
      <span class="champ-er">반응률 {champ["er"]:.1f}%</span>
      <span class="dim">{champ["date"]} {champ["dow"]}요일 {champ["hour"]}시</span></div>
    <p class="champ-cap">{linked(champ, 90)}</p>
    <div class="champ-k">도달(본 사람 수) {champ["reach"]:,} · 반응 {champ["inter"]} ·
      좋아요 {champ["likes"]} · 댓글 {champ["comments"]} · 저장 {champ["saved"]} ·
      공유 {champ["shares"]} · 팔로워 +{champ["follows"]}</div>
    <p class="champ-note">{" ".join(p for p in parts if p)}</p>
  </div>'''

    # ---- 전체 랭킹 (반응률 순)
    def rank_row(i, p):
        return (f'<tr><td class="num">{i+1}</td>'
                f'<td class="nw">{p["md"]}<span class="dim"> {p["dow"]} {p["hour"]}시</span></td>'
                f'<td><span class="chip">{TYPE_KO.get(p["type"], p["type"])}</span></td>'
                f'<td class="cap">{linked(p)}</td>'
                f'<td class="num strong">{p["er"]:.1f}%</td>'
                f'<td class="num">{p["reach"]:,}</td>'
                f'<td class="num">{p["inter"]}</td>'
                f'<td class="num">{(p["saved"]+p["shares"]) or "–"}</td></tr>')

    head = ('<thead><tr><th>#</th><th>게시일</th><th>포맷</th><th>내용</th>'
            '<th class="num">반응률</th><th class="num">도달<br>(본 사람 수)</th>'
            '<th class="num">반응</th><th class="num">저장+공유</th></tr></thead>')
    top_rows = "".join(rank_row(i, p) for i, p in enumerate(ranked[:TOP_VISIBLE]))
    rest_rows = "".join(rank_row(i + TOP_VISIBLE, p) for i, p in enumerate(ranked[TOP_VISIBLE:]))
    rank_html = f'<table>{head}<tbody>{top_rows}</tbody></table>'
    if rest_rows:
        rank_html += toggle(f"{TOP_VISIBLE+1}위 ~ {len(ranked)}위 보기",
                            f'<table>{head}<tbody>{rest_rows}</tbody></table>')

    # ---- 도달 / 저장 / 공유 랭킹
    def mini_rank(key, unit):
        rows = [p for p in posts if p[key]]
        rows.sort(key=lambda p: -p[key])
        rows = rows[:MINI_RANK]
        if not rows:
            return '<p class="empty">아직 기록이 없습니다</p>'
        h = ('<thead><tr><th>#</th><th>게시일</th><th>포맷</th><th>내용</th>'
             f'<th class="num">{esc(unit)}</th><th class="num">반응률</th></tr></thead>')
        b = "".join(
            f'<tr><td class="num">{i+1}</td><td class="nw">{p["md"]}</td>'
            f'<td><span class="chip">{TYPE_KO.get(p["type"], p["type"])}</span></td>'
            f'<td class="cap">{linked(p)}</td>'
            f'<td class="num strong">{p[key]:,}</td>'
            f'<td class="num">{p["er"]:.1f}%</td></tr>' for i, p in enumerate(rows))
        return f'<table>{h}<tbody>{b}</tbody></table>'

    other_ranks = (
        toggle(f"도달(본 사람 수) TOP {MINI_RANK} — 가장 널리 퍼진 게시물",
               mini_rank("reach", "도달"))
        + toggle(f"저장 TOP {MINI_RANK} — 다시 보려고 담아둔 게시물",
                 mini_rank("saved", "저장"))
        + toggle(f"공유 TOP {MINI_RANK} — 남에게 보낸 게시물",
                 mini_rank("shares", "공유")))

    # ---- 포맷별
    fmt_html = bars(fmt, lambda r: TYPE_KO.get(r["key"], r["key"]),
                    lambda r: f'· {r["n"]}개 · 도달 {r["reach"]:.0f}', emphasize_first=True)
    fmt_read = ""
    if len(fmt) >= 2 and fmt[1]["er"]:
        top, snd = fmt[0], fmt[1]
        fmt_read = (f'<p><b>{TYPE_KO.get(top["key"],top["key"])}가 '
                    f'{TYPE_KO.get(snd["key"],snd["key"])}보다 반응률 '
                    f'{top["er"]/snd["er"]:.1f}배 높습니다.</b> '
                    f'각각 게시물 {top["n"]}개 / {snd["n"]}개 기준입니다. '
                    f'업계 벤치마크도 캐러셀 {BENCH_FORMAT["CAROUSEL_ALBUM"]}% / '
                    f'이미지 {BENCH_FORMAT["IMAGE"]}%로 같은 방향입니다.</p>')

    # ---- 해시태그
    tag_html = bars(tag_stats, lambda r: "#" + r["key"],
                    lambda r: f'· {r["n"]}개', max_rows=15)
    tagged = [p for p in posts if p["tag_n"]]
    tag_read = (f'<p>해시태그가 있는 게시물은 {len(tagged)}개, 없는 게시물은 {n-len(tagged)}개입니다. '
                f'게시물당 평균 {avg(posts, lambda p: p["tag_n"]):.1f}개를 사용했습니다 '
                f'(인스타그램 허용 한도는 30개).</p>')

    def tag_bucket(p):
        k = p["tag_n"]
        return "0개" if k == 0 else ("1–3개" if k <= 3 else ("4–7개" if k <= 7 else "8개 이상"))
    tagn_html = bars(group_stats(posts, tag_bucket), lambda r: r["key"],
                     lambda r: f'· {r["n"]}개', narrow=True)

    def cap_bucket(p):
        k = p["cap_len"]
        return "~50자" if k <= 50 else ("51–150자" if k <= 150 else ("151–400자" if k <= 400 else "400자 초과"))
    capb_html = bars(group_stats(posts, cap_bucket), lambda r: r["key"],
                     lambda r: f'· {r["n"]}개', narrow=True)

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

    period = f'{posts[-1]["date"]} ~ {posts[0]["date"]}'
    ex_old, ex_bad = a.get("excluded_old", 0), a.get("excluded_bad", 0)
    ex_parts = []
    if ex_old:
        ex_parts.append(f"{ANALYSIS_MONTHS}개월 이전 {ex_old}개")
    if ex_bad:
        ex_parts.append(f"도달 집계 오류 {ex_bad}개")
    ex_note = (f'<div class="warn" style="margin-top:12px">제외된 게시물: {" · ".join(ex_parts)}. '
               f'오래된 게시물은 인스타그램이 도달을 과소 집계해 반응률이 비정상으로 나오므로 '
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
  <p class="sub">팔로워 반응률(참고용). 팔로워 수 대비 반응 비율로, 업계 평균과 비교할 수 있는 유일한 지표입니다.
     2026년 인스타그램 평균은 {BENCH_ER_FOLLOWERS}%입니다.</p>

  <h3>핵심 지표</h3>
  <p class="sub">기간 내 게시물 {n}개 기준</p>
  <div class="kpis">
    <div class="kpi"><div class="lbl">반응률</div><div class="v">{er_reach:.1f}%</div>
      <div class="cmp">본 사람 100명 중 {er_reach:.0f}명이 좋아요·댓글·저장·공유를 남김</div></div>
    <div class="kpi"><div class="lbl">팔로워 반응률(참고용)</div><div class="v">{er_fol:.2f}%</div>
      <div class="cmp {'good' if er_fol >= BENCH_ER_FOLLOWERS else 'bad'}">업계 평균 대비 {(er_fol-BENCH_ER_FOLLOWERS)/BENCH_ER_FOLLOWERS*100:+.0f}%</div></div>
    <div class="kpi"><div class="lbl">노출 범위</div><div class="v">{a_reach/F*100:.1f}%</div>
      <div class="cmp">게시물 하나가 평균 {a_reach:.0f}명에게 도달 · 팔로워 수 대비 비율</div></div>
    <div class="kpi"><div class="lbl">저장률</div><div class="v">{save_rate:.2f}%</div>
      <div class="cmp">합계 {tot_save}건 · 다시 보려고 담아둔 비율</div></div>
    <div class="kpi"><div class="lbl">공유율</div><div class="v">{share_rate:.2f}%</div>
      <div class="cmp">합계 {tot_share}건 · 남에게 보낸 비율</div></div>
  </div>

  <h3>분석</h3>
  <p class="sub">데이터가 갱신될 때마다 다시 쓰입니다</p>
  {ins_html}
  {chk_html}

  <h3>게시물 랭킹</h3>
  <p class="sub">반응률(본 사람 대비 반응) 순 · 상위 {RANK_LIMIT}위까지</p>
  {champ_html}
  {rank_html}
  <div style="margin-top:14px">{other_ranks}</div>

  <h3>포맷별 성과</h3>
  <p class="sub">반응률 — 본 사람 대비 반응 비율</p>
  {fmt_html}
  <div class="legend"><span><i class="sw"></i>가장 성과가 좋은 포맷</span>
    <span><i class="sw g"></i>비교군</span></div>
  <div class="reads">{fmt_read}</div>

  <h3>해시태그별 성과</h3>
  <p class="sub">{MIN_N}회 이상 사용한 해시태그만 · 반응률 순</p>
  {tag_html}
  <div class="reads">{tag_read}</div>

  <h3>해시태그 개수 · 캡션 길이</h3>
  <p class="sub">반응률</p>
  <div class="two">
    <div><div class="mini-t">해시태그 개수</div>{tagn_html}</div>
    <div><div class="mini-t">캡션 길이(해시태그 제외)</div>{capb_html}</div>
  </div>

  <h3>팔로워 구성</h3>
  <p class="sub">인스타그램이 추정한 값입니다</p>
  <div class="demos">{demo_html}</div>

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
.ins-box, .chk-box { border:1px solid var(--border); border-radius:10px;
  padding:14px 16px; margin-bottom:11px; }
.ins-box { border-left:3px solid var(--accent); background:#fbfcfe; }
.chk-box { border-left:3px solid #d9a520; background:#fffdf6; }
.ins-t, .chk-t { font-size:13px; font-weight:700; margin-bottom:9px; }
.ins-t { color:var(--accent); } .chk-t { color:#8a5a00; }
.ins-box p, .chk-box p { font-size:13.5px; line-height:1.7; margin:0 0 9px; }
.ins-box p:last-child, .chk-box p:last-child { margin-bottom:0; }
.ins-box b { color:var(--accent); } .chk-box b { color:#8a5a00; }
.champ { border:1px solid var(--border); border-left:3px solid var(--accent);
  border-radius:10px; padding:14px 16px; margin-bottom:14px; background:#fbfcfe; }
.champ-h { display:flex; align-items:baseline; gap:10px; flex-wrap:wrap; font-size:14px; }
.champ-er { color:var(--accent); font-weight:700; font-size:15px; }
.champ-cap { font-size:13px; color:var(--text2); margin:10px 0 8px; line-height:1.6; }
.champ-cap a { color:var(--text2); text-decoration:none; }
.champ-cap a:hover { color:var(--accent); text-decoration:underline; }
.champ-k { font-size:11.5px; color:var(--muted); font-variant-numeric:tabular-nums;
  line-height:1.6; padding-bottom:10px; border-bottom:1px solid var(--grid); }
.champ-note { font-size:13px; line-height:1.7; color:var(--text); margin:10px 0 0; }
"""


def build():
    cache = load("posts_cache.json", {})
    report = load("report_data.json", {"accounts": []})
    accounts = prep(cache, report)

    gen = report.get("generated_at", "")
    body = "".join(render_account(a) if len(a["posts"]) >= MIN_POSTS
                   else render_thin(a) for a in accounts) or \
        '<section class="acct"><p class="empty">분석할 데이터가 없습니다. instagram_api.py 를 먼저 실행하세요.</p></section>'

    total = sum(a["acc"].get("posts_total", 0) for a in accounts)
    anal = sum(len(a["posts"]) for a in accounts)

    html = f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<title>콘텐츠 분석</title>
<style>{CSS}</style></head><body><div class="wrap">
<div class="nav"><a href="./">일일 리포트</a><a class="on" href="./analysis.html">콘텐츠 분석</a></div>
<h1>콘텐츠 분석</h1>
<div class="updated">업데이트: {esc(gen)} · 전체 게시물 {total}개 중 인사이트 있는 {anal}개 분석</div>
{body}
<section class="acct">
  <h2 style="font-size:15px;margin:0 0 12px">이 분석의 한계</h2>
  <div class="limits">
    인사이트(도달·조회·저장)는 계정을 프로페셔널로 전환한 이후 게시물에만 존재합니다. 그 이전 게시물은 좋아요·댓글·해시태그만 남아 분석에서 제외됩니다.<br>
    "반응률"은 게시물을 본 사람 대비 좋아요·댓글·저장·공유의 비율입니다. 업계에서는 참여율(engagement rate)이라 부릅니다.<br>
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
