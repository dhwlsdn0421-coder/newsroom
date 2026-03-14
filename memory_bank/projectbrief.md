# Project Brief

## 목적
- YouTube URL로 영상 메타데이터(썸네일, 제목, 조회수) 조회 및 고화질 영상 다운로드(병합 후 한 파일 저장).

## 성공 기준
- URL 입력 → 정보 조회·다운로드 정상 동작.
- bestvideo+bestaudio 우선, fallback 후 ffmpeg 병합으로 단일 파일 저장.
