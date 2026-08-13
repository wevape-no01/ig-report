"""
스레드(Threads) API 수집기

인스타그램과 완전히 별개 API다.
  - 호스트: graph.threads.net
  - 토큰: 60일 만료 → refresh_access_token 으로 갱신해야 한다
  - "도달"이 없다. 조회수(views)만 있다.

동작:
  1) 토큰이 마지막 갱신 후 REFRESH_EVERY_DAYS 지났으면 갱신하고
     GitHub 저장소 시크릿(THREADS_TOKEN)에 새 토큰을 다시 저장한다
  2) 프로필 + 전체 게시물 + 게시물별 인사이트 수집 (캐시 재사용)
  3) 계정 인사이트: 조회수 일별 시계열, 좋아요/답글/리포스트/인용 합계,
     링크 클릭수, 팔로워 구성

설정(환경변수):
  THREADS_TOKEN    스레드 장기 액세스 토큰 (필수)
  GH_PAT           저장소 시크릿 쓰기 권한이 있는 GitHub 토큰 (자동 갱신용, 선택)
  GITHUB_REPOSITORY  "소유자/저장소" — Actions 가 자동으로 넣어준다

출력:
  threads_cache.json    전체 게시물 + 인사이트
  threads_report.json   프로필 + 최근 게시물 + 계정 인사이트
  threads_history.json  날짜별 스냅샷 (조회수·팔로워 추이)
  threads_token_meta.json  마지막 갱신 날짜 (토큰 값은 절대 저장하지 않는다)
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from urllib.request import urlopen, Request
from urllib.parse import urlencode
from urllib.error import HTTPError

BASE = "https://graph.threads.net/v1.0"
AUTH = "https://graph.threads.net"          # 토큰 갱신은 버전 경로가 없다
DIR = os.path.dirname(os.path.abspath(__file__))

REFRESH_DAYS = 30          # 이 기간 내 게시물은 매번 인사이트 재조회
REPORT_POSTS = 12          # 리포트에 최소로 실어보낼 게시물 수
REPORT_DAYS = 31           # "최근 한 달" 토글 기간
REFRESH_EVERY_DAYS = 7     # 토큰 갱신 주기 (만료는 60일이므로 넉넉하다)
BACKFILL_DAYS = 29         # 조회수 시계열을 채울 기간

MEDIA_METRICS = ["views", "likes", "replies", "reposts", "quotes", "shares"]
TOTAL_METRICS = ["likes", "replies", "reposts", "quotes"]
DEMO_BREAKDOWNS = ["age", "gender", "city", "country"]

P = lambda *a: print(*a, flush=True)


class ApiError(RuntimeError):
    def __init__(self, code, body):
        super().__init__(f"({code}) {body}")
        self.code, self.body = code, body


def request(url, tries=3):
    last = None
    for _ in range(tries):
        try:
            with urlopen(Request(url, headers={"User-Agent": "ig-report/2.0"}), timeout=40) as r:
                return json.loads(r.read().decode())
        except HTTPError as e:
            body = e.read().decode()[:300]
            if 400 <= e.code < 500:
                raise ApiError(e.code, body)
            last = ApiError(e.code, body)
        except Exception as e:
            last = ApiError(0, str(e)[:200])
    raise last


def get(path, params):
    return request(f"{BASE}/{path}?{urlencode(params)}")


def load_json(name, default):
    p = os.path.join(DIR, name)
    if not os.path.exists(p):
        return default
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def save_json(name, obj):
    with open(os.path.join(DIR, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


# ---------------------------------------------------------------- 토큰 갱신

def gh_api(method, path, pat, payload=None):
    import urllib.request
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        f"https://api.github.com{path}", data=data, method=method,
        headers={"Authorization": f"Bearer {pat}",
                 "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28",
                 "Content-Type": "application/json",
                 "User-Agent": "ig-report/2.0"})
    with urllib.request.urlopen(req, timeout=40) as r:
        raw = r.read().decode()
        return json.loads(raw) if raw.strip() else {}


def write_repo_secret(name, value, repo, pat):
    """GitHub 저장소 시크릿을 갱신한다. 값은 libsodium sealed box 로 암호화해야 한다."""
    from base64 import b64encode, b64decode
    from nacl import encoding, public
    key = gh_api("GET", f"/repos/{repo}/actions/secrets/public-key", pat)
    box = public.SealedBox(public.PublicKey(key["key"].encode(), encoding.Base64Encoder()))
    enc = b64encode(box.encrypt(value.encode())).decode()
    gh_api("PUT", f"/repos/{repo}/actions/secrets/{name}", pat,
           {"encrypted_value": enc, "key_id": key["key_id"]})


def check_pat():
    """GH_PAT 가 시크릿 쓰기 권한을 실제로 갖고 있는지 미리 확인한다.
    읽기 요청 한 번이라 부담이 없고, 갱신일이 와서야 문제를 발견하는 걸 막아준다."""
    repo, pat = os.environ.get("GITHUB_REPOSITORY"), os.environ.get("GH_PAT")
    if not pat:
        P("GH_PAT 없음 — 토큰 자동 갱신이 비활성 상태입니다 (60일 뒤 스레드가 멈춥니다).")
        return
    if not repo:
        P("GITHUB_REPOSITORY 없음 — 자동 갱신을 건너뜁니다.")
        return
    try:
        gh_api("GET", f"/repos/{repo}/actions/secrets/public-key", pat)
        P("GH_PAT 확인 완료 — 시크릿 쓰기 권한 정상.")
    except Exception as e:                            # noqa: BLE001
        P(f"GH_PAT 확인 실패: {type(e).__name__} {e}")
        P("→ 토큰 만료 또는 권한 부족. Secrets: Read and write 인지, "
          "대상 저장소가 ig-report 인지 확인하세요.")


def maybe_refresh_token(token):
    """필요하면 토큰을 갱신하고 새 토큰을 반환한다. 실패해도 기존 토큰으로 계속 진행한다."""
    meta = load_json("threads_token_meta.json", {})
    today = datetime.now(timezone.utc).date()
    last = meta.get("refreshed_on")
    if last:
        try:
            if (today - datetime.strptime(last, "%Y-%m-%d").date()).days < REFRESH_EVERY_DAYS:
                P(f"토큰 갱신 건너뜀 (마지막 갱신 {last})")
                return token
        except ValueError:
            pass

    try:
        d = request(f"{AUTH}/refresh_access_token?" + urlencode(
            {"grant_type": "th_refresh_token", "access_token": token}))
    except ApiError as e:
        P(f"토큰 갱신 실패 (기존 토큰으로 계속 진행): {e}")
        return token

    new = d.get("access_token")
    if not new:
        P("토큰 갱신 응답에 access_token 이 없음 — 기존 토큰 유지")
        return token
    days = int(d.get("expires_in", 0)) // 86400

    repo, pat = os.environ.get("GITHUB_REPOSITORY"), os.environ.get("GH_PAT")
    if repo and pat:
        try:
            write_repo_secret("THREADS_TOKEN", new, repo, pat)
            meta["refreshed_on"] = today.isoformat()
            meta["valid_days"] = days
            save_json("threads_token_meta.json", meta)
            P(f"토큰 갱신 완료 — 앞으로 {days}일 유효. 시크릿에 저장했습니다.")
        except Exception as e:                       # noqa: BLE001
            P(f"새 토큰을 시크릿에 저장하지 못했습니다: {type(e).__name__} {e}")
            P("→ GH_PAT 권한(Secrets: Read and write)을 확인하세요.")
    else:
        P(f"토큰을 갱신했지만(유효 {days}일) 저장할 곳이 없습니다 "
          f"(GH_PAT / GITHUB_REPOSITORY 미설정). 이번 실행에만 사용합니다.")
    return new


# ---------------------------------------------------------------- 수집

def fetch_profile(token):
    return get("me", {"fields": "id,username,name,threads_profile_picture_url,threads_biography",
                      "access_token": token})


def fetch_all_media(token):
    """모든 스레드 게시물을 페이지 넘기며 수집."""
    out = []
    base = {"fields": "id,media_product_type,media_type,permalink,text,timestamp,"
                      "shortcode,is_quote_post,has_replies,reply_audience",
            "limit": 100, "access_token": token}
    after, guard = None, 0
    while guard < 30:
        params = dict(base)
        if after:
            params["after"] = after
        d = get("me/threads", params)
        rows = d.get("data", [])
        out.extend(rows)
        paging = d.get("paging", {})
        if not rows or not paging.get("next"):
            break
        after = (paging.get("cursors") or {}).get("after")
        if not after:
            break
        guard += 1
    return out


def fetch_media_insights(token, media_id):
    """반환: (dict, supported). 리포스트 등은 빈 배열이 온다."""
    try:
        d = get(f"{media_id}/insights",
                {"metric": ",".join(MEDIA_METRICS), "access_token": token})
    except ApiError:
        return {}, False
    rows = d.get("data") or []
    out = {}
    for m in rows:
        vals = m.get("values") or []
        if vals:
            out[m["name"]] = vals[0].get("value")
        elif m.get("total_value"):
            out[m["name"]] = m["total_value"].get("value")
    return out, bool(out)


def fetch_views_series(token, days=BACKFILL_DAYS):
    """계정 조회수 일별 시계열. 반환: [(날짜, 값), ...]"""
    until = int(time.time())
    since = until - days * 86400
    try:
        d = get("me/threads_insights", {"metric": "views", "since": since,
                                        "until": until, "access_token": token})
    except ApiError as e:
        P(f"          조회수 시계열 실패: {e}")
        return []
    rows = d.get("data") or []
    if not rows:
        return []
    out = []
    for v in (rows[0].get("values") or []):
        et = v.get("end_time", "")
        if len(et) >= 10:
            out.append((et[:10], v.get("value")))
    if not out and rows[0].get("total_value"):        # 시계열 미지원으로 떨어질 때
        today = datetime.now(timezone.utc).date().isoformat()
        out.append((today, rows[0]["total_value"].get("value")))
    return out


def fetch_account_totals(token):
    """좋아요/답글/리포스트/인용 누적 + 팔로워 수 + 링크 클릭수."""
    out = {}
    for m in TOTAL_METRICS + ["followers_count"]:
        try:
            d = get("me/threads_insights", {"metric": m, "access_token": token})
            for row in d.get("data", []):
                tv = row.get("total_value") or {}
                if "value" in tv:
                    out[row["name"]] = tv["value"]
                else:
                    vals = row.get("values") or []
                    if vals:
                        out[row["name"]] = vals[-1].get("value")
        except ApiError:
            continue

    try:                                              # 링크 클릭수 (URL 별)
        d = get("me/threads_insights", {"metric": "clicks", "access_token": token})
        clicks = []
        for row in d.get("data", []):
            for lt in (row.get("total_value") or {}).get("breakdowns", []):
                for r in lt.get("results", []):
                    clicks.append({"url": (r.get("dimension_values") or [""])[0],
                                   "value": r.get("value")})
        if clicks:
            out["clicks"] = sorted(clicks, key=lambda c: -(c["value"] or 0))[:10]
    except ApiError:
        pass
    return out


def fetch_demographics(token):
    out = {}
    for bd in DEMO_BREAKDOWNS:
        try:
            d = get("me/threads_insights", {"metric": "follower_demographics",
                                            "breakdown": bd, "access_token": token})
            rows = d["data"][0]["total_value"]["breakdowns"][0]["results"]
            out[bd] = {(r["dimension_values"] or ["?"])[0]: r["value"] for r in rows}
        except (ApiError, KeyError, IndexError):
            continue        # 팔로워 100명 미만이면 아예 안 나온다
    return out


# ---------------------------------------------------------------- 메인

def collect(token, cache):
    profile = fetch_profile(token)
    uname = profile.get("username", "?")

    media = fetch_all_media(token)
    cutoff = datetime.now(timezone.utc) - timedelta(days=REFRESH_DAYS)
    fresh = reused = no_ins = 0

    for item in media:
        mid = item["id"]
        old = cache.get(mid, {})
        ts = item.get("timestamp", "")
        try:
            dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S%z")
        except ValueError:
            dt = datetime.now(timezone.utc)

        rec = {
            "id": mid,
            "text": item.get("text") or "",
            "media_type": item.get("media_type"),
            "media_product_type": item.get("media_product_type"),
            "is_quote_post": item.get("is_quote_post"),
            "timestamp": ts,
            "permalink": item.get("permalink"),
        }
        if old.get("no_insights"):
            rec.update(insights={}, no_insights=True)
            no_ins += 1
        elif dt >= cutoff or "insights" not in old:
            ins, ok = fetch_media_insights(token, mid)
            rec["insights"] = ins
            if ok:
                fresh += 1
            else:
                rec["no_insights"] = True
                no_ins += 1
        else:
            rec["insights"] = old.get("insights", {})
            reused += 1
        cache[mid] = rec

    posts = sorted(cache.values(), key=lambda p: p.get("timestamp", ""), reverse=True)
    with_ins = [p for p in posts if (p.get("insights") or {}).get("views") is not None]
    P(f"@{uname}: 스레드 {len(posts)}개 (신규조회 {fresh} · 캐시재사용 {reused} · "
      f"인사이트없음 {no_ins}) → 분석가능 {len(with_ins)}개")

    cut = (datetime.now(timezone.utc) - timedelta(days=REPORT_DAYS)).isoformat()
    recent = [p for p in posts if (p.get("timestamp") or "") >= cut]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "profile": profile,
        "account_insights": fetch_account_totals(token),
        "demographics": fetch_demographics(token),
        "posts_total": len(posts),
        "posts_analyzable": len(with_ins),
        "posts_recent_days": REPORT_DAYS,
        "posts_recent_count": len(recent),
        "posts": posts[:max(REPORT_POSTS, len(recent))],
    }


def update_history(token, report):
    """조회수는 29일치 시계열을 주므로 과거까지 채운다. 팔로워 수는 오늘 값만 있다."""
    hist = load_json("threads_history.json", [])
    if not isinstance(hist, list):
        hist = []
    rows = {r["date"]: r for r in hist if isinstance(r, dict) and r.get("date")}

    for date, val in fetch_views_series(token):
        rows.setdefault(date, {"date": date})["views"] = val

    today = datetime.now(timezone.utc).date().isoformat()
    ins = report["account_insights"]
    t = rows.setdefault(today, {"date": today})
    t["followers_count"] = ins.get("followers_count")
    for m in TOTAL_METRICS:
        if ins.get(m) is not None:
            t[m] = ins[m]

    ordered = [rows[d] for d in sorted(rows)]
    save_json("threads_history.json", ordered)
    P(f"          기록 {len(ordered)}일")
    return ordered


if __name__ == "__main__":
    tok = os.environ.get("THREADS_TOKEN", "").strip()
    if not tok:
        sys.exit("설정 없음: 환경변수 THREADS_TOKEN 이 필요합니다.")

    check_pat()
    tok = maybe_refresh_token(tok)

    cache = load_json("threads_cache.json", {})
    report = collect(tok, cache)
    save_json("threads_cache.json", cache)
    save_json("threads_report.json", report)
    update_history(tok, report)
