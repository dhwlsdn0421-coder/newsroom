# Product Context

## 비즈니스 로직
- URL 유효성: youtube.com/watch, youtu.be, Shorts 형식만 허용.
- 조회: yt-dlp extract_info → 썸네일(requests)·제목·조회수 표시.
- 다운로드: 저장 위치는 OS Downloads; bestvideo+bestaudio/best, merge_output_format mp4; 진행 상태(다운로드 중 % / 병합 중 / 완료) 표시.
