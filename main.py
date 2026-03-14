# YouTube Info Viewer - plan.md Phase 1
import os
import re
import sys

# Qt 플랫폼 플러그인 경로 설정 (Windows에서 "no Qt platform plugin could be initialized" 방지)
try:
    import PyQt5
    _qt_platforms = os.path.join(os.path.dirname(PyQt5.__file__), "Qt5", "plugins", "platforms")
    if os.path.isdir(_qt_platforms):
        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = _qt_platforms
except Exception:
    pass

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QLineEdit, QPushButton, QLabel, QMessageBox,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap
import yt_dlp
import requests


def is_valid_youtube_url(url: str) -> bool:
    """사용자가 입력한 URL의 유효성 검사."""
    if not url or not url.strip():
        return False
    patterns = [
        r"(?:https?://)?(?:www\.)?youtube\.com/watch\?v=[\w-]+",
        r"(?:https?://)?(?:www\.)?youtube\.com/shorts/[\w-]+",
        r"(?:https?://)?youtu\.be/[\w-]+",
    ]
    return any(re.search(p, url.strip()) for p in patterns)


def format_view_count(count) -> str:
    """천 단위 구분 기호(,)를 포함한 조회수 표시."""
    if count is None:
        return "0"
    try:
        return f"{int(count):,}"
    except (TypeError, ValueError):
        return "0"


def fetch_video_info(url: str) -> dict | None:
    """yt-dlp로 영상 메타데이터 추출. 실패 시 None."""
    opts = {"quiet": True, "no_warnings": True, "extract_flat": False}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                return None
            return {
                "video_id": info.get("id"),
                "title": info.get("title") or "",
                "view_count": info.get("view_count"),
                "thumbnail_url": info.get("thumbnail"),
            }
    except Exception:
        return None


def load_thumbnail_pixmap(url: str) -> QPixmap | None:
    """requests로 썸네일 이미지 다운로드 후 QPixmap 반환. 실패 시 None."""
    if not url:
        return None
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        pix = QPixmap()
        if pix.loadFromData(resp.content):
            return pix
    except Exception:
        pass
    return None


def get_downloads_dir() -> str:
    """운영체제의 Downloads 폴더 경로. 없으면 현재 디렉터리."""
    if os.name == "nt":
        # Windows: 사용자 폴더\Downloads
        base = os.environ.get("USERPROFILE") or os.path.expanduser("~")
        path = os.path.join(base, "Downloads")
    else:
        path = os.path.join(os.path.expanduser("~"), "Downloads")
    return path if os.path.isdir(path) else os.getcwd()


# 고화질 다운로드: bestvideo+bestaudio 우선, 없으면 자동 fallback. ffmpeg로 병합 후 한 파일로 저장.
DOWNLOAD_FORMAT = "bestvideo+bestaudio/best"
MERGE_OUTPUT_FORMAT = "mp4"


class DownloadWorker(QThread):
    """다운로드를 백그라운드에서 수행하고 진행 상태를 시그널로 전달."""
    progress = pyqtSignal(str)

    def __init__(self, url: str, out_dir: str, parent=None):
        super().__init__(parent)
        self.url = url
        self.out_dir = out_dir

    def run(self):
        try:
            download_finished_count = 0

            def progress_hook(d):
                nonlocal download_finished_count
                if d["status"] == "downloading":
                    total = d.get("total_bytes") or d.get("total_bytes_estimate")
                    if total and total > 0:
                        pct = min(100, 100 * d.get("downloaded_bytes", 0) / total)
                        self.progress.emit(f"다운로드 중... {pct:.0f}%")
                    else:
                        self.progress.emit("다운로드 중...")
                elif d["status"] == "finished":
                    download_finished_count += 1
                    # 영상+음원 각각 끝난 뒤 ffmpeg 병합 단계
                    self.progress.emit("병합 중...")

            opts = {
                "quiet": True,
                "no_warnings": True,
                "outtmpl": os.path.join(self.out_dir, "%(title)s.%(ext)s"),
                "format": DOWNLOAD_FORMAT,
                "merge_output_format": MERGE_OUTPUT_FORMAT,
                "progress_hooks": [progress_hook],
            }
            self.progress.emit("다운로드 준비 중...")
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([self.url])
            self.progress.emit("다운로드 완료")
        except Exception as e:
            self.progress.emit(f"실패: {e!s}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube Info Viewer")
        self.setMinimumSize(420, 520)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # 상단: URL 입력, 조회 버튼
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("YouTube URL 입력...")
        layout.addWidget(self.url_edit)

        self.fetch_btn = QPushButton("정보 조회")
        self.fetch_btn.clicked.connect(self.on_fetch)
        layout.addWidget(self.fetch_btn)

        self.download_btn = QPushButton("다운로드")
        self.download_btn.clicked.connect(self.on_download)
        layout.addWidget(self.download_btn)

        self.download_status = QLabel("")
        self.download_status.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(self.download_status)

        self._download_worker = None  # 참조 유지

        # 중앙: 썸네일 (고정 크기, 비율 유지)
        self.thumb_label = QLabel()
        self.thumb_label.setMinimumHeight(200)
        self.thumb_label.setAlignment(Qt.AlignCenter)
        self.thumb_label.setStyleSheet("background: #1a1a1a; border: 1px solid #333;")
        self.thumb_label.setText("썸네일이 여기에 표시됩니다.")
        self.thumb_label.setScaledContents(False)
        layout.addWidget(self.thumb_label)

        # 하단: 제목(볼드, 자동 줄바꿈), 조회수(색상 구분)
        self.title_label = QLabel("제목")
        self.title_label.setWordWrap(True)
        font = self.title_label.font()
        font.setBold(True)
        self.title_label.setFont(font)
        layout.addWidget(self.title_label)

        self.views_label = QLabel("조회수")
        self.views_label.setStyleSheet("color: #666;")
        layout.addWidget(self.views_label)

        layout.addStretch()

    def on_fetch(self):
        url = self.url_edit.text().strip()
        if not is_valid_youtube_url(url):
            QMessageBox.warning(
                self,
                "입력 오류",
                "유효한 YouTube URL을 입력해 주세요.\n(youtube.com, youtu.be, Shorts 등)",
            )
            return

        self.fetch_btn.setEnabled(False)
        self.thumb_label.setText("조회 중...")
        self.title_label.setText("")
        self.views_label.setText("")
        QApplication.processEvents()

        info = fetch_video_info(url)
        if not info:
            self.fetch_btn.setEnabled(True)
            self.thumb_label.setText("썸네일이 여기에 표시됩니다.")
            QMessageBox.warning(
                self,
                "조회 실패",
                "영상을 찾을 수 없거나 네트워크 오류가 발생했습니다.",
            )
            return

        # 썸네일 로드 및 표시
        thumb_url = info.get("thumbnail_url")
        pix = load_thumbnail_pixmap(thumb_url) if thumb_url else None
        if pix and not pix.isNull():
            scaled = pix.scaled(400, 225, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.thumb_label.setPixmap(scaled)
            self.thumb_label.setText("")
        else:
            self.thumb_label.setText("이미지를 불러올 수 없습니다.")
            self.thumb_label.setPixmap(QPixmap())

        self.title_label.setText(info.get("title") or "(제목 없음)")
        self.views_label.setText(f"조회수: {format_view_count(info.get('view_count'))}")
        self.fetch_btn.setEnabled(True)

    def on_download(self):
        url = self.url_edit.text().strip()
        if not is_valid_youtube_url(url):
            QMessageBox.warning(
                self,
                "입력 오류",
                "유효한 YouTube URL을 입력해 주세요.",
            )
            return
        out_dir = get_downloads_dir()
        self.download_btn.setEnabled(False)
        self.download_status.setText("준비 중...")
        self._download_worker = DownloadWorker(url, out_dir, self)
        self._download_worker.progress.connect(self._on_download_progress)
        self._download_worker.finished.connect(self._on_download_finished)
        self._download_worker.start()

    def _on_download_progress(self, text: str):
        self.download_status.setText(text)

    def _on_download_finished(self):
        self.download_btn.setEnabled(True)
        if "실패" in self.download_status.text():
            QMessageBox.warning(self, "다운로드 실패", self.download_status.text())
        elif "완료" in self.download_status.text():
            QMessageBox.information(
                self,
                "다운로드",
                f"저장 위치: {get_downloads_dir()}",
            )


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
