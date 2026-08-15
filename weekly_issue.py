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


def post(token, repo, title, body):
    req = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/issues",
        data=json.dumps({"title": title, "body": body,
                         "labels": [LABEL]}).encode(),
        method="POST",
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

    try:
        d = post(token, repo, title, body)
        print(f"주간 리포트 이슈 발행 완료: #{d.get('number')} {d.get('html_url')}")
    except urllib.error.HTTPError as e:
        detail = e.read().decode()[:300]
        if e.code == 422 and "label" in detail.lower():
            # 라벨이 아직 없는 저장소 — 라벨 없이 다시 시도한다
            try:
                req_body = {"title": title, "body": body}
                req = urllib.request.Request(
                    f"https://api.github.com/repos/{repo}/issues",
                    data=json.dumps(req_body).encode(), method="POST",
                    headers={"Authorization": f"Bearer {token}",
                             "Accept": "application/vnd.github+json",
                             "Content-Type": "application/json",
                             "User-Agent": "ig-report/2.0"})
                with urllib.request.urlopen(req, timeout=40) as r:
                    d = json.loads(r.read().decode())
                print(f"주간 리포트 이슈 발행 완료(라벨 없이): #{d.get('number')}")
                return
            except Exception as e2:                       # noqa: BLE001
                print(f"재시도 실패: {type(e2).__name__} {e2}")
                return
        print(f"이슈 발행 실패 (HTTP {e.code}): {detail}")
    except Exception as e:                                # noqa: BLE001
        print(f"이슈 발행 실패: {type(e).__name__} {e}")


if __name__ == "__main__":
    main()
