#!/usr/bin/env python3
"""
화면(HTML)만 고칠 때 쓰는 재생성 스크립트.

왜 필요한가:
  화면 코드를 고친 뒤 그냥 build_*.py 를 돌리면, 이 폴더에 남아 있는 '옛 데이터'로
  페이지가 만들어진다. 그걸 저장소에 올리면 사이트가 과거 날짜로 되돌아가고
  "N일째 데이터가 갱신되지 않았습니다" 빨간 띠가 뜬다. (2026-08-20, 08-21 두 번 발생)

  이 스크립트는 저장소의 최신 JSON 을 먼저 받아온 뒤에 페이지를 만든다.
  Meta API 는 한 번도 호출하지 않으므로 계정 차단 위험이 없다.

사용법:
    python3 rebuild.py            # 최신 데이터 받아서 10개 페이지 재생성
    python3 rebuild.py --no-pull  # 받지 않고 지금 있는 데이터로만 (권장하지 않음)
"""

import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone

DIR = os.path.dirname(os.path.abspath(__file__))
RAW = "https://raw.githubusercontent.com/wevape-no01/ig-report/main/"

# 수집기가 만드는 파일들. 이 파일들은 손으로 고치지 않는다.
DATA_FILES = [
    "report_data.json",
    "history.json",
    "posts_cache.json",
    "threads_report.json",
    "threads_history.json",
    "threads_cache.json",
    "notices.json",
]

# 저장소에 아직 없을 수도 있는 파일. 못 받아도 멈추지 않는다.
# analysis_history.json 은 첫 실행 때 만들어지므로 처음에는 없는 게 정상이다.
OPTIONAL_FILES = ["analysis_history.json"]

BUILDERS = [
    "build_dashboard.py",
    "build_analysis.py",
    "build_threads.py",
    "build_threads_analysis.py",
    "build_weekly.py",
    "build_analysis_trend.py",
]

PAGES = [
    "index.html", "analysis.html", "analysis-detail.html",
    "threads.html", "threads-analysis.html", "threads-detail.html",
    "weekly.html", "weekly-past.html",
    "threads-weekly.html", "threads-weekly-past.html",
    "analysis-trend.html",
]


def stamp(name, key="generated_at"):
    """JSON 파일의 생성 시각을 읽는다. 못 읽으면 None."""
    p = os.path.join(DIR, name)
    if not os.path.exists(p):
        return None
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f).get(key)
    except (json.JSONDecodeError, OSError):
        return None


def pull():
    """저장소의 최신 데이터 파일을 받아온다. 하나라도 실패하면 중단."""
    print("· 저장소에서 최신 데이터를 받아옵니다")
    before = stamp("report_data.json")
    for name in DATA_FILES + OPTIONAL_FILES:
        url = RAW + name
        tmp = os.path.join(DIR, name + ".tmp")
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                if r.status != 200:
                    raise OSError(f"HTTP {r.status}")
                body = r.read()
        except Exception as e:                      # noqa: BLE001
            if os.path.exists(tmp):
                os.remove(tmp)
            if name in OPTIONAL_FILES:
                print(f"  · {name} 없음 — 건너뜁니다 (아직 안 만들어졌을 수 있음)")
                continue
            print(f"  ✗ {name} 받기 실패: {e}")
            print("    → 옛 데이터로 페이지를 만들면 안 되므로 여기서 멈춥니다.")
            sys.exit(1)
        with open(tmp, "wb") as f:
            f.write(body)
        os.replace(tmp, os.path.join(DIR, name))
        print(f"  ✓ {name} ({len(body):,} bytes)")
    after = stamp("report_data.json")
    if before and before != after:
        print(f"  데이터 시각: {before} → {after}")
    else:
        print(f"  데이터 시각: {after}")


def build():
    print("· 페이지를 다시 만듭니다")
    for b in BUILDERS:
        r = subprocess.run([sys.executable, os.path.join(DIR, b)],
                           capture_output=True, text=True, cwd=DIR)
        if r.returncode != 0:
            print(f"  ✗ {b} 실패\n{r.stdout}\n{r.stderr}")
            sys.exit(1)
        print(f"  ✓ {b}")


def verify():
    """모든 페이지가 방금 받은 데이터 시각을 쓰고 있는지 확인한다."""
    print("· 확인")
    ig, th = stamp("report_data.json"), stamp("threads_report.json")
    ok = True
    for name in PAGES:
        p = os.path.join(DIR, name)
        if not os.path.exists(p):
            print(f"  ✗ {name} 없음")
            ok = False
            continue
        with open(p, encoding="utf-8") as f:
            html = f.read()
        i = html.find('data-generated="')
        got = html[i + 16:html.find('"', i + 16)] if i >= 0 else ""
        # 주간·지난 리포트는 기준 시각을 쓰지 않는다(빈 값이 정상)
        if got and got not in (ig, th):
            print(f"  ✗ {name} 이 옛 데이터를 쓰고 있습니다: {got}")
            ok = False
    if not ok:
        sys.exit(1)

    # 페이지와 데이터가 같아도, 그 데이터 자체가 오래됐으면 올리면 안 된다.
    # (사이트에 "N일째 갱신되지 않았습니다" 빨간 띠가 뜨는 조건과 같은 36시간 기준)
    age = None
    try:
        t = datetime.fromisoformat(ig)
        age = (datetime.now(timezone.utc) - t).total_seconds() / 3600
    except (TypeError, ValueError):
        pass
    if age is not None and age > 36:
        print(f"  ✗ 데이터가 {age:.0f}시간 전 것입니다 ({ig})")
        print("    → 이대로 올리면 사이트가 과거로 되돌아갑니다.")
        print("    → --no-pull 없이 다시 실행해 최신 데이터를 받으세요.")
        sys.exit(1)

    print(f"  ✓ 10개 페이지 모두 최신 데이터 기준 (인스타 {ig} · 스레드 {th})")
    if age is not None:
        print(f"  ✓ 데이터는 {age:.0f}시간 전 것입니다 (36시간 넘으면 중단)")
    print("\n이제 이 HTML 들을 저장소에 올리면 됩니다.")


if __name__ == "__main__":
    if "--no-pull" not in sys.argv:
        pull()
    else:
        print("· 데이터를 받지 않습니다 (--no-pull) — 옛 데이터일 수 있습니다")
    build()
    verify()
