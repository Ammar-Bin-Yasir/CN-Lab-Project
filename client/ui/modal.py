"""Window chrome for Chatters-owned dialogs (native pickers keep OS chrome)."""

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QDialog, QPushButton


def close_button(dialog, parent=None):
    """A keyboard-accessible close control that matches the in-app modal surface."""
    icon = QPixmap(20, 20)
    icon.fill(Qt.transparent)
    painter = QPainter(icon)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(QPen(QColor('#d1d3dc'), 1.8, Qt.SolidLine, Qt.RoundCap))
    painter.drawLine(5, 5, 15, 15)
    painter.drawLine(15, 5, 5, 15)
    painter.end()
    control = QPushButton(parent or dialog)
    control.setObjectName('dialogClose')
    control.setIcon(QIcon(icon))
    control.setFixedSize(32, 32)
    control.setToolTip('Close')
    control.setAccessibleName('Close dialog')
    control.setAutoDefault(False)
    control.clicked.connect(dialog.reject)
    return control


class InAppDialog(QDialog):
    """A modal with no second title bar; its own visible Close control is required."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self._drag_origin = None

    def draggable(self, widget):
        widget.installEventFilter(self)

    def eventFilter(self, watched, event):
        if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            self._drag_origin = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        elif event.type() == QEvent.MouseMove and self._drag_origin is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_origin)
        elif event.type() == QEvent.MouseButtonRelease:
            self._drag_origin = None
        return super().eventFilter(watched, event)
