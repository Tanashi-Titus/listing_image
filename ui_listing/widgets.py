"""Widget phụ: ô chọn ảnh, thẻ kết quả, dialog xem/sửa ảnh."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog,
    QDialog, QPlainTextEdit, QDialogButtonBox, QWidget,
)

from ui_listing import theme


def _thumb(path: str, w: int, h: int) -> QPixmap:
    pm = QPixmap(str(path))
    if pm.isNull():
        return pm
    return pm.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)


_IMG_EXT = (".png", ".jpg", ".jpeg", ".webp", ".bmp")


class ImagePicker(QFrame):
    """Ô chọn 1 ảnh: nút chọn + xem trước + xóa. Hỗ trợ KÉO-THẢ ảnh vào."""
    changed = Signal()

    def __init__(self, title: str, required: bool = False, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.setAcceptDrops(True)   # cho phép kéo-thả ảnh
        self.path: Optional[str] = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 10)
        lay.setSpacing(6)
        star = " *" if required else ""
        cap = QLabel(f"{title}{star}")
        cap.setObjectName("H2")
        lay.addWidget(cap)
        self.preview = QLabel("Kéo-thả ảnh vào đây\nhoặc bấm Chọn ảnh")
        self.preview.setProperty("muted", True)
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumHeight(96)
        self.preview.setStyleSheet(
            f"border:1px dashed {theme.BORDER}; border-radius:8px; color:{theme.TEXT_MUTED};")
        lay.addWidget(self.preview)
        row = QHBoxLayout()
        self.btn = QPushButton("Chọn ảnh")
        self.btn.clicked.connect(self._pick)
        self.btn_clear = QPushButton("Xóa")
        self.btn_clear.clicked.connect(self._clear)
        row.addWidget(self.btn)
        row.addWidget(self.btn_clear)
        lay.addLayout(row)

    def _pick(self):
        f, _ = QFileDialog.getOpenFileName(
            self, "Chọn ảnh", "", "Ảnh (*.png *.jpg *.jpeg *.webp)")
        if f:
            self.set_path(f)

    def set_path(self, f: str):
        self.path = f
        pm = _thumb(f, 220, 120)
        if not pm.isNull():
            self.preview.setPixmap(pm)
            self.preview.setText("")
        self.changed.emit()

    def _clear(self):
        self.path = None
        self.preview.clear()
        self.preview.setText("Chưa chọn")
        self.changed.emit()

    # --- kéo-thả ảnh ---
    def _first_image_url(self, md):
        if md.hasUrls():
            for u in md.urls():
                f = u.toLocalFile()
                if f and f.lower().endswith(_IMG_EXT):
                    return f
        return None

    def dragEnterEvent(self, e):
        if self._first_image_url(e.mimeData()):
            self.preview.setStyleSheet(
                f"border:2px dashed {theme.ORANGE}; border-radius:8px; color:{theme.ORANGE};")
            e.acceptProposedAction()
        else:
            e.ignore()

    def dragLeaveEvent(self, e):
        self.preview.setStyleSheet(
            f"border:1px dashed {theme.BORDER}; border-radius:8px; color:{theme.TEXT_MUTED};")

    def dropEvent(self, e):
        f = self._first_image_url(e.mimeData())
        self.preview.setStyleSheet(
            f"border:1px dashed {theme.BORDER}; border-radius:8px; color:{theme.TEXT_MUTED};")
        if f:
            self.set_path(f)
            e.acceptProposedAction()


class ResultCard(QFrame):
    """Thẻ 1 ảnh kết quả: xem trước (click phóng to) + nút Sửa."""
    edit_requested = Signal(object)   # phát chính card
    view_requested = Signal(object)

    def __init__(self, result: dict, parent=None):
        super().__init__(parent)
        self.setObjectName("Thumb")
        self.result = result
        self.setFixedWidth(210)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)

        self.img = QLabel()
        self.img.setAlignment(Qt.AlignCenter)
        self.img.setFixedHeight(180)
        self.img.setCursor(Qt.PointingHandCursor)
        self.img.mousePressEvent = lambda e: self.view_requested.emit(self)
        lay.addWidget(self.img)

        cap = QLabel(f"{result.get('label') or result.get('type')}")
        cap.setObjectName("H2")
        cap.setWordWrap(True)
        lay.addWidget(cap)

        self.btn_edit = QPushButton("✎ Sửa ảnh này")
        self.btn_edit.setObjectName("Maroon")
        self.btn_edit.clicked.connect(lambda: self.edit_requested.emit(self))
        lay.addWidget(self.btn_edit)

        self.refresh()

    def refresh(self):
        pm = _thumb(self.result.get("image"), 190, 180)
        if not pm.isNull():
            self.img.setPixmap(pm)
        else:
            self.img.setText("(lỗi ảnh)")


class ImageViewer(QDialog):
    """Xem ảnh phóng to."""
    def __init__(self, path: str, title: str = "Xem ảnh", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(760, 800)
        lay = QVBoxLayout(self)
        lbl = QLabel()
        lbl.setAlignment(Qt.AlignCenter)
        pm = QPixmap(str(path))
        if not pm.isNull():
            lbl.setPixmap(pm.scaled(720, 720, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        lay.addWidget(lbl)


class EditDialog(QDialog):
    """Nhập prompt sửa ảnh (+ ảnh tham chiếu tùy chọn)."""
    def __init__(self, result: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sửa ảnh bằng prompt")
        self.resize(560, 420)
        self.ref_path: Optional[str] = None
        lay = QVBoxLayout(self)

        top = QHBoxLayout()
        self.preview = QLabel()
        self.preview.setFixedSize(180, 180)
        self.preview.setAlignment(Qt.AlignCenter)
        pm = _thumb(result.get("image"), 180, 180)
        if not pm.isNull():
            self.preview.setPixmap(pm)
        top.addWidget(self.preview)
        info = QLabel(
            f"Loại: {result.get('label') or result.get('type')}\n\n"
            "Nhập yêu cầu chỉnh sửa (tiếng Việt/Anh đều được).\n"
            "Ảnh cũ + ngữ cảnh vẫn được ChatGPT nhớ."
        )
        info.setWordWrap(True)
        info.setProperty("muted", True)
        top.addWidget(info, 1)
        lay.addLayout(top)

        lay.addWidget(QLabel("Yêu cầu sửa:"))
        self.prompt = QPlainTextEdit()
        self.prompt.setPlaceholderText(
            "VD: đổi nền sang tông xám tối, làm chữ tiêu đề to hơn, thêm bóng đổ...")
        self.prompt.setFixedHeight(90)
        lay.addWidget(self.prompt)

        refrow = QHBoxLayout()
        self.btn_ref = QPushButton("+ Ảnh tham chiếu (tùy chọn)")
        self.btn_ref.clicked.connect(self._pick_ref)
        self.lbl_ref = QLabel("")
        self.lbl_ref.setProperty("muted", True)
        refrow.addWidget(self.btn_ref)
        refrow.addWidget(self.lbl_ref, 1)
        lay.addLayout(refrow)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText("Gửi sửa")
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def _pick_ref(self):
        f, _ = QFileDialog.getOpenFileName(
            self, "Ảnh tham chiếu", "", "Ảnh (*.png *.jpg *.jpeg *.webp)")
        if f:
            self.ref_path = f
            self.lbl_ref.setText(Path(f).name)

    def get_values(self):
        return self.prompt.toPlainText().strip(), self.ref_path
