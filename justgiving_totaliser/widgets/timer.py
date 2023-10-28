from datetime import datetime

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QLabel, QVBoxLayout, QWidget

from ..settings import DEFAULT_FONT


class TimerStatusDisplay(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.layout = QVBoxLayout()

        self._status = QLabel("Inactive")
        self._status.setFont(QFont(DEFAULT_FONT, 48))
        self._status.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self._status)

        self._last_check = QLabel("Not yet started")
        self._last_check.setFont(QFont(DEFAULT_FONT, 14))
        self._last_check.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self._last_check)

        self.setLayout(self.layout)

    @property
    def colour(self):
        return self._colour

    @colour.setter
    def colour(self, colour):
        self._colour = colour
        self.setStyleSheet(f"color: {colour}")

    @property
    def status(self):
        return self._status.text

    @status.setter
    def status(self, text):
        self._status.setText(text)

    @property
    def last_check(self):
        return self._last_check.text

    @last_check.setter
    def last_check(self, text):
        self._last_check.setText(text)


class StatusDisplayingTimer(QTimer):
    _colour = None
    last_check = "never"

    def __init__(self, status_display, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status_display = status_display
        self.timeout.connect(self.update_last_check)

    def start(self, *args, **kwargs):
        super().start(*args, **kwargs)
        self.status_display.colour = "#00a000"
        self.status_display.status = "Running"

    def stop(self, *args, **kwargs):
        super().stop(*args, **kwargs)
        self.status_display.colour = "#c00000"
        self.status_display.status = "Stopped!"

    def update_last_check(self, verb=None, success=False):
        self.status_display.last_check = (
            f"Last {verb if verb else 'called'}: {self.last_check}"
        )
        if success:
            self.status_display.status = "Running"
            self.last_check = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.status_display.colour = "#00a000"

    def update_failedcheck(self, verb=None):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.status_display.status = "Attempting to connect"
        self.status_display.last_check = (
            f"Update at {now} failed. Last successfully "
            f"{verb if verb else 'called'} at {self.last_check}"
        )
        self.status_display.colour = "#606000"
