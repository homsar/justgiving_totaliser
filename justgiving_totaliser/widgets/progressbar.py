from PyQt5.QtCore import Qt, QRect, QSize
from PyQt5.QtGui import QBrush, QFont, QPainter, QPen
from PyQt5.QtWidgets import QLabel, QVBoxLayout, QWidget

from ..settings import DEFAULT_FONT
from .mixins import (
    SaveSizeAndPositionOnClose,
    HideTitleBarOptional,
    ControllableBackgroundAndTextColour,
)


class ProgressBar(QWidget):
    totals = None
    next_threshold = None

    _bar_colour = Qt.green
    _text_colour = Qt.darkGreen

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
        bottom_margin = 5
        box_height = int(self.height() - margin - bottom_margin)
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

            # Draw next threshold
            if self.next_threshold and self.next_threshold <= target:
                painter.setPen(QPen(self.bar_colour, 2, Qt.DashLine))
                painter.setBrush(Qt.NoBrush)
                line_x = int(margin + box_width * self.next_threshold / target)
                painter.drawLine(line_x, margin, line_x, margin + box_height)

        # Draw outer rectangle
        painter.setPen(QPen(Qt.black, 2, Qt.SolidLine))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(margin, margin, box_width, box_height)


class ProgressBarWindow(
    QWidget,
    SaveSizeAndPositionOnClose,
    HideTitleBarOptional,
    ControllableBackgroundAndTextColour,
):
    _totals = None
    _next_threshold = None

    _bar_colour = Qt.green
    _text_colour = Qt.darkGreen

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.resize(512, 150)
        self.setWindowTitle("JustGiving Progress Bar")

        self.layout = QVBoxLayout()

        self.progress_bar = ProgressBar()
        self.layout.addWidget(self.progress_bar)

        self.next_threshold_label = QLabel("")
        self.next_threshold_label.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        self.next_threshold_label.setFont(QFont(DEFAULT_FONT, 18))
        self.layout.addWidget(self.next_threshold_label)

        self.setLayout(self.layout)

    @property
    def bar_colour(self):
        return self._bar_colour

    @bar_colour.setter
    def bar_colour(self, colour):
        self.progress_bar.bar_colour = colour
        self._bar_colour = colour
        self.update()

    @property
    def bar_text_colour(self):
        return self._bar_text_colour

    @bar_text_colour.setter
    def bar_text_colour(self, colour):
        self.progress_bar.text_colour = colour
        self._bar_text_colour = colour
        self.update()

    @property
    def totals(self):
        return self._totals

    @totals.setter
    def totals(self, totals):
        self._totals = totals
        self.progress_bar.totals = totals
        self.next_threshold = self.next_threshold

    @property
    def next_threshold(self):
        return self._next_threshold

    @next_threshold.setter
    def next_threshold(self, next_threshold):
        self._next_threshold = next_threshold
        self.progress_bar.next_threshold = next_threshold

        if self.totals and next_threshold:
            raised, target, currency = self.totals
            left_to_next_threshold = next_threshold - raised
            self.next_threshold_label.setText(
                f"{currency}{left_to_next_threshold} left to next bonus"
            )
