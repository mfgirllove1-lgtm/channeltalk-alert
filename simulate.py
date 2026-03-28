"""
simulate.py
채널톡 API 없이 실제 웹훅 페이로드를 흉내내어 전체 흐름을 테스트합니다.

사용법:
    python3 simulate.py                     # Railway 서버 대상
    python3 simulate.py http://localhost:8000  # 로컬 서버 대상
"""

import sys
import json
import requests

BASE_URL = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "https://channeltalk-alert-production.up.railway.app"

# ── 가상 채널톡 웹훅 페이로드 템플릿 ────────────────────────────
def make_payload(text: str, customer: str = "홍길동", chat_id: str = "CHAT001") -> dict:
    """실제 채널톡이 보내는 웹훅 형태를 흉내냅니다."""
    return {
        "type": "message_created",
        "chatId": chat_id,
        "userName": customer,
        "personType": "user",
        "channel": {
            "id": "CH_DUMMY_001",
            "name": "김상담"
        },
        "entity": {
            "plainText": text,
            "chatId": chat_id,
            "personType": "user"
        }
    }

# ── 테스트 시나리오 ─────────────────────────────────────────────
SCENARIOS = [
    {
        "label": "✅ 일반 문의 (정상)",
        "text": "배송이 언제 오나요? 주문번호 123456입니다.",
        "customer": "김민지",
        "chat_id": "CHAT001",
    },
    {
        "label": "⚖️ 소보원 신고 언급 (CRITICAL)",
        "text": "이렇게 처리해주시면 소보원에 신고할 수밖에 없어요. 전자상거래법 위반 아닌가요?",
        "customer": "박철수",
        "chat_id": "CHAT002",
    },
    {
        "label": "📢 언론 제보 위협 (CRITICAL)",
        "text": "계속 이러시면 언론에 제보하고 커뮤니티에 올릴 거예요.",
        "customer": "이영희",
        "chat_id": "CHAT003",
    },
    {
        "label": "🔥 강성 불만 (HIGH)",
        "text": "환불 안 해주면 가만 안 있을게요. 이게 말이 되냐고요. 진짜 사기네요.",
        "customer": "최민수",
        "chat_id": "CHAT004",
    },
    {
        "label": "🚨 복합 에스컬레이션 (CRITICAL — 다중 규칙)",
        "text": "소송 걸고 언론에도 제보할 거예요. 상담사 태도도 너무 불친절했어요.",
        "customer": "정수진",
        "chat_id": "CHAT005",
    },
    {
        "label": "👤 상담사 불만 (HIGH)",
        "text": "담당자 바꿔주세요. 상담사가 너무 무시하고 매너가 없어요.",
        "customer": "강현우",
        "chat_id": "CHAT006",
    },
]


def run():
    print(f"\n{'='*60}")
    print(f"  채널톡 에스컬레이션 시뮬레이션")
    print(f"  대상 서버: {BASE_URL}")
    print(f"{'='*60}\n")

    results = {"escalated": 0, "normal": 0, "error": 0}

    for s in SCENARIOS:
        print(f"[시나리오] {s['label']}")
        print(f"  고객: {s['customer']} | 채팅ID: {s['chat_id']}")
        print(f"  메시지: {s['text'][:60]}...")

        # 1) /test/detect — 탐지 결과만 빠르게 확인
        try:
            r = requests.post(
                f"{BASE_URL}/test/detect",
                json={"text": s["text"]},
                timeout=10
            )
            r.raise_for_status()
            d = r.json()
            print(f"  탐지결과: level={d['level']} | escalate={d['should_escalate']}")
            if d["matched_keywords"]:
                print(f"  감지키워드: {', '.join(d['matched_keywords'])}")
        except Exception as e:
            print(f"  [오류] /test/detect 실패: {e}")
            results["error"] += 1
            print()
            continue

        # 2) /webhook/channeltalk — 실제 웹훅 흐름 (Slack 알림까지)
        try:
            payload = make_payload(s["text"], s["customer"], s["chat_id"])
            r2 = requests.post(
                f"{BASE_URL}/webhook/channeltalk",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            r2.raise_for_status()
            w = r2.json()
            status = w.get("status", "unknown")
            print(f"  웹훅응답: {status}", end="")
            if status == "escalated":
                print(f" → Slack 알림 발송됨 🔔")
                results["escalated"] += 1
            else:
                print(f" → 정상 처리")
                results["normal"] += 1
        except Exception as e:
            print(f"  [오류] /webhook/channeltalk 실패: {e}")
            results["error"] += 1

        print()

    print(f"{'='*60}")
    print(f"  결과 요약")
    print(f"  에스컬레이션: {results['escalated']}건 | 정상: {results['normal']}건 | 오류: {results['error']}건")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    run()
