"""Local Unicode picker; selected characters use the ordinary text protocol."""

import logging
import sys
from pathlib import Path
from PySide6.QtGui import QFontDatabase, QTextDocument, QTextOption
from PySide6.QtWidgets import QGridLayout, QPushButton, QTextEdit, QLabel
from client.ui.modal import InAppDialog, close_button

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


_color_font_id = None


def _use_color_emoji():
    global _color_font_id
    if not sys.platform.startswith("linux"):
        return True
    if _color_font_id is None:
        # This bitmap font works with Linux Qt builds that leave COLRv1 glyphs blank.
        path = Path(__file__).with_name("assets") / "NotoColorEmoji.ttf"
        _color_font_id = QFontDatabase.addApplicationFont(str(path))
        if _color_font_id >= 0:
            for family in QFontDatabase.applicationFontFamilies(_color_font_id):
                QFontDatabase.addApplicationEmojiFontFamily(family)
        else:
            logging.warning("Color emoji font could not load; using readable text glyphs.")
    return _color_font_id >= 0


def configure_emoji_text(widget):
    """Prefer color; use monochrome only if the bundled Linux font cannot load."""
    if _use_color_emoji():
        return True
    # Preserve readable Unicode if a damaged/incomplete installation lacks the font.
    widget.setStyleSheet(
        "font-family: 'Inter', 'Segoe UI', 'Noto Sans', 'Noto Emoji', 'Symbola', sans-serif;"
    )
    document = widget.document() if isinstance(widget, QTextEdit) else widget.findChild(QTextDocument)
    if document is not None:
        option = document.defaultTextOption()
        option.setFlags(option.flags() | QTextOption.DisableEmojiParsing)
        document.setDefaultTextOption(option)
    return False


class EmojiPicker(InAppDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected = None
        self.setWindowTitle("Choose an emoji")
        color_emoji = configure_emoji_text(self)
        grid = QGridLayout(self)
        heading = QLabel('Choose an emoji')
        heading.setObjectName('fieldLabel')
        self.draggable(heading)
        grid.addWidget(heading, 0, 0, 1, 5)
        grid.addWidget(close_button(self), 0, 5)
        for index, (emoji, name) in enumerate(EMOJIS):
            glyph = emoji if color_emoji else emoji.replace("\ufe0f", "") + "\ufe0e"
            item = QPushButton(glyph)
            item.setObjectName("emojiChoice")
            if not color_emoji:
                configure_emoji_text(item)
            item.setToolTip(name)
            item.setAccessibleName(name)
            item.setAutoDefault(False)
            item.setMinimumSize(48, 44)
            item.clicked.connect(lambda checked=False, value=emoji: self.choose(value))
            grid.addWidget(item, index // 6 + 1, index % 6)
        cancel = QPushButton("Cancel")
        cancel.setAutoDefault(False)
        cancel.clicked.connect(self.reject)
        grid.addWidget(cancel, 6, 0, 1, 6)

    def choose(self, emoji):
        self.selected = emoji
        self.accept()
