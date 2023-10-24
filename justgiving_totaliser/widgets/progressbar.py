from PyQt5.QtCore import Qt, QRect, QSize
from PyQt5.QtGui import QBrush, QFont, QPainter, QPen
from PyQt5.QtWidgets import QWidget

from ..settings import DEFAULT_FONT
from .mixins import SaveSizeAndPositionOnClose, HideTitleBarOptional


class ProgressBar(QWidget, SaveSizeAndPositionOnClose, HideTitleBarOptional):
    totals = None

    _bar_colour = Qt.green
    _text_colour = Qt.darkGreen

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.resize(512, 150)
        self.setWindowTitle("JustGiving Progress Bar")

    @property
    def bar_colour(self):
        return self._bar_colour

    @bar_colour.setter
    def bar_colour(self, colour):
        self._bar_colour = colour
        self.update()

    @property
    def text_colour(self):
        return self._text_colour

    @text_colour.setter
    def text_colour(self, colour):
        self._text_colour = colour
        self.update()

    def minimumSizeHint(self):
        return QSize(0, 100)

    def paintEvent(self, event):
        painter = QPainter(self)

        margin = 20
        box_height = int(self.height() - margin * 2)
        box_width = int(self.width() - margin * 2)

        # Draw background rectangle
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(Qt.white, Qt.SolidPattern))
        painter.drawRect(margin, margin, box_width, box_height)

        # Draw total bar
        if self.totals:
            raised, target, currency = self.totals

            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(self.bar_colour, Qt.SolidPattern))
            painter.drawRect(
                margin, margin, int(min(raised / target, 1) * box_width), box_height
            )

            painter.setPen(self.text_colour)
            painter.setFont(QFont(DEFAULT_FONT, 30))
            painter.drawText(
                QRect(margin, margin, box_width, box_height),
                Qt.AlignCenter,
                f"{currency}{raised} / {currency}{target}",
            )

        # Draw outer rectangle
        painter.setPen(QPen(Qt.black, 2, Qt.SolidLine))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(margin, margin, box_width, box_height)
