"""
main.py
채널톡 Webhook을 수신해 에스컬레이션을 감지하고 Slack 알림을 보냅니다.
"""

import hmac
import hashlib
import os
import logging
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from app.detector import detect
from app.slack_notifier import send_alert

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="채널톡 에스컬레이션 알림 시스템",
    description="에브리유니즈 CX팀 — 문제 상담 자동 감지 & Slack 알림",
    version="1.0.0",
)

CHANNELTALK_WEBHOOK_SECRET = os.getenv("CHANNELTALK_WEBHOOK_SECRET", "")


def verify_signature(body: bytes, signature: str) -> bool:
    """채널톡 Webhook 서명 검증"""
    if not CHANNELTALK_WEBHOOK_SECRET:
        return True  # 개발환경: 시크릿 미설정 시 패스
    expected = hmac.new(
        CHANNELTALK_WEBHOOK_SECRET.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "channeltalk-alert"}


@app.post("/webhook/channeltalk")
async def channeltalk_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    채널톡 Webhook 수신 엔드포인트
    - 메시지 수신 시 에스컬레이션 탐지
    - 감지 시 Slack 알림 발송 (비동기 백그라운드)
    """
    body = await request.body()

    # 서명 검증
    sig = request.headers.get("x-channel-signature", "")
    if CHANNELTALK_WEBHOOK_SECRET and not verify_signature(body, sig):
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event_type = payload.get("type", "")
    logger.info(f"Webhook 수신: type={event_type}")

    # 메시지 이벤트만 처리
    if event_type not in ("message_created", "user_chat_message_created"):
        return JSONResponse({"status": "ignored", "type": event_type})

    # 페이로드 파싱
    message_obj = payload.get("entity", payload.get("message", {}))
    plain_text   = message_obj.get("plainText", message_obj.get("text", ""))
    chat_id      = str(payload.get("chatId", message_obj.get("chatId", "")))
    person_type  = message_obj.get("personType", payload.get("personType", ""))

    # 고객 메시지만 감지 (매니저 메시지 제외)
    if person_type == "manager":
        return JSONResponse({"status": "skipped", "reason": "manager message"})

    # 발신자 정보
    channel_info = payload.get("channel", {})
    agent        = channel_info.get("name", payload.get("agentName", ""))
    customer     = payload.get("userName", payload.get("user", {}).get("name", ""))
    chat_url     = f"https://desk.channel.io/#/channels/{channel_info.get('id','')}/user-chats/{chat_id}"

    # 에스컬레이션 탐지
    result = detect(
        message_text=plain_text,
        chat_id=chat_id,
        agent=agent,
        customer=customer,
    )

    logger.info(f"탐지 결과: chat_id={chat_id}, level={result.level}, escalate={result.should_escalate}")

    if result.should_escalate:
        background_tasks.add_task(send_alert, result, chat_url)
        return JSONResponse({
            "status": "escalated",
            "level": result.level,
            "triggered_rules": [r["rule"] for r in result.triggered_rules],
            "keywords": result.matched_keywords,
        })

    return JSONResponse({"status": "normal"})


@app.post("/test/detect")
async def test_detect(request: Request):
    """
    탐지 로직 테스트용 엔드포인트 (개발/QA용)
    Body: {"text": "테스트 메시지"}
    """
    body = await request.json()
    text = body.get("text", "")
    result = detect(text, chat_id="test-chat", agent="테스터", customer="테스트고객")
    return {
        "should_escalate": result.should_escalate,
        "level": result.level,
        "triggered_rules": result.triggered_rules,
        "matched_keywords": result.matched_keywords,
        "summary": result.summary,
        "preview": result.message_preview,
    }
