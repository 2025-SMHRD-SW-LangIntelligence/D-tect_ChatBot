# logic.py
import re
from typing import List, Dict, Optional
from openai import OpenAI
from config import (
    SERVICE_BRAND, CTA_URL, CTA_PITCH, EMERGENCY_NUMBER, HELPLINES,
    MODEL_NAME, OPENAI_API_KEY
)

RX_HIGH_RISK = re.compile(
    r"(자살|극단적\s*선택|죽고\s*싶(?:다|어요)?|생을\s*끝(?:내고|내고\s*싶|내고싶)?|"
    r"목숨(?:을)?\s*끊|스스로\s*해치|유서|투신|목매|손목\s*긋|과다\s*복용)",
    re.I
)
RX_VIOLENCE = re.compile(
    r"(살해|죽인?다고|협박|스토킹|따라오(?:고|는)|신상\s*털|유포\s*협박|폭행|폭력|"
    r"성폭행|성폭력|디지털\s*성범죄)",
    re.I
)
RX_LEGAL     = re.compile(r"(고소|고발|법적\s*대응|변호사|명예훼손|모욕|증거|신고|삭제요청|합의|처벌|변호)", re.I)
RX_COUNSEL = re.compile(
    r"(상담|심리|불안|불안해|우울|우울해|불면|공황|위로|"
    r"힘들|힘들어|지쳤|지쳐|무기력|외로워|외로움|쓸쓸|공허|"
    r"짜증|분노|화가|스트레스|멘붕|답답|눈물|울고|슬퍼|슬픔)",
    re.I
)

# 도메인 키워드(포함되면 지식이어도 허용)
RX_DOMAIN_WHITELIST = re.compile(
    r"(사이버불링|사이버 폭력|디지털성범죄|신고|고소|법적\s*대응|증거|보존|차단|유포|명예훼손|모욕|"
    r"상담|심리|불안|우울|위험|112|1366|1388|109|D-tect|디-텍트|변호사|법률)",
    re.I
)

# 오프토픽 지식 패턴 (간단·실용 위주로)
RX_OFFTOPIC_KNOWLEDGE = re.compile(
    r"(코딩|파이썬|python|자바|spring|스프링|자바스크립트|javascript|리액트|sql|에러|버그|"
    r"수학|공식|정의|증명|역사|과학|뉴스|시사|주가|환율|날씨|레시피|요리|여행|번역|문법|"
    r"요약|리뷰|영화|드라마|게임|축구|야구|음악|가사|가수|배우|유튜브|틱톡|인스타|마케팅|"
    r"토익|토플|면접|자소서|이력서|PPT|엑셀|R|MATLAB)",
    re.I
)

# 도메인 키워드(포함되면 지식이어도 허용)
RX_DOMAIN_WHITELIST = re.compile(
    r"(사이버불링|사이버 폭력|디지털성범죄|신고|고소|법적\s*대응|증거|보존|차단|유포|명예훼손|모욕|"
    r"상담|심리|불안|우울|위험|112|1366|1388|109|D-tect|디-텍트|변호사|법률)",
    re.I
)

# 오프토픽 지식 패턴 (간단·실용 위주로)
RX_OFFTOPIC_KNOWLEDGE = re.compile(
    r"(코딩|파이썬|python|자바|spring|스프링|자바스크립트|javascript|리액트|sql|에러|버그|"
    r"수학|공식|정의|증명|역사|과학|뉴스|시사|주가|환율|날씨|레시피|요리|여행|번역|문법|"
    r"요약|리뷰|영화|드라마|게임|축구|야구|음악|가사|가수|배우|유튜브|틱톡|인스타|마케팅|"
    r"토익|토플|면접|자소서|이력서|PPT|엑셀|R|MATLAB)",
    re.I
)

def is_offtopic_knowledge(text: str) -> bool:
    # 도메인 키워드가 있으면 지식이어도 허용
    if RX_DOMAIN_WHITELIST.search(text):
        return False
    # 지식·학습·코딩 등 오프토픽 패턴이면 차단
    return bool(RX_OFFTOPIC_KNOWLEDGE.search(text))




def classify_intent(text: str) -> str:
    if RX_HIGH_RISK.search(text): return "high_risk"
    if RX_VIOLENCE.search(text):  return "violence_risk"
    if RX_LEGAL.search(text):     return "legal"
    if RX_COUNSEL.search(text):   return "counsel"
    return "general"

def safety_banner() -> str:
    lines = [f"⚠️ 응급상황이면 즉시 **{EMERGENCY_NUMBER}**"]
    for t, d in HELPLINES:
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

SYSTEM = (
    "당신은 'D-tect' 사이버불링 상담 챗봇입니다.\n"
    "- 감정 표현에는 공감적으로 4~7문장 내로 간결하게 답합니다.\n"
    "- 일반 지식/학습/코딩/뉴스 등 상담 외 정보 제공은 하지 않습니다(서버에서 별도 차단).\n"
    "- 안전안내(112/상담전화)는 '자살, 죽고 싶다, 목숨을 끊...' 등 명확한 위기 단어가 있을 때만 제시합니다."
    " 단순한 슬픔/힘듦만으로는 안전안내를 넣지 않습니다.\n"
    "- 법률 도움이 필요하면 D-tect 연계를 제안합니다.\n"
)



_client: Optional[OpenAI] = None
def _get_client():
    global _client
    if _client is None:
        if not OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is not set")
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client

def llm_counsel_reply(message: str, history: Optional[List[Dict]]) -> str:
    client = _get_client()
    msgs = [{"role":"system","content":SYSTEM}]
    for t in (history or [])[-6:]:
        role = t.get("role","user")
        content = t.get("content","")
        if content:
            msgs.append({"role": role, "content": content})
    msgs.append({"role":"user","content":message})

    resp = client.chat.completions.create(
        model=MODEL_NAME,
        messages=msgs,
        temperature=0.6,
        max_tokens=400,
    )
    return resp.choices[0].message.content.strip()

def build_response(user_text: str, history: Optional[List[Dict]] = None) -> str:
    intent = classify_intent(user_text)

    if is_offtopic_knowledge(user_text):
        return  (
            "저는 D-tect 사이버불링 상담 챗봇이에요. 일반 지식/학습/코딩/뉴스와 같은 "
            "정보 제공은 하지 않아요.\n"
            "대신 온라인 괴롭힘, 법적 대응, 증거 보존, 심리 지원과 관련된 상담은 도와드릴 수 있어요.\n"
            f"긴급 상황이면 {EMERGENCY_NUMBER}에 즉시 연락하세요."
        )
        

    try:
        reply = llm_counsel_reply(user_text, history)
    except Exception:
        reply = ("말해줘서 고마워요. 지금 느끼는 감정은 충분히 이해받을 가치가 있어요. 원하시면 상황을 조금 더 알려주세요."
        )
    tail = ""    
    if intent in ("high_risk","violence_risk"):
        tail += "\n\n" + safety_banner() + "\n\n" + evidence_tips()
    if intent in ("legal","violence_risk"):
        tail += f"\n\n**{SERVICE_BRAND}**\n{CTA_PITCH}\n👉 {CTA_URL}"
    return reply + tail

# logic.py (아래 함수들을 파일 하단에 추가)
from typing import Deque
from openai import OpenAI
from config import OPENAI_API_KEY, MODEL_NAME


def summarize_turns(turns, prev_summary: str = "") -> str:
    """
    turns: deque/list of {"role": "...", "content": "..."}
    prev_summary: 직전 요약(있으면 더 축약)
    """
    if not OPENAI_API_KEY:
        # 키가 없으면 이전 요약을 그대로 쓰되 너무 길면 앞부분만
        s = prev_summary or ""
        return (s[:600] + " …") if len(s) > 600 else s

    client = OpenAI(api_key=OPENAI_API_KEY)

    convo_text = "\n".join(f"{t['role']}: {t['content']}" for t in turns)
    sys = (
        "다음 대화의 핵심만 5줄 이내의 한국어 문단으로 간결하게 요약해줘. "
        "감정/상태(불안·분노·슬픔 등), 반복되는 주제, 명시적 요청(상담/법률/안전)만 담아. "
        "실명/계정/연락처 등 식별정보는 넣지 마."
    )
    if prev_summary:
        sys += " 아래 '이전 요약'을 더 압축하고 최신 내용까지 반영해 업데이트해."

    messages = [
        {"role": "system", "content": sys},
    ]
    if prev_summary:
        messages.append({"role": "user", "content": f"[이전 요약]\n{prev_summary}"})
    messages.append({"role": "user", "content": f"[대화]\n{convo_text}"})

    r = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=0.2,
        max_tokens=240,
    )
    return r.choices[0].message.content.strip()
