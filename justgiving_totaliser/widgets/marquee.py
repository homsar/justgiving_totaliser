from html import escape

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QBrush, QColor, QFont, QFontMetrics, QPainter, QTextDocument
from PyQt5.QtWidgets import QWidget

from ..common import format_donor
from ..settings import DEFAULT_FONT
from .mixins import SaveSizeAndPositionOnClose, HideTitleBarOptional


class Marquee(QWidget, SaveSizeAndPositionOnClose, HideTitleBarOptional):
    """Marquee class courtesy of https://stackoverflow.com/questions/36297429/smooth-scrolling-text-in-qlabel"""

    x = 0

    paused = True
    document = None
    _speed = 50
    increment = 1
    timer = None

    text_font = QFont(DEFAULT_FONT, 18)
    _text_colour = QColor(Qt.white)

    @property
    def speed(self):
        return self._speed

    @speed.setter
    def speed(self, speed):
        self._speed = speed
        self.settings.setValue("marquee/speed", speed)
        if self.timer and self.timer.isActive:
            self.timer.setInterval(int((1 / self.speed) * 1000))

    @property
    def text_colour(self):
        return self._text_colour

    @text_colour.setter
    def text_colour(self, colour):
        self._text_colour = colour
        if self.document:
            self.setText(self.document.toPlainText(), reset=False)

    _donors = None
    _donor_iterator = None

    def __init__(self, parent=None):
        super().__init__(parent)
        self.fm = QFontMetrics(self.text_font)
        self.setWindowTitle("JustGiving Marquee")

    @property
    def donors(self):
        return self._donors

    @donors.setter
    def donors(self, donors):
        self._donors = donors

        if self.paused:
            self.setText(format_donor(self.get_next_donor()))
            self.paused = False

    def setText(self, value, reset=True):
        self.document = QTextDocument(self)
        self.document.setDefaultStyleSheet(
            f"body {{ color: {self.text_colour.name()}; }}"
        )
        self.document.setDefaultFont(self.text_font)
        self.document.setHtml("<body>" + escape(value) + "</body>")
        # I multiplied by 1.06 because otherwise the text goes on 2 lines
        self.document.setTextWidth(self.fm.width(value) * 1.06)
        self.document.setUseDesignMetrics(True)

        if reset:
            self.x = self.width()
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.translate)
            self.timer.start(int((1 / self.speed) * 1000))

    def get_next_donor(self):
        if not self._donor_iterator:
            self._donor_iterator = iter(self._donors)
        try:
            return next(self._donor_iterator)
        except StopIteration:
            self._donor_iterator = iter(self._donors)
            return next(self._donor_iterator)

    def translate(self):
        if not self.paused:
            if -self.x < self.document.textWidth():
                self.x -= self.increment
            else:
                self.timer.stop()
                self.setText(format_donor(self.get_next_donor()))
        self.repaint()

    def paintEvent(self, event):
        if self.document:
            p = QPainter(self)
            p.setBrush(QBrush(Qt.white, Qt.SolidPattern))
            p.translate(self.x, 0)
            self.document.drawContents(p)
        return super().paintEvent(event)
