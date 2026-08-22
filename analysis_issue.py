"""콘텐츠 분석 진단을 주간 보고로 내보낸다.

두 곳으로 같이 나간다.
  1) 사이트 오른쪽 위 종 (notices.json)
  2) GitHub 이슈 → GitHub 모바일 앱을 깔고 이 저장소를 Watch 해두면 휴대폰 알림

주간 리포트(weekly_issue.py)와 같은 방식이다. 다른 점은 담는 내용이다.
주간 리포트는 "지난 7일 숫자", 여기는 "지금 무엇이 문제이고 무엇을 하면 되는가"다.

문제가 있으면 같은 알림에 함께 담는다.
  - 확인 필요 항목이 있거나
  - 이번 주 값이 지난주보다 눈에 띄게 나빠졌으면
  사이트 알림 등급을 warn 으로 올리고 이슈 제목 앞에 ⚠️ 를 붙인다.
  알림을 두 번 보내지 않는다 — 하나에 다 담아야 읽는다.

이슈 발행이 실패해도 종료 코드는 0 이다. 알림 때문에 리포트 갱신이 실패하면 안 된다.

실행: python3 analysis_issue.py
"""

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

import advice
import analysis_history
import build_analysis
import notice

LABEL = "콘텐츠 분석"
SITE = "https://wevape-no01.github.io/ig-report/"

# 이만큼 넘게 나빠지면 "문제"로 본다 (지난주 대비 비율)
WORSE_PCT = 10.0

# 알림에 담을 지표. (열쇠, 이름, 소수 자리, 클수록 좋은가)
WATCH = [
    ("er_bench", "반응률", 2, True),
    ("posted_4w", "최근 4주 발행", 0, True),
    ("reach_median", "도달 중앙값", 0, True),
    ("follow_per100", "도달 100당 팔로우", 2, True),
]


def _fmt(v, dec):
    return "–" if v is None else f"{v:,.{dec}f}"


def _ga(word):
    """받침이 있으면 '이', 없으면 '가'. ("도달 100당 팔로우이" 같은 게 나온 적 있다)"""
    ch = word.strip()[-1] if word.strip() else ""
    if "가" <= ch <= "힣":
        return "이" if (ord(ch) - 0xAC00) % 28 else "가"
    return "이"


def deltas(rows):
    """지난주 대비 변화. (표시줄 목록, 나빠진 것 목록)"""
    lines, worse = [], []
    if len(rows) < 2:
        return lines, worse
    now, prev = rows[-1], rows[-2]
    for key, name, dec, up_good in WATCH:
        a, b = now.get(key), prev.get(key)
        if a is None or b is None:
            lines.append(f"- {name} · {_fmt(a, dec)} (지난주 비교값 없음)")
            continue
        d = a - b
        pct = (d / b * 100) if b else 0
        if abs(pct) < 0.5:
            lines.append(f"- {name} · {_fmt(a, dec)} (지난주와 거의 같음)")
            continue
        arrow = "▲" if d > 0 else "▼"
        lines.append(f"- {name} · {_fmt(a, dec)} {arrow} {abs(pct):.0f}% "
                     f"(지난주 {_fmt(b, dec)})")
        good = (d > 0) if up_good else (d < 0)
        if not good and abs(pct) >= WORSE_PCT:
            worse.append(f"{name}{_ga(name)} 지난주보다 {abs(pct):.0f}% 낮아졌습니다 "
                         f"({_fmt(b, dec)} → {_fmt(a, dec)})")
    return lines, worse


def collect():
    """계정별로 진단·확인 필요·추세를 모은다. 분석할 게 없으면 None."""
    cache = build_analysis.load("posts_cache.json", {})
    report = build_analysis.load("report_data.json", {})
    accounts = build_analysis.prep(cache, report)
    store = analysis_history._load(analysis_history.STORE, {}) or {}
    out = []
    for a in accounts:
        posts = a["posts"]
        if len(posts) < build_analysis.MIN_POSTS:
            continue
        prof = a["acc"]["profile"]
        F = prof.get("followers_count") or 0
        user = prof.get("username") or "?"
        diags = advice.diagnose(posts, F, build_analysis.BENCH_ER_FOLLOWERS)
        pl = advice.plan(posts, F, build_analysis.BENCH_ER_FOLLOWERS, diags)

        # "확인 필요" 문장은 화면과 같은 것을 쓴다 (HTML 태그만 걷어낸다)
        n = len(posts)
        a_reach = build_analysis.avg(posts, lambda p: p["reach"])
        a_inter = build_analysis.avg(posts, lambda p: p["inter"])
        er_reach = a_inter / a_reach * 100 if a_reach else 0
        er_fol = a_inter / F * 100 if F else 0
        basic = build_analysis.avg(posts, lambda p: p["likes"] + p["comments"])
        er_basic = basic / F * 100 if F else 0
        tot_reach = sum(p["reach"] for p in posts) or 1
        save_rate = sum(p["saved"] for p in posts) / tot_reach * 100
        share_rate = sum(p["shares"] for p in posts) / tot_reach * 100
        fmt = build_analysis.group_stats(posts, lambda p: p["type"])
        ranked = sorted(posts, key=lambda p: -p["er"])
        _, chk = build_analysis.build_insights(
            posts, ranked, fmt, [], er_reach, er_fol,
            save_rate, share_rate, F, n, er_basic)
        chk = [strip_tags(c) for c in chk]

        lines, worse = deltas(store.get(user) or [])
        out.append({"user": user, "label": a["acc"].get("label") or user,
                    "n": n, "followers": F, "er": er_basic,
                    "diags": diags, "plan": pl, "chk": chk,
                    "trend": lines, "worse": worse})
    return out or None


def strip_tags(s):
    """알림 본문은 마크다운이라 HTML 태그를 걷어낸다."""
    out, keep = [], True
    for ch in s:
        if ch == "<":
            keep = False
        elif ch == ">":
            keep = True
        elif keep:
            out.append(ch)
    return " ".join("".join(out).split())


def body_md(accs, site=SITE):
    L = []
    for a in accs:
        L.append(f"## @{a['user']}")
        L.append(f"게시물 {a['n']}개 · 팔로워 {a['followers']:,}명 · "
                 f"반응률 {a['er']:.2f}% (좋아요+댓글÷팔로워)")
        L.append("")
        if a["worse"]:
            L.append("### ⚠️ 지난주보다 나빠진 것")
            L += [f"- {w}" for w in a["worse"]]
            L.append("")
        if a["trend"]:
            L.append("### 지난주 대비")
            L += a["trend"]
            L.append("")
        if a["chk"]:
            L.append("### ⚠️ 확인 필요")
            L += [f"- {c}" for c in a["chk"]]
            L.append("")
        if a["diags"]:
            L.append("### 지금 할 일")
            for d in a["diags"][:3]:
                L.append(f"**{d['title']}**")
                L.append(f"- 근거 · {d['why']}")
                L.append(f"- 실행 · {d['do']}")
                L.append("")
        rules = (a["plan"] or {}).get("rules") or []
        if rules:
            L.append("### 발행 규칙")
            L.append("| 항목 | 값 |")
            L.append("|---|---|")
            L += [f"| {k} | {v} |" for k, v, _ in rules]
            L.append("")
    L.append("---")
    L.append(f"자세한 근거와 4주 판정 기준은 [콘텐츠 분석]({site}analysis.html), "
             f"수치 추이는 [지난 분석]({site}analysis-trend.html) 에서 봅니다.")
    return "\n".join(L)


def post(token, repo, payload):
    req = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/issues",
        data=json.dumps(payload).encode(), method="POST",
        headers={"Authorization": f"Bearer {token}",
                 "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28",
                 "Content-Type": "application/json",
                 "User-Agent": "ig-report/2.0"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read().decode())


def main():
    accs = collect()
    if not accs:
        print("분석할 게시물이 부족해 콘텐츠 분석 보고를 건너뜁니다.")
        return

    today = (datetime.now(timezone.utc) + timedelta(hours=9)).date()
    week = analysis_history.week_start(
        datetime.now(timezone.utc) + timedelta(hours=9)).strftime("%Y-%m-%d")

    problems = [p for a in accs for p in (a["worse"] + a["chk"])]
    head = accs[0]
    title = f"콘텐츠 분석 {today:%Y-%m-%d}"
    if problems:
        title = "⚠️ " + title

    # --- 사이트 알림 (한 주에 하나만 뜨도록 key 에 주를 넣는다)
    if problems:
        first = problems[0]
        summary = (f"확인할 것이 {len(problems)}건 있습니다. {first}"
                   if len(problems) > 1 else first)
        notice.add("warn", f"analysis-{week}",
                   "콘텐츠 분석 — 확인이 필요합니다", summary, SITE + "analysis.html")
    else:
        todo = head["diags"][0]["title"] if head["diags"] else "지금은 큰 문제가 없습니다."
        notice.add("info", f"analysis-{week}",
                   "콘텐츠 분석 보고가 나왔습니다",
                   f"반응률 {head['er']:.2f}% · {todo}", SITE + "analysis.html")

    # --- GitHub 이슈 (휴대폰 알림)
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if not (token and repo):
        print("GITHUB_TOKEN / GITHUB_REPOSITORY 가 없어 이슈 발행을 건너뜁니다.")
        print(body_md(accs))
        return

    # 담당자로 지정해야 휴대폰 푸시가 온다 (weekly_issue.py 와 같은 이유)
    owner = repo.split("/")[0]
    payload = {"title": title, "body": body_md(accs),
               "labels": [LABEL], "assignees": [owner]}

    # 라벨이 없거나 담당자 지정이 막히면 422 — 하나씩 빼고 다시 시도한다.
    for drop in (None, "labels", "assignees"):
        if drop:
            payload.pop(drop, None)
        try:
            d = post(token, repo, payload)
            note = f" ({drop} 없이)" if drop else ""
            print(f"콘텐츠 분석 이슈 발행 완료{note}: #{d.get('number')} {d.get('html_url')}")
            return
        except urllib.error.HTTPError as e:
            detail = e.read().decode()[:300]
            if e.code != 422:
                print(f"이슈 발행 실패 (HTTP {e.code}): {detail}")
                return
            print(f"422 — 다음 항목을 빼고 다시 시도합니다. 응답: {detail[:150]}")
        except Exception as e:                            # noqa: BLE001
            print(f"이슈 발행 실패: {type(e).__name__} {e}")
            return
    print("콘텐츠 분석 이슈 발행에 실패했습니다.")


if __name__ == "__main__":
    main()
