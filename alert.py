"""
실패 알림을 웹훅(슬랙/디스코드)으로 보낸다.
ALERT_WEBHOOK 이 없으면 조용히 넘어간다.

사용: python alert.py "보낼 메시지"

환경변수:
  ALERT_WEBHOOK  슬랙 또는 디스코드 웹훅 주소 (없으면 아무것도 안 함)
  RUN_URL        실패한 실행 주소 (있으면 메시지에 붙인다)

알림 전송이 실패해도 종료 코드는 0 이다 — 알림 때문에 워크플로가 또 실패하면 안 된다.

참고: 휴대폰 푸시는 GitHub 모바일 앱이 담당한다. 이 파일은 슬랙/디스코드를
추가로 쓰고 싶을 때를 위한 것이고, 시크릿을 넣기 전까지는 동작하지 않는다.
"""

import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

REPORT_URL = "https://wevape-no01.github.io/ig-report/"


def main():
    hook = os.environ.get("ALERT_WEBHOOK", "").strip()
    if not hook:
        print("ALERT_WEBHOOK 이 없어 알림을 건너뜁니다.")
        return

    body = sys.argv[1] if len(sys.argv) > 1 else "WEVAPE SNS 리포트 알림"
    now = datetime.now(timezone.utc) + timedelta(hours=9)
    msg = f"{body}\n시각: {now:%m/%d %H:%M} (한국시간)"
    run_url = os.environ.get("RUN_URL", "").strip()
    if run_url:
        msg += f"\n원인 확인: {run_url}"
    msg += f"\n리포트: {REPORT_URL}"

    # 슬랙은 text, 디스코드는 content 를 읽는다. 둘 다 담아 보낸다.
    payload = json.dumps({"text": msg, "content": msg}).encode()
    req = urllib.request.Request(
        hook, data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "ig-report/2.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            print(f"알림 전송 완료 (HTTP {r.status})")
    except Exception as e:                                # noqa: BLE001
        print(f"알림 전송 실패: {type(e).__name__} {e}")


if __name__ == "__main__":
    main()
