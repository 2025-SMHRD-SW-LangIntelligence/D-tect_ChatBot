import os
from typing import List, Dict, Optional

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from dotenv import load_dotenv

from logic import build_response, classify_intent, summarize_turns
from memory import MEMORY

load_dotenv()

# 환경 변수
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_NAME     = os.getenv("MODEL_NAME", "gpt-4o-mini")

SERVICE_BRAND  = os.getenv("SERVICE_BRAND", "D-tect 법률전문가 연계")
# 배포에서 노출 방지용(상대경로)
CTA_URL        = os.getenv("CTA_URL", "/api/bot/webhook")
CTA_PITCH      = os.getenv("CTA_PITCH", "법률 도움이 필요하시다면 D-tect 전문 변호사와 바로 연결해 드립니다.")
EMERGENCY_NUMBER = os.getenv("EMERGENCY_NUMBER", "112")

# ===== 요청/응답 모델 =====
class ChatIn(BaseModel):
    message: str
    sessionId: Optional[str] = None
    history: Optional[List[Dict]] = None  # 프론트가 보내면 사용, 아니면 서버 메모리를 사용
    # ❗프론트가 보내는 기타 필드(context 등) 무시
    model_config = ConfigDict(extra="ignore")

class ChatOut(BaseModel):
    reply: str
    intent: str

# ===== FastAPI 앱 =====
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)

@app.get("/")
def health():
    return {"ok": True}

# 메인 엔드포인트
@app.post("/api/bot/message", response_model=ChatOut)
def chat(payload: ChatIn):
    if not payload.message:
        raise HTTPException(status_code=400, detail="message is required")

    # 1) 세션 메모리 로드
    sid = payload.sessionId or "anon"
    mem = MEMORY.get(sid)

    # 2) 유저 발화 저장
    mem.add("user", payload.message)

    # 3) 필요 시 요약 갱신
    mem.maybe_summarize(summarize_turns, threshold=10)

    # 4) LLM history 구성: [요약] + 최근 N턴
    history_for_llm: List[Dict] = []
    if mem.summary:
        history_for_llm.append({"role": "system", "content": f"[요약]\n{mem.summary}"})
    history_for_llm += mem.recent(k=8)

    # 프론트가 history를 직접 보냈다면 합쳐 사용(선택)
    if payload.history:
        history_for_llm += payload.history[-4:]

    # 5) 응답 생성
    reply = build_response(payload.message, history=history_for_llm)

    # 6) 봇 응답 저장
    mem.add("assistant", reply)

    # 7) intent (logic.py 사용)
    intent = classify_intent(payload.message)

    return ChatOut(reply=reply, intent=intent)

# === 프론트 경로와 매칭용 별칭(배포에서 프론트가 /chat/api/… 로 호출할 때) ===
@app.post("/chat/api/bot/message", response_model=ChatOut)
def chat_alias(payload: ChatIn):
    return chat(payload)

# 레거시 호환(원하면 유지)
@app.post("/chat")
async def legacy_endpoint(payload: ChatIn):
    return chat(payload)

# 파비콘 500 방지
@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)

# 단순 세션 초기화(운영에선 비활성/보호 권장)
@app.post("/memory/reset")
def reset_memory(sessionId: str):
    MEMORY.clear(sessionId)
    return {"ok": True}

# 전역 예외 로깅
import logging, traceback
logging.basicConfig(level=logging.INFO)

@app.exception_handler(Exception)
async def all_exception_handler(request, exc):
    logging.error("Unhandled error at %s\n%s", request.url.path, traceback.format_exc())
    return JSONResponse(status_code=500, content={"message": "서버 오류가 발생했습니다.", "detail": str(exc)})
