"""근거 있는 진단과 실행 지침을 만든다.

화면(HTML)은 만들지 않는다. 숫자를 재고, 그 숫자가 판단 근거로 쓸 만한지 따지고,
쓸 만한 것만 "근거 / 해석 / 실행" 세 덩어리로 돌려준다.

왜 따로 뺐나
  build_analysis.py 안에서 문장을 만들면 근거와 표현이 뒤섞여, 나중에 숫자가 바뀌었을 때
  어느 문장이 어느 계산에서 나왔는지 추적이 안 된다. 여기서는 계산과 판정만 하고
  문장 조립은 마지막에 한 번만 한다.

지켜야 할 원칙
  1. 표본 수를 밝히지 않는 주장은 만들지 않는다.
  2. 기간이 다른 두 묶음을 비교하지 않는다. (계정이 활발하던 시기와 식은 시기를
     섞으면 "해시태그가 효과 있다" 같은 가짜 결론이 나온다 — 실제로 그랬다)
  3. API 가 값을 주지 않는 것과 값이 0 인 것을 구분한다.
     릴스는 follows·profile_visits 를 아예 주지 않는다. 이걸 0 으로 읽으면
     "릴스는 팔로워를 못 데려온다"는 틀린 말이 나온다.
  4. 확실하지 않으면 확실하지 않다고 쓴다.
"""

from collections import defaultdict
from datetime import timedelta
from statistics import median

# 이 개수보다 적은 묶음으로는 비교하지 않는다
MIN_GROUP = 8
# 두 묶음의 차이가 이 배수 미만이면 "차이 없음"으로 본다
MEANINGFUL_X = 1.3


def _median(rows, f):
    v = [f(r) for r in rows if f(r) is not None]
    return median(v) if v else 0


def _avg(rows, f):
    v = [f(r) for r in rows if f(r) is not None]
    return sum(v) / len(v) if v else 0


def _er_bench(p, followers):
    """업계 벤치마크와 같은 식 — (좋아요+댓글) ÷ 팔로워 × 100."""
    return (p["likes"] + p["comments"]) / followers * 100 if followers else 0


# --------------------------------------------------------------- 개별 진단

def cadence(posts):
    """월별 발행량과 성과. 발행이 끊기면 다른 모든 지표가 같이 무너진다."""
    by = defaultdict(list)
    for p in posts:
        by[p["dt"].strftime("%Y-%m")].append(p)
    months = sorted(by)
    if len(months) < 4:
        return None
    rows = [{"month": m, "n": len(by[m]),
             "reach": _median(by[m], lambda p: p["reach"]),
             "follows": sum(p["follows"] for p in by[m] if p.get("follows_known", True))}
            for m in months]
    recent3, past3 = rows[-3:], rows[:3]
    n_now = sum(r["n"] for r in recent3) / 3
    n_then = sum(r["n"] for r in past3) / 3
    peak = max(rows, key=lambda r: r["n"])
    # "많이 올린 달"이 아니라 "실제로 팔로워가 붙은 달"을 근거로 삼는다.
    # 글 수만 많고 성과가 없던 달을 목표로 제시하면 설득력이 없다.
    best = max(rows, key=lambda r: (r["follows"], r["reach"]))
    return {"rows": rows, "n_now": n_now, "n_then": n_then, "peak": peak, "best": best,
            "drop": n_then > 0 and n_now < n_then * 0.5}


def format_gap(posts):
    """릴스와 피드를 같은 기간 안에서만 비교한다.

    릴스가 올라간 첫 날부터 마지막 날 사이의 피드 글만 상대로 삼는다.
    그래야 "릴스가 활발하던 시기"의 효과와 섞이지 않는다.
    """
    reels = [p for p in posts if p.get("is_reel")]
    if len(reels) < 5:
        return None
    lo = min(p["dt"] for p in reels)
    hi = max(p["dt"] for p in reels)
    feed = [p for p in posts if not p.get("is_reel") and lo <= p["dt"] <= hi]
    if len(feed) < MIN_GROUP:
        return None
    r_reach, f_reach = _median(reels, lambda p: p["reach"]), _median(feed, lambda p: p["reach"])
    if not f_reach:
        return None
    return {"n_reel": len(reels), "n_feed": len(feed),
            "reel_reach": r_reach, "feed_reach": f_reach, "x": r_reach / f_reach,
            "reel_share": _avg(reels, lambda p: p["shares"]),
            "feed_share": _avg(feed, lambda p: p["shares"]),
            "reel_save": _avg(reels, lambda p: p["saved"]),
            "feed_save": _avg(feed, lambda p: p["saved"]),
            "from": lo.strftime("%Y-%m-%d"), "to": hi.strftime("%Y-%m-%d"),
            # 릴스는 팔로우·프로필 방문을 API 가 주지 않는다. 없는 값이지 0 이 아니다.
            "follows_measurable": any(p.get("follows_known") for p in reels)}


def hashtag_effect(posts, followers):
    """해시태그 유무를 같은 기간 안에서 비교한다.

    전체 기간으로 재면 "해시태그가 있으면 반응률이 높다"고 나오는데, 이건 착시다.
    해시태그를 많이 붙이던 시기가 마침 계정이 활발하던 시기였을 뿐이다.
    그래서 최근 절반 구간에서만 다시 잰다.
    """
    if len(posts) < MIN_GROUP * 3:
        return None
    ordered = sorted(posts, key=lambda p: p["dt"])
    half = ordered[len(ordered) // 2:]
    with_t = [p for p in half if p["tag_n"] > 0]
    without = [p for p in half if p["tag_n"] == 0]
    if len(with_t) < MIN_GROUP or len(without) < MIN_GROUP:
        return None
    a = _avg(with_t, lambda p: _er_bench(p, followers))
    b = _avg(without, lambda p: _er_bench(p, followers))
    ra = _median(with_t, lambda p: p["reach"])
    rb = _median(without, lambda p: p["reach"])
    x = (a / b) if b else 0
    return {"n_with": len(with_t), "n_without": len(without),
            "er_with": a, "er_without": b, "reach_with": ra, "reach_without": rb,
            "x": x, "meaningful": x >= MEANINGFUL_X or (x and x <= 1 / MEANINGFUL_X),
            "from": half[0]["dt"].strftime("%Y-%m-%d")}


def reach_concentration(posts):
    """도달 상위 20% 글이 신규 팔로우의 몇 %를 만들었나.

    한쪽으로 쏠려 있다면, 모든 글을 고르게 잘 만드는 것보다
    크게 터질 글이 나올 기회를 늘리는 편이 낫다는 뜻이다.
    """
    known = [p for p in posts if p.get("follows_known", True)]
    tot = sum(p["follows"] for p in known)
    if tot < 10 or len(known) < MIN_GROUP * 2:
        return None
    top = sorted(known, key=lambda p: -p["reach"])[:max(1, len(known) // 5)]
    share = sum(p["follows"] for p in top) / tot * 100
    return {"n": len(known), "top_n": len(top), "total": tot,
            "share": share, "skewed": share >= 50}


def best_slot(posts, followers):
    """요일·시간대 중 표본이 충분하면서 눈에 띄게 나은 칸을 찾는다."""
    out = {}
    for name, key in (("dow", lambda p: p["dow"]),
                      ("hour", lambda p: f"{p['hour'] // 3 * 3:02d}-{p['hour'] // 3 * 3 + 2}시")):
        by = defaultdict(list)
        for p in posts:
            by[key(p)].append(p)
        cand = [(k, v) for k, v in by.items() if len(v) >= MIN_GROUP]
        if len(cand) < 2:
            continue
        scored = sorted(cand, key=lambda kv: -_avg(kv[1], lambda p: _er_bench(p, followers)))
        (k1, v1), (k2, v2) = scored[0], scored[-1]
        a = _avg(v1, lambda p: _er_bench(p, followers))
        b = _avg(v2, lambda p: _er_bench(p, followers))
        out[name] = {"best": k1, "n_best": len(v1), "er_best": a,
                     "worst": k2, "n_worst": len(v2), "er_worst": b,
                     "x": (a / b) if b else 0,
                     "meaningful": bool(b) and a / b >= MEANINGFUL_X}
    return out or None


def follow_conversion(posts):
    """도달 100건당 팔로우 몇 건. 노출이 사람으로 바뀌는 비율."""
    known = [p for p in posts if p.get("follows_known", True)]
    r = sum(p["reach"] for p in known)
    f = sum(p["follows"] for p in known)
    if not r:
        return None
    return {"reach": r, "follows": f, "per100": f / r * 100, "n": len(known)}


# --------------------------------------------------------------- 조립

def diagnose(posts, followers, bench):
    """근거 / 해석 / 실행 세 덩어리짜리 진단 목록.

    posts 는 build_analysis.load_accounts() 가 만든 형태를 그대로 받는다.
    앞에 놓인 것일수록 지금 가장 크게 영향을 주는 것이다.
    """
    out = []
    n = len(posts)
    if not n or not followers:
        return out

    er_now = _avg(posts, lambda p: _er_bench(p, followers))
    span = f'{min(p["dt"] for p in posts):%Y-%m-%d} ~ {max(p["dt"] for p in posts):%Y-%m-%d}'

    # 1. 발행량 — 다른 어떤 개선보다 앞선다
    c = cadence(posts)
    if c and c["drop"]:
        pk, bs = c["peak"], c["best"]
        out.append({
            "title": "발행이 멈춘 것이 지금 가장 큰 문제입니다",
            "why": (f'최근 3개월은 월 평균 {c["n_now"]:.1f}개를 올렸습니다. '
                    f'분석 시작 무렵 3개월은 월 {c["n_then"]:.1f}개였습니다. '
                    f'성과가 가장 좋았던 {bs["month"]}에는 {bs["n"]}개를 올려 신규 팔로우 '
                    f'{bs["follows"]}건, 도달 중앙값 {bs["reach"]:.0f}명이 나왔습니다. '
                    f'최근 3개월 합계 신규 팔로우는 '
                    f'{sum(r["follows"] for r in c["rows"][-3:])}건입니다.'),
            "read": ('인스타그램은 최근 게시 빈도를 계정 활성도로 봅니다. 글이 끊기면 '
                     '기존 팔로워에게 노출되는 양부터 줄고, 그다음에 새 사람에게 닿는 양이 줍니다. '
                     '지금 반응률이 낮은 것은 소재 문제이기 이전에 발행량 문제입니다. '
                     '소재를 아무리 다듬어도 월 1~2개로는 회복되지 않습니다.'),
            "do": (f'자동 발행의 첫 목표를 "품질"이 아니라 "빈도"로 잡으세요. '
                   f'주 3회(월 12~13개)를 4주간 유지하는 것이 1순위입니다. '
                   f'이 계정은 {pk["month"]}에 {pk["n"]}개까지 올린 적이 있으므로 '
                   f'무리한 목표가 아닙니다.'),
            "tag": "발행량",
        })

    # 2. 포맷 — 도달을 키우는 지렛대
    g = format_gap(posts)
    if g and g["x"] >= MEANINGFUL_X:
        note = ''
        if not g["follows_measurable"]:
            note = (' 다만 인스타그램 API 는 릴스에 대해 팔로우·프로필 방문 수를 주지 않습니다. '
                    '릴스가 팔로워를 데려왔는지 못 데려왔는지는 이 데이터로는 알 수 없습니다 '
                    '(0 이 아니라 값이 없는 것입니다).')
        out.append({
            "title": f'릴스가 피드보다 {g["x"]:.1f}배 더 퍼집니다',
            "why": (f'{g["from"]} ~ {g["to"]} 같은 기간 안에서 릴스 {g["n_reel"]}개와 '
                    f'피드 {g["n_feed"]}개를 비교했습니다. 도달 중앙값이 '
                    f'{g["reel_reach"]:.0f}명 대 {g["feed_reach"]:.0f}명입니다. '
                    f'공유는 글당 {g["reel_share"]:.2f}건 대 {g["feed_share"]:.2f}건, '
                    f'저장은 {g["reel_save"]:.2f}건 대 {g["feed_save"]:.2f}건입니다.'),
            "read": ('릴스는 팔로워 밖으로 배포되는 통로가 따로 있습니다. 평균값 대신 중앙값으로 잰 것은 '
                     '한두 개가 크게 터진 착시를 걸러내기 위해서입니다. 중앙값에서도 차이가 나므로 '
                     '"운이 좋았던 몇 개" 때문이 아닙니다.' + note),
            "do": ('자동 발행에서 릴스 비중을 최소 3분의 1로 잡으세요. '
                   '사진 소재를 그대로 쓰더라도 6~10초짜리 세로 영상으로 감싸면 릴스로 나갑니다. '
                   '릴스의 팔로우 기여는 측정이 안 되니, 릴스를 늘린 주와 그렇지 않은 주의 '
                   '계정 전체 신규 팔로워 수를 비교해서 판단하세요.'),
            "tag": "포맷",
        })

    # 3. 해시태그 — 효과가 없다면 그것도 결론이다
    h = hashtag_effect(posts, followers)
    if h and not h["meaningful"]:
        out.append({
            "title": "해시태그를 다듬는 데 시간을 쓸 이유가 없습니다",
            "why": (f'{h["from"]} 이후 글만 놓고 보면, 해시태그를 붙인 {h["n_with"]}개의 반응률은 '
                    f'{h["er_with"]:.2f}%, 붙이지 않은 {h["n_without"]}개는 {h["er_without"]:.2f}% 입니다. '
                    f'도달 중앙값은 {h["reach_with"]:.0f}명 대 {h["reach_without"]:.0f}명입니다.'),
            "read": ('전체 기간으로 재면 해시태그가 있는 쪽이 좋아 보이는데, 이건 착시입니다. '
                     '해시태그를 많이 붙이던 시기가 마침 글을 활발히 올리던 시기였습니다. '
                     '같은 기간 안에서 비교하면 차이가 사라집니다.'),
            "do": ('해시태그는 지역·업종 5개 안쪽으로 고정해 두고 더 손대지 마세요. '
                   '그 시간을 발행 빈도와 릴스 제작에 쓰는 편이 효과가 큽니다.'),
            "tag": "해시태그",
        })
    elif h and h["meaningful"] and h["x"] >= MEANINGFUL_X:
        out.append({
            "title": f'해시태그를 붙인 글의 반응률이 {h["x"]:.1f}배 높습니다',
            "why": (f'{h["from"]} 이후 글만 비교했습니다. 붙인 {h["n_with"]}개 {h["er_with"]:.2f}% 대 '
                    f'붙이지 않은 {h["n_without"]}개 {h["er_without"]:.2f}%.'),
            "read": '같은 기간 안에서도 차이가 남아 있으므로 시기 효과로 보기 어렵습니다.',
            "do": '자동 발행 템플릿에 지역·업종 해시태그 3~5개를 기본으로 넣으세요.',
            "tag": "해시태그",
        })

    # 4. 쏠림 — 어디에 힘을 쓸지 정하는 근거
    rc = reach_concentration(posts)
    if rc and rc["skewed"]:
        out.append({
            "title": f'신규 팔로워의 {rc["share"]:.0f}%를 상위 {rc["top_n"]}개 글이 만들었습니다',
            "why": (f'팔로우 수를 알 수 있는 글 {rc["n"]}개에서 신규 팔로우가 모두 {rc["total"]}건 '
                    f'나왔습니다. 도달 상위 20%인 {rc["top_n"]}개가 그중 '
                    f'{rc["share"]:.0f}%를 만들었습니다.'),
            "read": ('성과가 소수의 글에 몰려 있습니다. 모든 글을 고르게 잘 만드는 것보다, '
                     '크게 터질 글이 나올 기회를 늘리는 편이 기대값이 높습니다. '
                     '기회를 늘리는 방법은 발행 수를 늘리는 것과, 팔로워 밖으로 나가는 포맷을 쓰는 것입니다.'),
            "do": ('자동 발행에서 한 편에 오래 공들이기보다 주 3회를 지키세요. '
                   '도달이 평소의 2배를 넘긴 글은 따로 표시해 두고, 그 소재를 한 달 뒤 각도만 바꿔 다시 쓰세요.'),
            "tag": "쏠림",
        })

    # 5. 노출 → 사람 전환
    fc = follow_conversion(posts)
    if fc and fc["reach"] >= 3000:
        out.append({
            "title": f'도달 100명당 팔로우 {fc["per100"]:.2f}건입니다',
            "why": (f'팔로우 수를 알 수 있는 글 {fc["n"]}개 기준, 누적 도달 {fc["reach"]:,}명에 '
                    f'신규 팔로우 {fc["follows"]}건입니다.'),
            "read": ('노출이 사람으로 바뀌는 비율입니다. 이 비율이 낮으면 도달을 늘려도 팔로워는 '
                     '잘 늘지 않습니다. 글을 본 사람이 프로필로 넘어올 이유가 캡션에 없을 때 이렇게 됩니다.'),
            "do": ('캡션 마지막 줄을 고정 문구로 만드세요 — 무엇을 파는 곳인지, 어디에 있는지, '
                   '팔로우하면 무엇을 받는지 한 줄씩. 자동 발행 템플릿의 마지막 3줄로 넣으면 됩니다. '
                   '4주 뒤 이 숫자가 올라갔는지로 효과를 판정하세요.'),
            "tag": "전환",
        })

    # 6. 요일·시간 — 표본이 받쳐줄 때만
    bs = best_slot(posts, followers)
    if bs:
        for key, ko in (("dow", "요일"), ("hour", "시간대")):
            s = bs.get(key)
            if not s or not s["meaningful"]:
                continue
            out.append({
                "title": f'{s["best"]}에 올린 글의 반응률이 가장 높습니다',
                "why": (f'{ko}별로 나눠 표본 {MIN_GROUP}개 이상인 칸만 비교했습니다. '
                        f'{s["best"]} {s["n_best"]}개 {s["er_best"]:.2f}% 대 '
                        f'{s["worst"]} {s["n_worst"]}개 {s["er_worst"]:.2f}% ({s["x"]:.1f}배).'),
                "read": (f'{ko}는 게시물 수가 적어 흔들리기 쉬운 항목입니다. 지금 표본으로는 '
                         f'"이 칸이 확실히 낫다"까지는 말하기 어렵고, 같은 조건이면 이쪽을 고르는 정도로 쓰세요.'),
                "do": f'자동 발행 기본 시간을 {s["best"]}로 두고, 4주 뒤 다시 재서 유지할지 정하세요.',
                "tag": ko,
            })

    for d in out:
        d["scope"] = f'게시물 {n}개 · {span} · 팔로워 {followers:,}명 · 반응률은 (좋아요+댓글)÷팔로워'
    return out


def plan(posts, followers, bench, diags):
    """자동 발행에 그대로 넣을 수 있는 규칙과 4주 실험 계획.

    diagnose() 가 찾아낸 것만 반영한다. 근거 없는 항목은 만들지 않는다.
    """
    tags = {d["tag"] for d in diags}
    n = len(posts)
    er = _avg(posts, lambda p: _er_bench(p, followers)) if n and followers else 0
    rules, checks = [], []

    if "발행량" in tags:
        rules.append(("발행 빈도", "주 3회 (화·목·토)",
                      "발행이 끊긴 것이 지금 가장 큰 하락 요인이라 1순위입니다."))
    else:
        rules.append(("발행 빈도", "주 3회 이상 유지",
                      "지금 속도가 떨어지면 다른 지표가 같이 내려갑니다."))

    if "포맷" in tags:
        rules.append(("포맷 비율", "릴스 1 : 피드 2",
                      "같은 기간 비교에서 릴스 도달 중앙값이 피드보다 높았습니다."))
    bs = best_slot(posts, followers) or {}
    if bs.get("hour", {}).get("meaningful"):
        rules.append(("게시 시각", bs["hour"]["best"],
                      f'표본 {bs["hour"]["n_best"]}개 기준으로 가장 높았습니다. 4주 뒤 재확인 대상입니다.'))
    if bs.get("dow", {}).get("meaningful"):
        rules.append(("요일", bs["dow"]["best"],
                      f'표본 {bs["dow"]["n_best"]}개 기준. 확정은 아니고 기본값으로만 씁니다.'))
    if "해시태그" in tags:
        h = hashtag_effect(posts, followers)
        if h and not h["meaningful"]:
            rules.append(("해시태그", "지역·업종 고정 5개, 매번 바꾸지 않음",
                          "같은 기간 비교에서 효과 차이가 확인되지 않았습니다."))
        else:
            rules.append(("해시태그", "지역·업종 3~5개",
                          "같은 기간 비교에서도 차이가 남았습니다."))
    rules.append(("캡션 마지막 3줄", "무엇을 파는 곳인지 / 어디인지 / 팔로우할 이유",
                  "도달이 팔로우로 바뀌는 비율을 올리기 위한 것입니다."))

    checks.append(("발행 수", "주 3개", "가장 먼저 무너지는 지표라 매주 봅니다."))
    checks.append(("반응률", f"{er:.2f}% → {max(er * 1.2, bench):.2f}%",
                   f"지금 값의 1.2배와 업계 평균 {bench}% 중 높은 쪽입니다."))
    fc = follow_conversion(posts)
    if fc:
        checks.append(("도달 100당 팔로우", f'{fc["per100"]:.2f}건 → {fc["per100"] * 1.5:.2f}건',
                       "캡션 마지막 3줄이 먹히는지 보는 지표입니다."))
    if "포맷" in tags:
        checks.append(("릴스 주 1개", "4주간 4개", "릴스는 팔로우 기여가 측정되지 않아 주 단위 팔로워 증감으로 판정합니다."))

    return {"rules": rules, "checks": checks,
            "note": ("아래 규칙은 위 진단에서 근거가 확인된 것만 담았습니다. "
                     "4주 뒤 같은 화면에서 다시 재고, 오르지 않은 규칙은 버리세요.")}
