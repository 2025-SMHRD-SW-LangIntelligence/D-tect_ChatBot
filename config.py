from pathlib import Path
import os
from dotenv import load_dotenv


load_dotenv()

SERVICE_BRAND = os.getenv("SERVICE_BRAND", "D-tect 법률전문가 연계").strip()
CTA_URL       = os.getenv("CTA_URL", "http://127.0.0.1:8081/api/bot/webhook").strip()
CTA_PITCH     = os.getenv("CTA_PITCH", "법률 도움이 필요하시다면 D-tect 전문 변호사와 연결해 드립니다.").strip()

EMERGENCY_NUMBER = os.getenv("EMERGENCY_NUMBER", "112")

# 콤마 구분 "번호,설명"
HELPLINES_RAW = [
    os.getenv("HELPLINE_1", "109,자살예방(24h)"),
    os.getenv("HELPLINE_2", "1388,청소년상담(24h)"),
    os.getenv("HELPLINE_3", "1366,여성긴급(24h)")
]
HELPLINES = []
for item in HELPLINES_RAW:
    num, desc = (item.split(",", 1) + [""])[:2]
    HELPLINES.append((num.strip(), desc.strip()))

MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
