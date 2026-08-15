"""
카카오톡 "나에게 보내기" 알림.

토큰 구조:
  액세스 토큰   6시간   — 매번 새로 받는다 (저장하지 않음)
  리프레시 토큰 2개월  — 시크릿 KAKAO_REFRESH_TOKEN 에 보관.
                        갱신 시 새 값이 내려오면 시크릿에 다시 저장한다.

필요한 환경변수:
  KAKAO_REST_KEY        카카오 개발자 앱의 REST API 키
  KAKAO_REFRESH_TOKEN   최초 인증으로 받은 리프레시 토큰
  (선택) GH_PAT + GITHUB_REPOSITORY  새 리프레시 토큰 자동 저장용

동의항목(scope): talk_message
"""

import json
import os
import urllib.parse
import urllib.request

import ghsecret

AUTH = "https://kauth.kakao.com/oauth/token"
SEND = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
TEXT_LIMIT = 190          # 카카오 텍스트 템플릿 한도는 200자. 여유를 둔다.
REPORT_URL = "https://wevape-no01.github.io/ig-report/"


def _post(url, fields, headers=None):
    data = urllib.parse.urlencode(fields).encode()
    h = {"Content-Type": "application/x-www-form-urlencoded;charset=utf-8",
         "User-Agent": "ig-report/2.0"}
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h, method="POST")
    with urllib.request.urlopen(req, timeout=25) as r:
        raw = r.read().decode()
        return json.loads(raw) if raw.strip() else {}


def configured():
    return bool(os.environ.get("KAKAO_REST_KEY") and os.environ.get("KAKAO_REFRESH_TOKEN"))


def get_access_token():
    """리프레시 토큰으로 액세스 토큰을 받는다.
    카카오는 리프레시 토큰 만료가 1개월 미만으로 남았을 때만 새 값을 함께 준다.
    새 값이 오면 즉시 시크릿에 저장해야 한다 — 놓치면 연결이 끊긴다."""
    d = _post(AUTH, {
        "grant_type": "refresh_token",
        "client_id": os.environ["KAKAO_REST_KEY"],
        "refresh_token": os.environ["KAKAO_REFRESH_TOKEN"],
    })
    new_refresh = d.get("refresh_token")
    if new_refresh:
        print("카카오 리프레시 토큰이 새로 발급됐습니다. 시크릿에 저장합니다.")
        ghsecret.write("KAKAO_REFRESH_TOKEN", new_refresh)
    return d.get("access_token")


def send(text, link=REPORT_URL, button="리포트 열기"):
    """나에게 보내기. 성공하면 True. 실패해도 예외를 밖으로 던지지 않는다."""
    try:
        token = get_access_token()
        if not token:
            print("카카오 액세스 토큰을 받지 못했습니다.")
            return False
        body = text if len(text) <= TEXT_LIMIT else text[:TEXT_LIMIT - 1] + "…"
        template = {
            "object_type": "text",
            "text": body,
            "link": {"web_url": link, "mobile_web_url": link},
            "button_title": button,
        }
        r = _post(SEND, {"template_object": json.dumps(template, ensure_ascii=False)},
                  {"Authorization": f"Bearer {token}"})
        if r.get("result_code") == 0:
            print("카카오톡 알림 전송 완료")
            return True
        print(f"카카오톡 응답: {r}")
        return False
    except Exception as e:                                # noqa: BLE001
        print(f"카카오톡 전송 실패: {type(e).__name__} {e}")
        return False


def exchange_code(code, redirect_uri):
    """최초 1회: 인가 코드를 리프레시 토큰으로 바꾸고 시크릿에 저장한다.
    토큰 값은 화면에 찍지 않는다."""
    d = _post(AUTH, {
        "grant_type": "authorization_code",
        "client_id": os.environ["KAKAO_REST_KEY"],
        "redirect_uri": redirect_uri,
        "code": code,
    })
    refresh = d.get("refresh_token")
    access = d.get("access_token")
    if not refresh:
        print(f"리프레시 토큰을 받지 못했습니다. 응답: { {k: v for k, v in d.items() if 'token' not in k} }")
        return False
    print(f"인증 성공 — 리프레시 토큰 유효기간 {int(d.get('refresh_token_expires_in', 0)) // 86400}일")
    if not ghsecret.write("KAKAO_REFRESH_TOKEN", refresh):
        print("시크릿 저장에 실패했습니다. GH_PAT 권한을 확인하세요.")
        return False
    # 바로 테스트 메시지를 보내 연결을 확인한다
    try:
        template = {
            "object_type": "text",
            "text": "✅ WEVAPE SNS 알림 연결 완료\n앞으로 데이터 수집이 실패하면 여기로 알려드립니다.",
            "link": {"web_url": REPORT_URL, "mobile_web_url": REPORT_URL},
            "button_title": "리포트 열기",
        }
        r = _post(SEND, {"template_object": json.dumps(template, ensure_ascii=False)},
                  {"Authorization": f"Bearer {access}"})
        print("테스트 메시지 전송 결과:", "성공" if r.get("result_code") == 0 else r)
    except Exception as e:                                # noqa: BLE001
        print(f"테스트 메시지 실패: {type(e).__name__} {e}")
    return True


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2 and sys.argv[1] == "setup":
        ok = exchange_code(sys.argv[2].strip(),
                           os.environ.get("KAKAO_REDIRECT_URI", REPORT_URL))
        sys.exit(0 if ok else 1)
    send(sys.argv[1] if len(sys.argv) > 1 else "WEVAPE SNS 테스트 알림")
