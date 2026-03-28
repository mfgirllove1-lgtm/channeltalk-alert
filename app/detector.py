"""
escalation_detector.py
채널톡 메시지에서 에스컬레이션 필요 여부를 탐지합니다.
"""

from dataclasses import dataclass, field
from typing import Optional

# ── 탐지 규칙 정의 ──────────────────────────────────────────
RULES = {
    "법적조치": {
        "level": "CRITICAL",
        "keywords": ["고소", "소송", "변호사", "법적조치", "고발", "소비자원", "공정위", "국민신문고"],
        "label": "⚖️ 법적 조치 언급",
    },
    "미디어위협": {
        "level": "CRITICAL",
        "keywords": ["뉴스", "방송", "기자", "SNS 올린다", "인스타", "유튜브 올린다", "커뮤니티", "후기 올린다", "블로그"],
        "label": "📢 미디어/SNS 위협",
    },
    "강성불만": {
        "level": "HIGH",
        "keywords": ["환불 안 해주면", "취소 안 되면", "이게 말이 되냐", "어이없", "황당", "최악", "환불하라", "당장", "사기"],
        "label": "🔥 강성 불만",
    },
    "상담사불만": {
        "level": "HIGH",
        "keywords": ["상담사가", "직원이", "응대가", "무시", "불친절", "매너", "태도", "실력없", "담당자 바꿔"],
        "label": "👤 상담사 태도 불만",
    },
    "반복요청": {
        "level": "HIGH",
        "keywords": ["몇 번을 말해", "계속 말했잖아", "또 연락", "이미 말했는데", "왜 아직도"],
        "label": "🔁 반복 요청",
    },
    "욕설위협": {
        "level": "CRITICAL",
        "keywords": ["씨발", "개새끼", "ㅅㅂ", "ㄱㅅㄲ", "죽여", "찾아간다", "처들어간다"],
        "label": "🚨 욕설/위협",
    },
    "장기미해결": {
        "level": "HIGH",
        "keywords": ["언제까지", "몇 주째", "몇 달째", "아직도 해결", "해결이 안 돼"],
        "label": "⏰ 장기 미해결",
    },
    "개인정보유출": {
        "level": "CRITICAL",
        "keywords": ["개인정보", "정보유출", "해킹", "계정도용", "타인결제", "명의도용"],
        "label": "🔐 개인정보/보안 이슈",
    },
}


@dataclass
class EscalationResult:
    should_escalate: bool
    level: str              # CRITICAL / HIGH / NORMAL
    triggered_rules: list   # 탐지된 규칙 목록
    matched_keywords: list  # 실제 매칭된 키워드
    summary: str            # 슬랙 전송용 요약
    chat_id: str = ""
    message_preview: str = ""
    agent: str = ""
    customer: str = ""


def detect(message_text: str, chat_id: str = "", agent: str = "", customer: str = "") -> EscalationResult:
    """
    메시지 텍스트를 분석해 에스컬레이션 여부와 등급을 반환합니다.
    """
    if not message_text:
        return EscalationResult(False, "NORMAL", [], [], "정상", chat_id, "", agent, customer)

    triggered = []
    matched_kw = []
    highest_level = "NORMAL"
    level_priority = {"CRITICAL": 2, "HIGH": 1, "NORMAL": 0}

    for rule_name, rule in RULES.items():
        for kw in rule["keywords"]:
            if kw in message_text:
                triggered.append({"rule": rule_name, "label": rule["label"], "level": rule["level"]})
                matched_kw.append(kw)
                if level_priority[rule["level"]] > level_priority[highest_level]:
                    highest_level = rule["level"]
                break  # 규칙당 1회만 카운트

    should_escalate = len(triggered) > 0
    preview = message_text[:120].replace("\n", " ") + ("..." if len(message_text) > 120 else "")

    labels = " | ".join(r["label"] for r in triggered)
    summary = f"{labels} — 키워드: {', '.join(matched_kw)}" if triggered else "정상"

    return EscalationResult(
        should_escalate=should_escalate,
        level=highest_level,
        triggered_rules=triggered,
        matched_keywords=matched_kw,
        summary=summary,
        chat_id=chat_id,
        message_preview=preview,
        agent=agent,
        customer=customer,
    )
