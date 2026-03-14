# System Patterns

## 아키텍처 / 패턴
- 단일 진입점: main.py (MainWindow + DownloadWorker QThread).
- UI: QVBoxLayout, URL 입력 → 정보 조회 / 다운로드 버튼 → 썸네일·제목·조회수·다운로드 상태 라벨.
- 다운로드: 백그라운드 QThread, progress_hook으로 시그널 전달, 상태 메시지 갱신.
