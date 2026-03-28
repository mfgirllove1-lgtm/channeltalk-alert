"""
slack_notifier.py
에스컬레이션 결과를 Slack으로 전송합니다.
"""

import requests
import os
from datetime import datetime
from app.detector import EscalationResult

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

LEVEL_COLOR = {
    "CRITICAL": "#E74C3C",  # 빨강
    "HIGH":     "#F39C12",  # 주황
    "NORMAL":   "#27AE60",  # 초록
}

LEVEL_EMOJI = {
    "CRITICAL": "🚨",
    "HIGH":     "⚠️",
    "NORMAL":   "✅",
}


def send_alert(result: EscalationResult, channeltalk_url: str = "") -> bool:
    """
    에스컬레이션 결과를 Slack Block Kit 메시지로 전송합니다.
    Returns True if successful.
    """
    if not SLACK_WEBHOOK_URL:
        print("[SlackNotifier] SLACK_WEBHOOK_URL 환경변수가 설정되지 않았습니다.")
        return False

    emoji = LEVEL_EMOJI.get(result.level, "⚠️")
    color = LEVEL_COLOR.get(result.level, "#F39C12")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    rules_text = "\n".join(f"• {r['label']}" for r in result.triggered_rules)
    keywords_text = "`, `".join(result.matched_keywords)

    chat_link = (
        f"<{channeltalk_url}|채널톡에서 보기>"
        if channeltalk_url
        else f"`{result.chat_id[:16]}...`"
    )

    payload = {
        "attachments": [
            {
                "color": color,
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"{emoji} [{result.level}] 에스컬레이션 감지 — 상위부서 확인 필요",
                        },
                    },
                    {"type": "divider"},
                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*🔗 채팅 ID*\n{chat_link}"},
                            {"type": "mrkdwn", "text": f"*👤 고객*\n{result.customer or '미확인'}"},
                            {"type": "mrkdwn", "text": f"*🧑‍💼 담당 상담사*\n{result.agent or '미배정'}"},
                            {"type": "mrkdwn", "text": f"*🕐 감지 시각*\n{now}"},
                        ],
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*🚩 탐지된 규칙*\n{rules_text}",
                        },
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*🔑 감지 키워드*\n`{keywords_text}`",
                        },
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*💬 메시지 미리보기*\n> {result.message_preview}",
                        },
                    },
                    {"type": "divider"},
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": "🤖 에브리유니즈 CX 에스컬레이션 알림 시스템 | channeltalk-alert",
                            }
                        ],
                    },
                ],
            }
        ]
    }

    try:
        resp = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=5)
        resp.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"[SlackNotifier] 전송 실패: {e}")
        return False
