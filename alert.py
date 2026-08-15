"""
실패 알림을 보낸다. 카카오톡 "나에게 보내기" 와 웹훅(슬랙/디스코드)을 모두 지원한다.
설정된 채널로만 보내고, 아무것도 없으면 조용히 넘어간다.

사용: python alert.py "보낼 메시지"

환경변수:
  KAKAO_REST_KEY / KAKAO_REFRESH_TOKEN   카카오톡 알림 (선택)
  ALERT_WEBHOOK                          슬랙 또는 디스코드 웹훅 주소 (선택)
  RUN_URL                                실패한 실행 주소 (있으면 메시지에 붙인다)

알림 전송이 실패해도 종료 코드는 0 이다 — 알림 때문에 워크플로가 또 실패하면 안 된다.
"""

import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

REPORT_URL = "https://wevape-no01.github.io/ig-report/"


def send_webhook(msg):
    hook = os.environ.get("ALERT_WEBHOOK", "").strip()
    if not hook:
        return
    payload = json.dumps({"text": msg, "content": msg}).encode()
    req = urllib.request.Request(
        hook, data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "ig-report/2.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            print(f"웹훅 알림 전송 완료 (HTTP {r.status})")
    except Exception as e:                                # noqa: BLE001
        print(f"웹훅 알림 전송 실패: {type(e).__name__} {e}")


def send_kakao(msg):
    try:
        import kakao
    except Exception as e:                                # noqa: BLE001
        print(f"카카오 모듈 로드 실패: {e}")
        return
    if not kakao.configured():
        return
    kakao.send(msg)


def main():
    body = sys.argv[1] if len(sys.argv) > 1 else "WEVAPE SNS 리포트 알림"
    now = datetime.now(timezone.utc) + timedelta(hours=9)
    msg = f"{body}\n시각: {now:%m/%d %H:%M} (한국시간)"
    run_url = os.environ.get("RUN_URL", "").strip()

    # 카카오는 200자 제한이라 링크를 버튼으로 뺀다. 웹훅은 본문에 그대로 붙인다.
    send_kakao(msg)

    web = msg
    if run_url:
        web += f"\n원인 확인: {run_url}"
    web += f"\n리포트: {REPORT_URL}"
    send_webhook(web)

    if not (os.environ.get("ALERT_WEBHOOK") or os.environ.get("KAKAO_REFRESH_TOKEN")):
        print("설정된 알림 채널이 없어 건너뜁니다.")


if __name__ == "__main__":
    main()
