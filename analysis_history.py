"""콘텐츠 분석 수치를 주 단위로 적어 둔다.

왜 필요한가
  콘텐츠 분석 페이지는 매일 새로 그려지고 예전 화면은 남지 않는다. 그래서 "지난달보다
  나아졌나"를 볼 방법이 없다. 여기서 주 1회 스냅샷을 남겨 그 질문에 답한다.

왜 주 1회인가
  이 지표는 24개월 창의 누적 평균이라 하루로는 거의 움직이지 않는다.
  실제로 재보니 하루 간격 변화는 120회 중 118회가 0.005%p 미만이었다.
  한 달 간격이면 91회 중 57회가 움직였다. 주 1회가 "변화가 보이면서 기록이 안 넘치는"
  지점이다. 자동 발행 실험의 판정 주기(4주)와도 맞는다.

소급분에 대하여
  처음 실행할 때 과거 2년치를 계산해 채운다. 다만 이건 **지금 시점의 지표값**으로
  거슬러 계산한 것이라 그 주에 화면에 떠 있던 값과 완전히 같지는 않다.
  - 게시물별 좋아요·도달은 한 달만 지나면 거의 안 변하므로 오차가 작다.
  - 팔로워 수는 과거 값을 모른다 (history.json 이 37일치뿐). 현재 값으로 나눴다.
  그래서 소급분은 estimated=True 로 표시하고 화면에서 구분해 그린다. 추정을 실측인 척
  하지 않는다.

실행: 수집 직후 build_analysis.py 보다 먼저 부르면 된다.
"""

import json
import os
from datetime import datetime, timedelta, timezone
from statistics import median

DIR = os.path.dirname(os.path.abspath(__file__))
STORE = "analysis_history.json"

ANALYSIS_MONTHS = 24        # build_analysis.ANALYSIS_MONTHS 와 같아야 한다
BACKFILL_YEARS = 2          # 처음 한 번 소급해 채울 기간
MIN_FOLLOWERS = 100         # 이보다 적으면 팔로워 기준 지표를 내지 않는다


def _load(name, default):
    p = os.path.join(DIR, name)
    if not os.path.exists(p):
        return default
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def _save(name, data):
    with open(os.path.join(DIR, name), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


def week_start(d):
    """그 날짜가 속한 주의 월요일. 주 단위로 한 칸만 남기기 위한 열쇠."""
    return d - timedelta(days=d.weekday())


def _posts_of(cache, ig_id):
    slot = cache.get(str(ig_id or ""))
    if slot is None:
        slot = list(cache.values())[0] if len(cache) == 1 else {}
    if not isinstance(slot, dict):
        return []
    out = []
    for p in slot.values():
        ins = p.get("insights") or {}
        if not isinstance(ins.get("reach"), (int, float)) or ins["reach"] <= 0:
            continue
        try:
            dt = datetime.strptime(p["timestamp"], "%Y-%m-%dT%H:%M:%S%z") + timedelta(hours=9)
        except (ValueError, KeyError):
            continue
        out.append({
            "dt": dt,
            "reach": ins["reach"],
            "likes": p.get("like_count") or 0,
            "comments": p.get("comments_count") or 0,
            "saved": ins.get("saved") or 0,
            "shares": ins.get("shares") or 0,
            "follows": ins.get("follows") or 0,
            "follows_known": ins.get("follows") is not None,
            "is_reel": (p.get("media_product_type") or p.get("media_type")) == "REELS",
        })
    out.sort(key=lambda p: p["dt"])
    return out


def measure(posts, asof, followers):
    """asof 시점에 화면에 떠 있었을 값. 없으면 None."""
    lo = asof - timedelta(days=int(ANALYSIS_MONTHS * 30.44))
    v = [p for p in posts if lo <= p["dt"] <= asof]
    if len(v) < 10:
        return None
    n = len(v)
    tot_reach = sum(p["reach"] for p in v) or 1
    inter = sum(p["likes"] + p["comments"] + p["saved"] + p["shares"] for p in v)
    basic = sum(p["likes"] + p["comments"] for p in v)
    known = [p for p in v if p["follows_known"]]
    kr = sum(p["reach"] for p in known)
    kf = sum(p["follows"] for p in known)
    # 최근 4주에 몇 개 올렸나 — 발행 속도는 이 지표들을 앞에서 끌고 다닌다
    recent = [p for p in v if p["dt"] >= asof - timedelta(days=28)]
    row = {
        "date": asof.strftime("%Y-%m-%d"),
        "n": n,
        "posted_4w": len(recent),
        "reach_median": round(median(p["reach"] for p in v), 1),
        "er_reach": round(inter / tot_reach * 100, 3),
        "save_rate": round(sum(p["saved"] for p in v) / tot_reach * 100, 3),
        "share_rate": round(sum(p["shares"] for p in v) / tot_reach * 100, 3),
        "reels_4w": len([p for p in recent if p["is_reel"]]),
        "follow_per100": round(kf / kr * 100, 3) if kr else None,
    }
    # 팔로워로 나누는 값은 분모가 작으면 터진다. 낼 수 없으면 넣지 않는다.
    row["er_bench"] = (round(basic / n / followers * 100, 3)
                       if followers and followers >= MIN_FOLLOWERS else None)
    row["followers"] = followers
    return row


def backfill(posts, followers, weeks_back):
    """과거 주간 스냅샷을 거슬러 계산한다. 전부 estimated 표시."""
    if not posts:
        return []
    today = datetime.now(timezone.utc) + timedelta(hours=9)
    out = []
    for i in range(weeks_back, 0, -1):
        asof = week_start(today) - timedelta(weeks=i)
        if asof < posts[0]["dt"]:
            continue
        r = measure(posts, asof, followers)
        if r:
            r["estimated"] = True
            out.append(r)
    return out


def record(report_data=None, cache=None, today=None):
    """이번 주 스냅샷을 남긴다. 저장소가 비어 있으면 과거 2년치를 먼저 채운다.

    같은 주에 이미 기록이 있으면 덮어쓴다 (그 주의 최신 값이 남는다).
    """
    rep = report_data if report_data is not None else _load("report_data.json", {})
    cache = cache if cache is not None else _load("posts_cache.json", {})
    if not isinstance(cache, dict):
        return {}
    store = _load(STORE, {})
    if not isinstance(store, dict):
        store = {}
    now = today or (datetime.now(timezone.utc) + timedelta(hours=9))
    this_week = week_start(now)
    changed = {}

    for acc in (rep.get("accounts") or []):
        prof = acc.get("profile") or {}
        user = prof.get("username")
        if not user:
            continue
        posts = _posts_of(cache, prof.get("id"))
        followers = prof.get("followers_count") or 0
        rows = store.get(user) or []

        if not rows:
            rows = backfill(posts, followers, BACKFILL_YEARS * 52)

        cur = measure(posts, this_week, followers)
        if cur is None:
            # 이번 주 기준으로는 낼 수 없다 (글이 너무 적음). 과거분만 남긴다.
            if rows:
                store[user] = rows
            continue
        cur["estimated"] = False
        rows = [r for r in rows if r["date"] != cur["date"]]
        rows.append(cur)
        rows.sort(key=lambda r: r["date"])
        store[user] = rows
        changed[user] = len(rows)

    _save(STORE, store)
    return changed


if __name__ == "__main__":
    got = record()
    if not got:
        print("남길 스냅샷이 없습니다 (게시물이 부족하거나 데이터가 없음)")
    for u, k in got.items():
        print(f"@{u}: 주간 스냅샷 {k}개 (파일 {STORE})")
