"""API 키로 사용 가능한 Gemini 모델 목록 조회 (generateContent 지원만)."""
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")

import os
os.environ.setdefault("GEMINI_MODEL", "")

from google import genai
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"].strip())
print("generateContent 지원 모델:")
for m in client.models.list():
    if hasattr(m, "supported_actions") and m.supported_actions:
        if "generateContent" in m.supported_actions:
            print(" ", m.name)
    elif hasattr(m, "supported_generation_methods"):
        if "generateContent" in (m.supported_generation_methods or []):
            print(" ", getattr(m, "name", m))
