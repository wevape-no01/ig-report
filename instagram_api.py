"""
인스타그램 Graph API에서 계정/게시물 인사이트를 가져온다. (여러 계정 지원)

설정값은 아래 순서로 찾는다:
  1) 환경변수 IG_ACCOUNTS  (GitHub Actions에서 Secrets로 주입)
  2) 같은 폴더의 accounts.json  (내 컴퓨터에서 테스트할 때)

형식 (JSON 배열):
[
  {"label": "위베이프", "ig_id": "1784...", "token": "EAGL..."},
  {"label": "재팬",     "ig_id": "1784...", "token": "EAGL..."}
]

토큰은 페이지 액세스 토큰이라 만료 기한이 없다.
"""

import json
import os
from datetime import datetime, timezone
from urllib.request import urlopen, Request
from urllib.parse import urlencode
from urllib.error import HTTPError

GRAPH_API_VERSION = "v21.0"
BASE_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ACCOUNTS_PATH = os.path.join(BASE_DIR, "accounts.json")

# 계정 레벨 인사이트 (total_value 방식)
ACCOUNT_METRICS = ["reach", "profile_views", "accounts_engaged", "total_interactions"]

# 게시물 인사이트. 미디어 타입에 따라 지원 여부가 달라서 실패하면 개별 재시도한다.
MEDIA_METRICS = ["reach", "saved", "shares", "total_interactions", "views"]


def _get(path, params):
    url = f"{BASE_URL}/{path}?{urlencode(params)}"
    req = Request(url, headers={"User-Agent": "ig-dashboard/1.0"})
    try:
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except HTTPError as e:
        raise RuntimeError(f"({e.code}) {path}: {e.read().decode()[:300]}") from None


def load_accounts():
    raw = os.environ.get("IG_ACCOUNTS", "").strip()
    if not raw and os.path.exists(ACCOUNTS_PATH):
        with open(ACCOUNTS_PATH, encoding="utf-8") as f:
            raw = f.read()
    if not raw:
        raise SystemExit(
            "설정이 없습니다. 환경변수 IG_ACCOUNTS 를 넣거나 accounts.json 을 만들어주세요.\n"
            "형식: [{\"label\":\"이름\",\"ig_id\":\"...\",\"token\":\"...\"}]"
        )
    accounts = json.loads(raw)
    if not isinstance(accounts, list) or not accounts:
        raise SystemExit("IG_ACCOUNTS 는 비어있지 않은 JSON 배열이어야 합니다.")
    return accounts


def fetch_profile(acc):
    return _get(acc["ig_id"], {
        "fields": "username,name,followers_count,follows_count,media_count",
        "access_token": acc["token"],
    })


def fetch_account_insights(acc):
    """계정 전체 인사이트. 지원 안 되는 메트릭은 조용히 건너뛴다."""
    result = {}
    for metric in ACCOUNT_METRICS:
        try:
            data = _get(f"{acc['ig_id']}/insights", {
                "metric": metric,
                "period": "day",
                "metric_type": "total_value",
                "access_token": acc["token"],
            })
            for m in data.get("data", []):
                val = m.get("total_value", {}).get("value")
                if val is None and m.get("values"):
                    val = m["values"][0].get("value")
                result[m["name"]] = val
        except RuntimeError:
            continue
    return result


def fetch_recent_media(acc, limit=12):
    return _get(f"{acc['ig_id']}/media", {
        "fields": "id,caption,media_type,media_product_type,timestamp,permalink,"
                  "like_count,comments_count,thumbnail_url,media_url",
        "limit": limit,
        "access_token": acc["token"],
    }).get("data", [])


def fetch_media_insights(acc, media_id):
    """메트릭을 한꺼번에 요청하면 하나만 미지원이어도 전체가 실패하므로,
    실패 시 메트릭을 하나씩 다시 시도한다."""
    try:
        data = _get(f"{media_id}/insights", {
            "metric": ",".join(MEDIA_METRICS), "access_token": acc["token"],
        })
        return {m["name"]: m["values"][0]["value"] for m in data.get("data", [])}
    except RuntimeError:
        pass

    result = {}
    for metric in MEDIA_METRICS:
        try:
            data = _get(f"{media_id}/insights", {
                "metric": metric, "access_token": acc["token"],
            })
            for m in data.get("data", []):
                result[m["name"]] = m["values"][0]["value"]
        except RuntimeError:
            continue
    return result


def collect_account(acc):
    profile = fetch_profile(acc)
    posts = []
    for item in fetch_recent_media(acc):
        posts.append({
            "id": item["id"],
            "caption": (item.get("caption") or "")[:100],
            "media_type": item.get("media_type"),
            "timestamp": item.get("timestamp"),
            "permalink": item.get("permalink"),
            "like_count": item.get("like_count", 0),
            "comments_count": item.get("comments_count", 0),
            "insights": fetch_media_insights(acc, item["id"]),
        })
    return {
        "label": acc.get("label") or profile.get("username"),
        "profile": profile,
        "account_insights": fetch_account_insights(acc),
        "posts": posts,
    }


def collect_report():
    accounts = load_accounts()
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "accounts": [collect_account(a) for a in accounts],
    }


def update_history(report):
    """API가 과거 팔로워 수를 주지 않으므로, 실행할 때마다 그날 값을 누적 저장한다."""
    path = os.path.join(BASE_DIR, "history.json")
    today = datetime.now(timezone.utc).date().isoformat()

    history = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            history = json.load(f)
    if not isinstance(history, dict):
        history = {}   # 예전 리스트 형식이면 새로 시작

    for acc in report["accounts"]:
        key = acc["profile"].get("username", acc["label"])
        rows = history.setdefault(key, [])
        followers = acc["profile"].get("followers_count", 0)
        if rows and rows[-1]["date"] == today:
            rows[-1]["followers_count"] = followers
        else:
            rows.append({"date": today, "followers_count": followers})

    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    return history


if __name__ == "__main__":
    report = collect_report()
    with open(os.path.join(BASE_DIR, "report_data.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    hist = update_history(report)
    for acc in report["accounts"]:
        u = acc["profile"].get("username")
        print(f"@{u}: 팔로워 {acc['profile'].get('followers_count')}명, "
              f"게시물 {len(acc['posts'])}개 수집, 기록 {len(hist.get(u, []))}일치")
