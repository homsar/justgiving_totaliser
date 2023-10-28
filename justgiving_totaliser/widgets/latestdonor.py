from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QLabel, QVBoxLayout, QWidget

from ..settings import DEFAULT_FONT
from .mixins import (
    SaveSizeAndPositionOnClose,
    ControllableBackgroundAndTextColour,
    HideTitleBarOptional,
)


class LatestDonor(
    QWidget,
    SaveSizeAndPositionOnClose,
    ControllableBackgroundAndTextColour,
    HideTitleBarOptional,
):
    _donor = None

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.resize(250, 50)

        self.layout = QVBoxLayout()
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.name = QLabel("")
        self.name.setAlignment(Qt.AlignCenter)
        self.name.setFont(QFont(DEFAULT_FONT, 36))
        self.layout.addWidget(self.name)

        message_font = QFont(DEFAULT_FONT, 18)
        message_font.setItalic(True)
        self.message = QLabel("")
        self.message.setAlignment(Qt.AlignCenter)
        self.message.setFont(message_font)
        self.layout.addWidget(self.message)

        self.setLayout(self.layout)
        self.setWindowTitle("JustGiving Latest Donor")

    @property
    def donor(self):
        return self._donor

    @donor.setter
    def donor(self, donor):
        self._donor = donor
        if donor.amount is None:
            self.name.setText(f"{donor.name}")
        else:
            self.name.setText(f"{donor.name}: {donor.amount}")
        self.message.setText(donor.comment)
