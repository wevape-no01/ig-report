"""
주간 요약을 "숫자"로만 계산한다. 화면(HTML)과 GitHub 이슈 본문이 이 값을 같이 쓴다.

기간: 어제까지 7일 = 이번 주. 그 앞 7일 = 지난 주.
인스타그램은 어제까지의 값만 확정해서 주기 때문에 오늘은 넣지 않는다.

여기서는 API 를 부르지 않는다. 이미 저장된 json 만 읽는다.
"""

import json
import os
from datetime import datetime, timedelta, timezone

DIR = os.path.dirname(os.path.abspath(__file__))
WINDOW = 7


def load(name, default):
    p = os.path.join(DIR, name)
    if not os.path.exists(p):
        return default
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def periods(today=None):
    """(이번주 시작, 이번주 끝, 지난주 시작, 지난주 끝) — 모두 날짜 문자열, 양끝 포함."""
    t = today or datetime.now(timezone.utc).date()
    end = t - timedelta(days=1)                       # 어제
    start = end - timedelta(days=WINDOW - 1)
    p_end = start - timedelta(days=1)
    p_start = p_end - timedelta(days=WINDOW - 1)
    return (start.isoformat(), end.isoformat(),
            p_start.isoformat(), p_end.isoformat())


def _sum(rows, key, a, b):
    """a~b 사이 날짜의 key 합. 값이 하나도 없으면 None."""
    vals = [r[key] for r in rows
            if a <= r.get("date", "") <= b and isinstance(r.get(key), (int, float))]
    return sum(vals) if vals else None


def _last(rows, key, b):
    """b 이하 날짜 중 가장 최근 key 값."""
    ok = [r for r in rows
          if r.get("date", "") <= b and isinstance(r.get(key), (int, float))]
    return ok[-1][key] if ok else None


def _chg(now, prev):
    """(증감, 증감률%) — 계산 못 하면 (None, None)."""
    if not isinstance(now, (int, float)) or not isinstance(prev, (int, float)):
        return None, None
    d = now - prev
    return d, (round(d / prev * 100) if prev else None)


def _rate(posts, react_keys, base_key):
    """반응률(%) — 콘텐츠 분석과 같은 방식. 인사이트가 있는 글 전체 기준."""
    r = v = 0
    for p in posts:
        ins = p.get("insights") or {}
        b = ins.get(base_key)
        if not isinstance(b, (int, float)) or b <= 0:
            continue
        v += b
        r += sum((ins.get(k) or 0) for k in react_keys)
    # 분모가 너무 작으면 비율이 크게 튄다. 판단을 오도하므로 아예 내지 않는다.
    return (r / v * 100) if v >= 100 else None


def _top(posts, key, a, b, limit=3):
    """a~b 사이에 올린 글을 key 기준 내림차순으로."""
    out = []
    for p in posts:
        ts = (p.get("timestamp") or "")[:10]
        if not (a <= ts <= b):
            continue
        v = (p.get("insights") or {}).get(key)
        if isinstance(v, (int, float)):
            out.append({"date": ts, "value": v,
                        "text": (p.get("caption") or p.get("text") or "").strip(),
                        "permalink": p.get("permalink")})
    out.sort(key=lambda r: -r["value"])
    return out[:limit]


def _rate_ig(posts):
    """인스타 반응률 — 본 사람 대비 좋아요·댓글·저장·공유."""
    r = v = 0
    for p in posts:
        ins = p.get("insights") or {}
        reach = ins.get("reach")
        if not isinstance(reach, (int, float)) or reach <= 0:
            continue
        v += reach
        r += (p.get("like_count") or 0) + (p.get("comments_count") or 0) \
             + (ins.get("saved") or 0) + (ins.get("shares") or 0)
    return (r / v * 100) if v >= 100 else None


def instagram(today=None):
    """계정별 주간 요약 리스트. 데이터가 없으면 빈 리스트."""
    a, b, pa, pb = periods(today)
    hist = load("history.json", {})
    rep = load("report_data.json", {})
    if not isinstance(hist, dict):
        return []

    by_user = {}
    for acc in (rep.get("accounts") or []):
        by_user[(acc.get("profile") or {}).get("username")] = acc

    out = []
    for user, rows in hist.items():
        rows = sorted([r for r in rows if isinstance(r, dict) and r.get("date")],
                      key=lambda r: r["date"])
        acc = by_user.get(user) or {}
        posts = acc.get("posts") or []
        m = {"user": user, "label": acc.get("label") or user,
             "start": a, "end": b,
             "followers": _last(rows, "followers_count", b),
             "posted": len([p for p in posts if a <= (p.get("timestamp") or "")[:10] <= b])}
        for k in ("reach", "views", "new_followers"):
            now, prev = _sum(rows, k, a, b), _sum(rows, k, pa, pb)
            m[k], m[k + "_prev"] = now, prev
            m[k + "_delta"], m[k + "_pct"] = _chg(now, prev)
        # 비팔로워 비율은 두 값이 모두 기록된 날만 써야 한다.
        # 도달은 29일치 시계열로 채워지지만 팔로워/비팔로워 분리는 그날 실행됐을 때만
        # 저장되므로, 그냥 각각 합치면 분모만 커져서 비율이 낮게 나온다.
        both = [r for r in rows if a <= r.get("date", "") <= b
                and isinstance(r.get("reach"), (int, float))
                and isinstance(r.get("reach_non_follower"), (int, float))]
        rc = sum(r["reach"] for r in both)
        nf = sum(r["reach_non_follower"] for r in both)
        m["non_follower_pct"] = round(nf / rc * 100) if rc else None
        m["non_follower_days"] = len(both)
        # 반응률은 콘텐츠 분석과 같은 기준(인사이트 있는 글 전체)으로 낸다.
        # 주 단위로 쪼개면 그 주에 올린 글이 없을 때 값이 사라진다.
        m["react_rate"] = _rate_ig(posts)
        m["top"] = _top(posts, "reach", a, b)
        out.append(m)
    out.sort(key=lambda m: -(m.get("followers") or 0))
    return out


def threads(today=None):
    a, b, pa, pb = periods(today)
    rows = load("threads_history.json", [])
    rep = load("threads_report.json", {}) or {}
    if not isinstance(rows, list):
        rows = []
    rows = sorted([r for r in rows if isinstance(r, dict) and r.get("date")],
                  key=lambda r: r["date"])
    if not rows and not rep:
        return None

    posts = rep.get("posts") or []
    prof = rep.get("profile") or {}
    now, prev = _sum(rows, "views", a, b), _sum(rows, "views", pa, pb)
    d, pct = _chg(now, prev)
    f_now, f_prev = _last(rows, "followers_count", b), _last(rows, "followers_count", pb)
    fd, _ = _chg(f_now, f_prev)
    cache = load("threads_cache.json", {})
    all_posts = list(cache.values()) if isinstance(cache, dict) else []
    tot = {k: sum((p.get("insights") or {}).get(k) or 0 for p in all_posts)
           for k in ("likes", "replies", "reposts", "quotes", "shares")}
    return {"username": prof.get("username"), "start": a, "end": b,
            "react_rate": _rate(all_posts,
                                ("likes", "replies", "reposts", "quotes", "shares"), "views"),
            "likes": tot["likes"], "replies": tot["replies"], "reposts": tot["reposts"],
            "views": now, "views_prev": prev, "views_delta": d, "views_pct": pct,
            "followers": f_now if f_now is not None else prof.get("followers_count"),
            "followers_delta": fd,
            "posted": len([p for p in posts if a <= (p.get("timestamp") or "")[:10] <= b]),
            "top": _top(posts, "views", a, b)}


# ---------------------------------------------------------------- 이슈 본문
def _n(v):
    return "-" if v is None else f"{v:,}"


def _arrow(d, pct):
    if d is None:
        return ""
    if d == 0:
        return " (지난주와 같음)"
    s = f" ({'+' if d > 0 else ''}{d:,}"
    if pct is not None:
        s += f", {'+' if d > 0 else ''}{pct}%"
    return s + ")"


def _cut(t, k=40):
    t = " ".join((t or "").split())
    return (t[:k] + "…") if len(t) > k else (t or "(내용 없음)")


def issue_body(site_url="https://wevape-no01.github.io/ig-report/"):
    """GitHub 이슈에 넣을 마크다운. 제목은 부르는 쪽에서 만든다."""
    igs, th = instagram(), threads()
    a, b, _, _ = periods()
    L = [f"**{a} ~ {b}** (7일)", ""]

    for m in igs:
        L.append(f"### 인스타그램 · {m['label']} (@{m['user']})")
        L.append(f"- 팔로워 **{_n(m['followers'])}명** · "
                 f"신규 {_n(m['new_followers'])}명{_arrow(m['new_followers_delta'], m['new_followers_pct'])}")
        L.append(f"- 도달 **{_n(m['reach'])}**{_arrow(m['reach_delta'], m['reach_pct'])}"
                 + (f" · 비팔로워 비중 {m['non_follower_pct']}% (기록된 {m['non_follower_days']}일 기준)"
                    if m["non_follower_pct"] is not None else ""))
        L.append(f"- 조회수 **{_n(m['views'])}**{_arrow(m['views_delta'], m['views_pct'])}")
        L.append(f"- 이번 주 올린 게시물 {m['posted']}개")
        if m["top"]:
            L.append("- 도달 상위:")
            for t in m["top"]:
                L.append(f"  - {t['date']} · 도달 {_n(t['value'])} · {_cut(t['text'])}")
        L.append("")

    if th:
        L.append(f"### 스레드 (@{th.get('username') or '?'})")
        L.append(f"- 팔로워 **{_n(th['followers'])}명**"
                 + (f" ({'+' if (th['followers_delta'] or 0) > 0 else ''}{th['followers_delta']:,}명)"
                    if th["followers_delta"] is not None else " (증감 기록 모으는 중)"))
        L.append(f"- 조회수 **{_n(th['views'])}**{_arrow(th['views_delta'], th['views_pct'])}")
        L.append(f"- 이번 주 올린 글 {th['posted']}개")
        if th["top"]:
            L.append("- 조회수 상위:")
            for t in th["top"]:
                L.append(f"  - {t['date']} · 조회 {_n(t['value'])} · {_cut(t['text'])}")
        L.append("")

    L.append(f"[주간 리포트 열기]({site_url}weekly.html) · "
             f"[일일 리포트]({site_url})")
    return "\n".join(L)


def issue_title():
    a, b, _, _ = periods()
    return f"주간 리포트 {a} ~ {b}"


if __name__ == "__main__":
    print(issue_title())
    print(issue_body())
