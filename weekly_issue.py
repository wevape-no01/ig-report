"""
주간 요약을 GitHub 이슈로 올린다.

GitHub 모바일 앱에서 이 저장소를 Watch 해두면 이슈가 올라올 때 휴대폰 알림이 온다.
새 계정도, 비용도, 별도 시크릿도 필요 없다 — Actions 가 자동으로 주는
GITHUB_TOKEN 만 쓴다 (워크플로에 issues: write 권한 필요).

환경변수:
  GITHUB_TOKEN       Actions 가 자동 주입
  GITHUB_REPOSITORY  "소유자/저장소" — Actions 가 자동 주입

이슈 발행이 실패해도 종료 코드는 0 이다. 알림 때문에 리포트 갱신이 실패하면 안 된다.
"""

import json
import os
import urllib.error
import urllib.request

import notice
import weekly

LABEL = "주간 리포트"
SITE = "https://wevape-no01.github.io/ig-report/"


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
    title, body = weekly.issue_title(), weekly.issue_body()

    # 사이트 오른쪽 위 종에도 띄운다. 한 주에 한 번만 뜨도록 key 에 기간을 넣는다.
    a, b, _, _ = weekly.periods()
    notice.add("info", f"weekly-{a}",
               "주간 리포트가 나왔습니다",
               f"{a} ~ {b} 7일치 요약입니다. 지난 7일과 비교한 숫자를 볼 수 있습니다.",
               SITE + "weekly.html")

    token = os.environ.get("GITHUB_TOKEN", "").strip()
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if not (token and repo):
        print("GITHUB_TOKEN / GITHUB_REPOSITORY 가 없어 이슈 발행을 건너뜁니다.")
        return

    # 담당자로 지정해야 휴대폰 푸시가 온다. 지정이 없으면 앱 알림함에만 들어간다.
    # (@멘션도 푸시가 오지만 담당자 지정과 겹쳐 두 번 오므로 쓰지 않는다.)
    owner = repo.split("/")[0]
    payload = {"title": title, "body": body,
               "labels": [LABEL], "assignees": [owner]}

    # 라벨이 없는 저장소거나 담당자 지정이 막히면 422 가 온다.
    # 그때는 문제되는 항목을 하나씩 빼면서 다시 시도한다 — 알림은 나가야 한다.
    for drop in (None, "labels", "assignees"):
        if drop:
            payload.pop(drop, None)
        try:
            d = post(token, repo, payload)
            note = f" ({drop} 없이)" if drop else ""
            print(f"주간 리포트 이슈 발행 완료{note}: #{d.get('number')} {d.get('html_url')}")
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
    print("주간 리포트 이슈 발행에 실패했습니다.")


if __name__ == "__main__":
    main()
