"""API 설정 확인 스크립트 (프로젝트 루트의 .env를 __file__ 기준으로 로드)."""
from pathlib import Path
from dotenv import load_dotenv
import os

ROOT = Path(__file__).resolve().parent
env_path = ROOT / ".env"
loaded = load_dotenv(env_path)
print(f".env 경로: {env_path}")
print(f"파일 존재: {env_path.exists()}, load_dotenv 결과: {loaded}")

key = os.environ.get("GEMINI_API_KEY")
if not key or not str(key).strip():
    print("GEMINI_API_KEY: NOT SET")
    exit(1)
print(f"GEMINI_API_KEY: SET (길이 {len(key.strip())}자)")

try:
    from app.services.summary_service import _get_client
    _get_client()
    print("Gemini 클라이언트 초기화: OK")
except Exception as e:
    print(f"Gemini 클라이언트 초기화: 실패 - {type(e).__name__}: {e}")
    exit(1)
