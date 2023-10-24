from itertools import zip_longest

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QFontMetrics, QPainter
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from .mixins import (
    SaveSizeAndPositionOnClose,
    ControllableBackgroundAndTextColour,
    HideTitleBarOptional,
)
from ..settings import DEFAULT_FONT
from ..types import NULL_DONOR


class ElidingLabel(QLabel):
    def paintEvent(self, event):
        painter = QPainter(self)
        metrics = QFontMetrics(self.font())
        elided = metrics.elidedText(self.text(), Qt.ElideRight, self.width())
        painter.drawText(self.rect(), self.alignment(), elided)


class SingleDonor(QWidget):
    _donor = None

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.layout = QHBoxLayout()
        self.name = ElidingLabel("")
        self.name.setFont(QFont(DEFAULT_FONT, 24))
        self.name.setMinimumWidth(50)
        self.amount = QLabel("")
        self.amount.setFont(QFont(DEFAULT_FONT, 24))
        self.amount.setAlignment(Qt.AlignVCenter | Qt.AlignRight)

        self.layout.addWidget(self.name)
        self.layout.addWidget(self.amount)

        self.setLayout(self.layout)

    @property
    def donor(self):
        return self._donor

    @donor.setter
    def donor(self, donor):
        self._donor = donor
        self.name.setText(donor.name)
        if donor.amount.split():
            amount = []
            for element in donor.amount.split():
                if element == "+":
                    break
                amount.append(element)

            self.amount.setText(" ".join(amount))
        else:
            self.amount.setText("")


class DonorList(
    QWidget,
    SaveSizeAndPositionOnClose,
    ControllableBackgroundAndTextColour,
    HideTitleBarOptional,
):
    _donors = None

    def __init__(self, num_donors=10, parent=None):
        super().__init__(parent=parent)

        self.resize(200, 250)
        self.num_donors = num_donors
        self.setWindowTitle("JustGiving Donor List")

    @property
    def num_donors(self):
        return self._num_donors

    @num_donors.setter
    def num_donors(self, num_donors):
        self._num_donors = num_donors
        self.set_up_widgets(num_donors)

    def set_up_widgets(self, num_donors):
        if isinstance(self.layout, QVBoxLayout):
            QWidget().setLayout(self.layout)

        self.layout = QVBoxLayout()
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(10, 0, 10, 0)

        self.donor_widgets = []
        for _ in range(num_donors):
            donor_widget = SingleDonor()
            self.donor_widgets.append(donor_widget)
            self.layout.addWidget(donor_widget)

        self.setLayout(self.layout)
        if self.donors:
            self.donors = self.donors

    @property
    def donors(self):
        return self._donors

    @donors.setter
    def donors(self, donors):
        self._donors = donors
        for donor, donor_widget in zip_longest(
            donors[: len(self.donor_widgets)], self.donor_widgets, fillvalue=NULL_DONOR
        ):
            donor_widget.donor = donor
