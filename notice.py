"""
사이트 오른쪽 위 종 아이콘에 뜨는 알림을 notices.json 에 쌓는다.

읽음 여부는 서버에 저장하지 않는다. 브라우저(localStorage)가 기억한다.
그래서 여기서는 "무슨 알림이 있었는지"만 관리한다.

key 를 주면 같은 key 의 알림은 덮어쓴다 — 같은 알림이 매일 쌓이는 걸 막는다.

쓰는 법:
  python notice.py <level> <key> <제목> [본문] [링크]
  level: error(빨강) | warn(주황) | info(파랑) | ok(초록)

예)
  python notice.py error collect-2026-08-15 "데이터 수집 실패" "인스타그램 수집이 실패했습니다."
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone

DIR = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(DIR, "notices.json")
LIMIT = 20                      # 최근 20개만 남긴다
LEVELS = ("error", "warn", "info", "ok")


def load():
    if not os.path.exists(PATH):
        return []
    try:
        with open(PATH, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def add(level, key, title, body="", link=""):
    """알림 하나를 넣는다. 이미 같은 key 가 있으면 내용만 갱신한다."""
    if level not in LEVELS:
        level = "info"
    now = datetime.now(timezone.utc) + timedelta(hours=9)     # 한국시간
    item = {"id": key, "level": level, "title": title,
            "body": body, "link": link, "at": f"{now:%Y-%m-%d %H:%M}"}

    rows = [r for r in load() if isinstance(r, dict) and r.get("id") != key]
    rows.insert(0, item)
    rows = rows[:LIMIT]
    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    print(f"알림 기록: [{level}] {title}")
    return item


def main():
    a = sys.argv[1:]
    if len(a) < 3:
        print(__doc__)
        sys.exit(1)
    add(a[0], a[1], a[2], a[3] if len(a) > 3 else "", a[4] if len(a) > 4 else "")


if __name__ == "__main__":
    main()
