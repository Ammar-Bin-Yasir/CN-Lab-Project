"""Local Unicode picker; selected characters use the ordinary text protocol."""

import sys
from PySide6.QtGui import QTextDocument, QTextOption
from PySide6.QtWidgets import QDialog, QGridLayout, QPushButton, QTextEdit

EMOJIS = (
    ("😀", "Grinning face"), ("😄", "Smiling face"),
    ("😂", "Face with tears of joy"), ("😊", "Blushing smile"),
    ("😉", "Winking face"), ("😍", "Heart eyes"),
    ("🥳", "Party face"), ("😎", "Sunglasses"),
    ("🤔", "Thinking face"), ("😢", "Crying face"),
    ("😭", "Loudly crying face"), ("😡", "Angry face"),
    ("👍", "Thumbs up"), ("👎", "Thumbs down"),
    ("👏", "Clapping hands"), ("🙌", "Raised hands"),
    ("🙏", "Folded hands"), ("💪", "Flexed arm"),
    ("❤️", "Red heart"), ("💜", "Purple heart"),
    ("🔥", "Fire"), ("✨", "Sparkles"),
    ("🎉", "Party popper"), ("✅", "Check mark"),
    ("❌", "Cross mark"), ("👀", "Eyes"),
    ("💯", "Hundred points"), ("🚀", "Rocket"),
    ("📚", "Books"), ("💻", "Laptop"),
)


def configure_emoji_text(widget):
    if not sys.platform.startswith("linux"):
        return
    # Some Qt/Linux builds cannot draw COLRv1 color glyphs; preserve the text.
    widget.setStyleSheet(
        "font-family: 'Inter', 'Segoe UI', 'Noto Sans', 'Noto Emoji', 'Symbola', sans-serif;"
    )
    document = widget.document() if isinstance(widget, QTextEdit) else widget.findChild(QTextDocument)
    if document is not None:
        option = document.defaultTextOption()
        option.setFlags(option.flags() | QTextOption.DisableEmojiParsing)
        document.setDefaultTextOption(option)


class EmojiPicker(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected = None
        self.setWindowTitle("Choose an emoji")
        grid = QGridLayout(self)
        for index, (emoji, name) in enumerate(EMOJIS):
            # Only the simple picker glyphs request text presentation on Linux.
            glyph = emoji.replace("\ufe0f", "") + "\ufe0e" if sys.platform.startswith("linux") else emoji
            item = QPushButton(glyph)
            item.setObjectName("emojiChoice")
            item.setToolTip(name)
            item.setAccessibleName(name)
            item.setAutoDefault(False)
            item.setMinimumSize(48, 44)
            item.clicked.connect(lambda checked=False, value=emoji: self.choose(value))
            grid.addWidget(item, index // 6, index % 6)
        cancel = QPushButton("Cancel")
        cancel.setAutoDefault(False)
        cancel.clicked.connect(self.reject)
        grid.addWidget(cancel, 5, 0, 1, 6)

    def choose(self, emoji):
        self.selected = emoji
        self.accept()
