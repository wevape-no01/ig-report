"""
GitHub 저장소 시크릿을 코드에서 갱신한다.

만료되는 토큰(스레드, 카카오)을 자동으로 갱신하려면 새 토큰을 어딘가 저장해야 하는데,
이 저장소는 공개라 파일에 쓰면 안 된다. 그래서 GitHub 시크릿에 되돌려 쓴다.
시크릿 값은 반드시 저장소 공개키로 암호화(libsodium sealed box)해서 보내야 한다.

필요:
  GH_PAT             Secrets: Read and write 권한이 있는 GitHub 토큰
  GITHUB_REPOSITORY  "소유자/저장소" — Actions 가 자동으로 넣어준다
  pip install pynacl
"""

import json
import os
import urllib.request


def _api(method, path, pat, payload=None):
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


def available():
    return bool(os.environ.get("GH_PAT") and os.environ.get("GITHUB_REPOSITORY"))


def write(name, value):
    """시크릿 하나를 갱신한다. 성공하면 True."""
    pat = os.environ.get("GH_PAT")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not (pat and repo):
        print(f"[{name}] 저장 건너뜀 — GH_PAT / GITHUB_REPOSITORY 없음")
        return False
    try:
        from base64 import b64encode
        from nacl import encoding, public
        key = _api("GET", f"/repos/{repo}/actions/secrets/public-key", pat)
        box = public.SealedBox(public.PublicKey(key["key"].encode(), encoding.Base64Encoder()))
        enc = b64encode(box.encrypt(value.encode())).decode()
        _api("PUT", f"/repos/{repo}/actions/secrets/{name}", pat,
             {"encrypted_value": enc, "key_id": key["key_id"]})
        print(f"[{name}] 시크릿 갱신 완료")
        return True
    except Exception as e:                                # noqa: BLE001
        print(f"[{name}] 시크릿 갱신 실패: {type(e).__name__} {e}")
        return False
