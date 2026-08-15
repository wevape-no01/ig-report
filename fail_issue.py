"""
데이터 수집이 실패하면 GitHub 이슈로 남긴다. 정상으로 돌아오면 그 이슈를 닫는다.

왜 이슈로 만드는가:
  GitHub 이 자동으로 보내는 "workflow run failed" 푸시는 저장소 이름과 워크플로
  이름만 실어 보낸다. 무엇이 왜 실패했는지는 안 보인다. 그 형식은 바꿀 수 없다.
  반면 이슈 알림은 제목과 본문 미리보기가 그대로 푸시에 실린다.
  그래서 실패 내용을 잠금화면에서 바로 읽으려면 이슈로 만드는 편이 낫다.

중복 방지:
  이미 열려 있는 실패 이슈가 있으면 새로 만들지 않고 댓글만 단다.
  (댓글도 푸시가 온다. 매일 실패해도 이슈가 쌓이지 않는다.)

쓰는 법:
  python fail_issue.py open     실패했을 때
  python fail_issue.py close    정상 갱신됐을 때 (열린 실패 이슈를 닫는다)

환경변수: GITHUB_TOKEN, GITHUB_REPOSITORY (Actions 가 자동 주입)
          RUN_URL (선택) 실패한 실행 주소

알림 때문에 워크플로가 또 실패하면 안 되므로 종료 코드는 항상 0 이다.
"""

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

PREFIX = "🔴 데이터 수집 실패"
SITE = "https://wevape-no01.github.io/ig-report/"


def kst():
    return datetime.now(timezone.utc) + timedelta(hours=9)


def api(method, path, payload=None):
    token = os.environ["GITHUB_TOKEN"]
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        data=json.dumps(payload).encode() if payload is not None else None,
        method=method,
        headers={"Authorization": f"Bearer {token}",
                 "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28",
                 "Content-Type": "application/json",
                 "User-Agent": "ig-report/2.0"})
    with urllib.request.urlopen(req, timeout=40) as r:
        raw = r.read().decode()
        return json.loads(raw) if raw.strip() else {}


def open_failure_issues(repo):
    """제목이 PREFIX 로 시작하는, 열려 있는 이슈들. PR 은 걸러낸다."""
    rows = api("GET", f"/repos/{repo}/issues?state=open&per_page=50")
    return [i for i in rows
            if "pull_request" not in i and (i.get("title") or "").startswith(PREFIX)]


def do_open(repo):
    now = kst()
    run = os.environ.get("RUN_URL", "").strip()
    owner = repo.split("/")[0]
    # 휴대폰 푸시를 확실히 받으려면 "나를 직접 겨냥한" 알림이어야 한다.
    # Watch 중인 저장소에 이슈가 새로 생긴 것만으로는 알림함에만 들어가고
    # 푸시는 안 오는 경우가 있다. @멘션과 담당자 지정은 푸시가 보장된다.
    body = (
        f"@{owner}\n\n"
        f"매일 아침 7시 자동 수집이 **{now:%m월 %d일 %H:%M}** (한국시간)에 실패했습니다.\n\n"
        f"리포트 숫자는 마지막으로 성공한 시점 그대로 남아 있습니다. "
        f"내일 아침 자동 실행에서 다시 시도하며, 그때 성공하면 이 이슈는 자동으로 닫힙니다.\n\n"
        + (f"- 실패 원인 보기: {run}\n" if run else "")
        + f"- 리포트 열기: {SITE}\n\n"
        f"토큰이 만료됐거나 Meta 개발자 계정이 잠긴 경우가 가장 흔합니다. "
        f"실행 기록의 빨간 단계를 열면 원인 메시지가 나옵니다."
    )
    existing = open_failure_issues(repo)
    if existing:
        n = existing[0]["number"]
        api("POST", f"/repos/{repo}/issues/{n}/comments", {"body": body})   # 댓글도 @멘션이 들어간다
        print(f"이미 열린 실패 이슈 #{n} 에 댓글을 달았습니다.")
        return
    payload = {"title": f"{PREFIX} — {now:%m/%d %H:%M}", "body": body,
               "assignees": [owner]}
    try:
        d = api("POST", f"/repos/{repo}/issues", payload)
    except urllib.error.HTTPError as e:
        if e.code != 422:                                 # 담당자 지정이 막힌 경우
            raise
        print("담당자 지정에 실패해 담당자 없이 다시 만듭니다.")
        payload.pop("assignees")
        d = api("POST", f"/repos/{repo}/issues", payload)
    print(f"실패 이슈 생성: #{d.get('number')} {d.get('html_url')}")


def do_close(repo):
    rows = open_failure_issues(repo)
    if not rows:
        print("열려 있는 실패 이슈가 없습니다.")
        return
    now = kst()
    for i in rows:
        n = i["number"]
        api("POST", f"/repos/{repo}/issues/{n}/comments",
            {"body": f"✅ **{now:%m월 %d일 %H:%M}** (한국시간) 수집이 정상으로 돌아왔습니다. "
                     f"리포트가 다시 갱신됐습니다.\n\n리포트 열기: {SITE}"})
        api("PATCH", f"/repos/{repo}/issues/{n}", {"state": "closed"})
        print(f"실패 이슈 #{n} 를 닫았습니다.")


def main():
    what = sys.argv[1] if len(sys.argv) > 1 else "open"
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if not (repo and os.environ.get("GITHUB_TOKEN")):
        print("GITHUB_TOKEN / GITHUB_REPOSITORY 가 없어 건너뜁니다.")
        return
    try:
        (do_close if what == "close" else do_open)(repo)
    except urllib.error.HTTPError as e:
        print(f"이슈 처리 실패 (HTTP {e.code}): {e.read().decode()[:300]}")
    except Exception as e:                                # noqa: BLE001
        print(f"이슈 처리 실패: {type(e).__name__} {e}")


if __name__ == "__main__":
    main()
