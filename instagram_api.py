"""
인스타그램 Graph API 수집기 (여러 계정 지원 + 전체 백필 + 캐싱)

동작:
  1) 계정의 모든 게시물 목록을 페이지 넘기며 가져온다 (캡션은 자르지 않음)
  2) 게시물별 인사이트는 posts_cache.json 에 저장해두고 재사용한다
     - 최근 REFRESH_DAYS 일 이내 게시물만 매번 다시 조회 (오래된 값은 거의 안 변함)
     - 인사이트가 아예 없는 게시물(프로 전환 이전)은 표시해두고 다시 시도하지 않음
  3) 계정 인사이트, 팔로워/비팔로워 도달, 팔로워 인구통계를 함께 수집

설정: 환경변수 IG_ACCOUNTS 또는 같은 폴더의 accounts.json
  [{"label":"이름","ig_id":"1784...","token":"EAGL..."}]

출력:
  posts_cache.json  전체 게시물 + 인사이트 (분석용)
  report_data.json  최근 게시물 요약 (일일 리포트용)
  history.json      날짜별 스냅샷 (팔로워 추이, 신규 유입 추이)
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from urllib.request import urlopen, Request
from urllib.parse import urlencode
from urllib.error import HTTPError

V = "v21.0"
BASE = f"https://graph.facebook.com/{V}"
DIR = os.path.dirname(os.path.abspath(__file__))

REFRESH_DAYS = 30      # 이 기간 내 게시물은 매 실행마다 인사이트 재조회
REPORT_POSTS = 12      # 일일 리포트에 보여줄 최근 게시물 수

MEDIA_METRICS = ["reach", "views", "saved", "shares", "total_interactions",
                 "profile_visits", "follows"]
ACCOUNT_METRICS = ["reach", "views", "profile_views", "accounts_engaged",
                   "total_interactions"]
DEMO_BREAKDOWNS = ["age", "gender", "city", "country"]

P = lambda *a: print(*a, flush=True)


def get(path, params, tries=3):
    url = f"{BASE}/{path}?{urlencode(params)}"
    last = None
    for _ in range(tries):
        try:
            with urlopen(Request(url, headers={"User-Agent": "ig-report/2.0"}), timeout=40) as r:
                return json.loads(r.read().decode())
        except HTTPError as e:
            body = e.read().decode()[:300]
            # 4xx 는 재시도해도 같으므로 즉시 반환
            if 400 <= e.code < 500:
                raise ApiError(e.code, body)
            last = ApiError(e.code, body)
        except Exception as e:                      # 네트워크 일시 오류
            last = ApiError(0, str(e)[:200])
    raise last


class ApiError(RuntimeError):
    def __init__(self, code, body):
        super().__init__(f"({code}) {body}")
        self.code, self.body = code, body


def load_accounts():
    raw = os.environ.get("IG_ACCOUNTS", "").strip()
    path = os.path.join(DIR, "accounts.json")
    if not raw and os.path.exists(path):
        raw = open(path, encoding="utf-8").read()
    if not raw:
        sys.exit("설정 없음: 환경변수 IG_ACCOUNTS 또는 accounts.json 이 필요합니다.")
    accounts = json.loads(raw)
    if not isinstance(accounts, list) or not accounts:
        sys.exit("IG_ACCOUNTS 는 비어있지 않은 JSON 배열이어야 합니다.")
    return accounts


def load_json(name, default):
    path = os.path.join(DIR, name)
    if not os.path.exists(path):
        return default
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def save_json(name, obj):
    with open(os.path.join(DIR, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


# ---------------------------------------------------------------- 수집

def fetch_all_media(acc):
    """모든 게시물을 페이지 넘기며 수집. 캡션은 자르지 않는다.
    paging.next URL 을 그대로 쓰면 API 버전이 달라 깨지므로 after 커서만 이어받는다."""
    out = []
    base = {
        "fields": "id,caption,media_type,media_product_type,timestamp,permalink,"
                  "like_count,comments_count,thumbnail_url,media_url",
        "limit": 100, "access_token": acc["token"],
    }
    after, guard = None, 0
    while guard < 30:
        params = dict(base)
        if after:
            params["after"] = after
        data = get(f"{acc['ig_id']}/media", params)
        rows = data.get("data", [])
        out.extend(rows)
        paging = data.get("paging", {})
        if not rows or not paging.get("next"):
            break
        after = paging.get("cursors", {}).get("after")
        if not after:
            break
        guard += 1
    return out


def fetch_media_insights(acc, media_id):
    """묶음 요청 실패 시 메트릭을 하나씩 시도. (지원 여부가 미디어 타입마다 다름)
    반환: (dict, supported)  supported=False 면 이 게시물은 인사이트 자체가 없음."""
    try:
        d = get(f"{media_id}/insights",
                {"metric": ",".join(MEDIA_METRICS), "access_token": acc["token"]})
        return {m["name"]: m["values"][0]["value"] for m in d.get("data", [])}, True
    except ApiError:
        pass

    res = {}
    for m in MEDIA_METRICS:
        try:
            d = get(f"{media_id}/insights", {"metric": m, "access_token": acc["token"]})
            for row in d.get("data", []):
                res[row["name"]] = row["values"][0]["value"]
        except ApiError:
            continue
    return res, bool(res)


def fetch_account_insights(acc):
    out = {}
    for m in ACCOUNT_METRICS:
        try:
            d = get(f"{acc['ig_id']}/insights", {
                "metric": m, "period": "day", "metric_type": "total_value",
                "access_token": acc["token"]})
            for row in d.get("data", []):
                out[row["name"]] = row.get("total_value", {}).get("value")
        except ApiError:
            continue

    # 팔로워 / 비팔로워 분리 — 신규 유입(해시태그·탐색탭·공유) 대리 지표
    for m in ("reach", "views"):
        try:
            d = get(f"{acc['ig_id']}/insights", {
                "metric": m, "period": "day", "metric_type": "total_value",
                "breakdown": "follow_type", "access_token": acc["token"]})
            for row in d.get("data", []):
                for bd in row.get("total_value", {}).get("breakdowns", []):
                    for r in bd.get("results", []):
                        key = f"{m}_{r['dimension_values'][0].lower()}"
                        out[key] = r["value"]
        except ApiError:
            continue
    return out


def fetch_demographics(acc):
    out = {}
    for bd in DEMO_BREAKDOWNS:
        try:
            d = get(f"{acc['ig_id']}/insights", {
                "metric": "follower_demographics", "period": "lifetime",
                "metric_type": "total_value", "timeframe": "this_month",
                "breakdown": bd, "access_token": acc["token"]})
            rows = d["data"][0]["total_value"]["breakdowns"][0]["results"]
            out[bd] = {r["dimension_values"][0]: r["value"] for r in rows}
        except (ApiError, KeyError, IndexError):
            continue
    return out


# ---------------------------------------------------------------- 메인

def collect(acc, cache):
    ig = acc["ig_id"]
    slot = cache.setdefault(ig, {})
    profile = get(ig, {
        "fields": "username,name,followers_count,follows_count,media_count",
        "access_token": acc["token"]})
    uname = profile.get("username", ig)

    media = fetch_all_media(acc)
    cutoff = datetime.now(timezone.utc) - timedelta(days=REFRESH_DAYS)
    fresh = reused = skipped = no_ins = 0

    for item in media:
        mid = item["id"]
        old = slot.get(mid, {})
        ts = item.get("timestamp", "")
        try:
            dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S%z")
        except ValueError:
            dt = datetime.now(timezone.utc)

        rec = {
            "id": mid,
            "caption": item.get("caption") or "",          # 자르지 않음
            "media_type": item.get("media_type"),
            "media_product_type": item.get("media_product_type"),
            "timestamp": ts,
            "permalink": item.get("permalink"),
            "like_count": item.get("like_count", 0),
            "comments_count": item.get("comments_count", 0),
        }

        if old.get("no_insights"):                          # 프로 전환 이전 → 재시도 안 함
            rec.update(insights={}, no_insights=True)
            no_ins += 1
        elif dt >= cutoff or "insights" not in old:         # 최신이거나 아직 안 받은 것
            ins, ok = fetch_media_insights(acc, mid)
            rec["insights"] = ins
            if not ok:
                rec["no_insights"] = True
                no_ins += 1
            else:
                fresh += 1
        else:                                               # 오래된 것 → 캐시 재사용
            rec["insights"] = old.get("insights", {})
            reused += 1
            skipped += 1

        slot[mid] = rec

    posts = sorted(slot.values(), key=lambda p: p.get("timestamp", ""), reverse=True)
    with_ins = [p for p in posts if p.get("insights", {}).get("reach") is not None]
    P(f"@{uname}: 게시물 {len(posts)}개 (신규조회 {fresh} · 캐시재사용 {reused} · "
      f"인사이트없음 {no_ins}) → 분석가능 {len(with_ins)}개")
    if with_ins:
        P(f"          인사이트 수집 범위: {with_ins[-1]['timestamp'][:10]} ~ {with_ins[0]['timestamp'][:10]}")

    return {
        "label": acc.get("label") or uname,
        "profile": profile,
        "account_insights": fetch_account_insights(acc),
        "demographics": fetch_demographics(acc),
        "posts_total": len(posts),
        "posts_analyzable": len(with_ins),
        "posts": posts[:REPORT_POSTS],
    }


def update_history(report):
    """API가 과거 값을 주지 않으므로 매 실행마다 그날의 스냅샷을 누적한다."""
    hist = load_json("history.json", {})
    if not isinstance(hist, dict):
        hist = {}
    today = datetime.now(timezone.utc).date().isoformat()

    for acc in report["accounts"]:
        u = acc["profile"].get("username", acc["label"])
        ins = acc["account_insights"]
        row = {
            "date": today,
            "followers_count": acc["profile"].get("followers_count", 0),
            "reach": ins.get("reach"),
            "reach_non_follower": ins.get("reach_non_follower"),
            "views": ins.get("views"),
            "views_non_follower": ins.get("views_non_follower"),
        }
        rows = hist.setdefault(u, [])
        if rows and rows[-1]["date"] == today:
            rows[-1] = row
        else:
            rows.append(row)
    save_json("history.json", hist)
    return hist


if __name__ == "__main__":
    accounts = load_accounts()
    cache = load_json("posts_cache.json", {})
    report = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "accounts": [collect(a, cache) for a in accounts]}

    save_json("posts_cache.json", cache)
    save_json("report_data.json", report)
    hist = update_history(report)
    P("기록 일수: " + ", ".join(f"{k} {len(v)}일" for k, v in hist.items()))
