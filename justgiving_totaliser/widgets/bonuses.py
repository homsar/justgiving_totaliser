from collections import namedtuple
from decimal import Decimal

from PyQt5.QtGui import QDoubleValidator
from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

SingleBonus = namedtuple("SingleBonus", ["threshold", "bonus"])


class SingleBonusWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.layout = QHBoxLayout()
        self.validator = QDoubleValidator()
        self.validator.setBottom(0)

        self.threshold_label = QLabel("Threshold: ")
        self.layout.addWidget(self.threshold_label)

        self.threshold_input = QLineEdit("0", parent=self)
        self.threshold_input.setValidator(self.validator)
        self.layout.addWidget(self.threshold_input)

        self.bonus_label = QLabel("Bonus hours: ")
        self.layout.addWidget(self.bonus_label)

        self.bonus_input = QLineEdit("0", parent=self)
        self.bonus_input.setValidator(self.validator)
        self.layout.addWidget(self.bonus_input)

        self.delete_button = QPushButton("-", parent=self)
        self.delete_button.clicked.connect(self.delete_me)
        self.layout.addWidget(self.delete_button)

        self.setLayout(self.layout)

    def delete_me(self):
        self.deleteLater()

    @property
    def threshold(self):
        return Decimal(self.threshold_input.text())

    @threshold.setter
    def threshold(self, threshold):
        self.threshold_input.setText(str(threshold))

    @property
    def bonus(self):
        return float(self.bonus_input.text())

    @bonus.setter
    def bonus(self, bonus):
        self.bonus_input.setText(str(bonus))

    @property
    def value(self):
        return SingleBonus(self.threshold, self.bonus)

    @value.setter
    def value(self, value):
        self.threshold, self.bonus = value


class Bonuses(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.layout = QVBoxLayout()

        self.bonus_widgets = []
        self.setLayout(self.layout)

    def add(self):
        bonus_widget = SingleBonusWidget()
        self.bonus_widgets.append(bonus_widget)
        self.layout.addWidget(bonus_widget)
        return bonus_widget

    @property
    def bonuses(self):
        return [widget.value for widget in self.bonus_widgets]

    @bonuses.setter
    def bonuses(self, bonuses):
        while (child := self.layout.takeAt(0)) != None:
            child.widget().deleteLater()

        self.bonus_widgets = []
        for bonus in bonuses:
            self.add().value = bonus
        if not bonuses:
            self.add()


class BonusDialog(QDialog):
    def __init__(self, settings=None, parent=None):
        super().__init__(parent=parent)

        self.setWindowTitle("Set bonuses")
        self.settings = settings
        self.layout = QVBoxLayout()

        self.bonuses_widget = Bonuses()
        self.layout.addWidget(self.bonuses_widget)

        self.add_new_button = QPushButton("+", self)
        self.add_new_button.clicked.connect(self.bonuses_widget.add)
        self.layout.addWidget(self.add_new_button)

        self.cumulative_warning = QLabel(
            "Note: bonuses are added together, they don't replace each other"
        )
        self.layout.addWidget(self.cumulative_warning)

        self.buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)
        self.layout.addWidget(self.buttonbox)

        self.setLayout(self.layout)

    @property
    def bonuses(self):
        return self.bonuses_widget.bonuses

    @bonuses.setter
    def bonuses(self, bonuses):
        self.bonuses_widget.bonuses = bonuses
