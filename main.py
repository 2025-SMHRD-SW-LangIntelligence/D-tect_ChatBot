# main.py
import os, re
from typing import List, Dict, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict
from dotenv import load_dotenv

from logic import build_response, classify_intent, summarize_turns  # ← 논리/LLM은 logic.py만 사용
from memory import MEMORY

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_NAME     = os.getenv("MODEL_NAME", "gpt-4o-mini")

SERVICE_BRAND = os.getenv("SERVICE_BRAND", "D-tect 법률전문가 연계")
CTA_URL       = os.getenv("CTA_URL", "http://127.0.0.1:8081/api/bot/webhook")
CTA_PITCH     = os.getenv("CTA_PITCH", "법률 도움이 필요하시다면 D-tect 전문 변호사와 바로 연결해 드립니다.")
EMERGENCY_NUMBER = os.getenv("EMERGENCY_NUMBER", "112")
HELPLINES = os.getenv("HELPLINES", "109:자살예방(24시간),1388:청소년상담(24시간),1366:여성긴급(24시간)")




def _parse_helplines(raw:str):
    out=[]
    for tok in (raw or "").split(","):
        if ":" in tok:
            t,d = tok.split(":",1); out.append((t.strip(), d.strip()))
    return out
HELPLINES_TUP = _parse_helplines(HELPLINES)

# HELPLINES_TUP 아래쯤
HELPLINES_TXT = "\n".join([f"• {t}: {d}" for t, d in HELPLINES_TUP])

SYSTEM = f"""당신은 'D-tect' 사이버불링 상담 챗봇입니다.
목적: 온라인 괴롭힘/디지털성범죄에 대한 예방·대응·증거 보존, 법률/심리 지원 안내.
금지: 일반 지식/학습/코딩/뉴스 등 상담 외 질문에는 답하지 말고 역할을 안내합니다.
톤: 공감적·비판단적·간결, 한국어 존댓말만 사용.
긴급 시 즉시 {EMERGENCY_NUMBER} 연락을 권고합니다.
도움 번호:
{HELPLINES_TXT}
법률 연계가 필요하면 '{SERVICE_BRAND}' 안내 링크: {CTA_URL}
"""


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
    

# ===== 의도/위험 감지(룰) =====
RX_HIGH_RISK = re.compile(r"(자살|죽고\s*싶|생을\s*끝|극단|목숨|스스로\s*해치|유서)", re.I)
RX_VIOLENCE  = re.compile(r"(살해|죽인다고|협박|스토킹|따라오|신상털|유포협박|폭행|성폭|디지털성범죄)", re.I)
RX_LEGAL     = re.compile(r"(고소|고발|법적\s*대응|변호사|명예훼손|모욕|증거|신고|삭제요청|합의|처벌)", re.I)
RX_COUNSEL   = re.compile(r"(상담|심리|불안|우울|불면|공황|위로|힘들|괴로워)", re.I)

def classify_intent(text: str) -> str:
    if RX_HIGH_RISK.search(text): return "high_risk"
    if RX_VIOLENCE.search(text):  return "violence_risk"
    if RX_LEGAL.search(text):     return "legal"
    if RX_COUNSEL.search(text):   return "counsel"
    return "general"


def safety_banner() -> str:
    lines = [f"⚠️ 응급상황이면 즉시 **{EMERGENCY_NUMBER}**"]
    for t,d in HELPLINES_TUP:
        lines.append(f"• {t} — {d}")
    return "\n".join(lines)

def evidence_tips() -> str:
    tips = [
        "원본 화면 전체 캡처(시간/날짜 포함).",
        "URL/작성자 ID/게시 시각 기록.",
        "차단 전 캡처 및 HTML 저장(Ctrl+S).",
        "금전피해 시 입금내역·계좌·시간 확보.",
        "클라우드 등 복수 매체로 백업."
    ]
    return "증거 보존 체크리스트:\n- " + "\n- ".join(tips)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["POST","GET","OPTIONS"],
    allow_headers=["*"],
)

@app.get("/")
def health():
    return {"ok": True}

@app.post("/api/bot/message", response_model=ChatOut)
def chat(payload: ChatIn):
    if not payload.message:
        raise HTTPException(status_code=400, detail="message is required")

    # 1) 세션 메모리 로드
    sid = payload.sessionId or "anon"
    mem = MEMORY.get(sid)

    # 2) 유저 발화 저장
    mem.add("user", payload.message)

    # 3) 필요 시 요약 갱신 (예: 10턴마다)
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

    # 7) intent 판별 + 안전/법률 꼬리말(이미 build_response에서 처리하지만 intent도 리턴)
    intent = classify_intent(payload.message)

    return ChatOut(reply=reply, intent=intent)

@app.post("/memory/reset")
def reset_memory(sessionId: str):
    MEMORY.clear(sessionId)
    return {"ok": True}

# 1) /api/bot/message → /chat 과 동일 동작
@app.post("/chat")
async def legacy_endpoint(payload: ChatIn):
    return chat(payload)

# 2) 파비콘 500 없애기 (선택)
from fastapi import Response
@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)

import logging, traceback
from fastapi.responses import JSONResponse

logging.basicConfig(level=logging.INFO)

@app.exception_handler(Exception)
async def all_exception_handler(request, exc):
    logging.error("Unhandled error at %s\n%s", request.url.path, traceback.format_exc())
    return JSONResponse(status_code=500, content={"message": "서버 오류가 발생했습니다.", "detail": str(exc)})
