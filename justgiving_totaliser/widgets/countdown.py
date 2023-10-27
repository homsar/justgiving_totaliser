from datetime import datetime, timedelta, timezone
import logging

from PyQt5.QtCore import pyqtSignal, Qt, QTimer
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QAction,
    QDateTimeEdit,
    QDialog,
    QDialogButtonBox,
    QInputDialog,
    QLabel,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from .mixins import (
    SaveSizeAndPositionOnClose,
    ControllableBackgroundAndTextColour,
    HideTitleBarOptional,
)
from ..settings import DEFAULT_FONT


class DateTimeDialog(QDialog):
    def __init__(self, default_datetime=None, parent=None):
        super().__init__(parent=parent)

        self.setWindowTitle("Set start time")
        self.layout = QVBoxLayout()

        self.label = QLabel("Pick a time for your event to start")
        self.layout.addWidget(self.label)

        self.datetimepicker = QDateTimeEdit()
        if not default_datetime:
            default_datetime = datetime.now()

        self.datetimepicker.setDateTime(default_datetime)
        self.layout.addWidget(self.datetimepicker)

        self.buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)
        self.layout.addWidget(self.buttonbox)

        self.setLayout(self.layout)


class Countdown(
    QWidget,
    SaveSizeAndPositionOnClose,
    ControllableBackgroundAndTextColour,
    HideTitleBarOptional,
):
    refresh_interval = 250
    event_finish = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.settings = None
        self._start_time = None
        self._target_length = None

        self.bonus_time = []

        self.label = QLabel("...")
        self.label.setFont(QFont(DEFAULT_FONT, 72))
        self.label.setAlignment(Qt.AlignCenter)

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.label)
        self.setLayout(self.layout)

        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_time)

    def set_up_menu(self, menu):
        set_target_length_action = QAction("Set target length", self)
        set_target_length_action.setStatusTip(
            "Set the minimum time of the event, before any bonus and extra time."
        )
        set_target_length_action.triggered.connect(self.prompt_set_target_length)

        start_action = QAction("Start event NOW!", self)
        start_action.setStatusTip(
            "Set the event start time to now and start counting down"
        )
        start_action.triggered.connect(self.start_now)

        set_start_time_action = QAction("Set event start time", self)
        set_start_time_action.setStatusTip("Pick the event start time")
        set_start_time_action.triggered.connect(self.set_start_time)

        extra_time_action = QAction("Add extra time", self)
        extra_time_action.setStatusTip(
            "Add extra time to the event, in addition to any bonus time."
        )
        extra_time_action.triggered.connect(self.prompt_add_extra_time)

        reset_action = QAction("Reset all times", self)
        reset_action.setStatusTip(
            "Reset event start time and duration, and any extra time"
        )
        reset_action.triggered.connect(self.reset)

        self.actions = [
            start_action,
            set_start_time_action,
            set_target_length_action,
            extra_time_action,
            reset_action,
        ]
        for action in self.actions:
            menu.addAction(action)

    def load_settings(self, settings):
        self.settings = settings

        start_time = settings.value("countdown/start_time", None)
        if start_time and not start_time.tzinfo:
            logging.warning("Provided start_time was not time-zone aware.")
            start_time = start_time.astimezone()
        self._start_time = start_time

        self._target_length = settings.value("countdown/target_length", None)
        self._extra_time = settings.value("countdown/extra_time", [])
        self.consider_starting()

    def consider_starting(self):
        if self.start_time and self.target_length:
            self.timer.start(self.refresh_interval)

    def refresh_time(self):
        end_time = (
            self.start_time
            + self.target_length
            + sum(self.bonus_time, timedelta())
            + sum(self.extra_time, timedelta())
        )
        time_left = (end_time - datetime.now(timezone.utc)).total_seconds()
        if time_left < 0:
            if self.label.text() != "FINISHED!":
                self.label.setText("FINISHED!")
                self.event_finish.emit()
        else:
            hours, remainder = divmod(time_left, 60 * 60)
            minutes, seconds = divmod(remainder, 60)
            self.label.setText(f"{int(hours)}:{int(minutes):02}:{int(seconds):02}")

    @property
    def start_time(self):
        return self._start_time

    @start_time.setter
    def start_time(self, start_time):
        if not start_time.tzinfo:
            logging.warning("Provided start_time was not time-zone aware.")
            start_time = start_time.astimezone()
        self._start_time = start_time
        if self.settings:
            self.settings.setValue("countdown/start_time", start_time)
        self.consider_starting()
        logging.info(f"Set start time to {start_time} at {datetime.now()}")

    @property
    def target_length(self):
        return self._target_length

    @target_length.setter
    def target_length(self, target_length):
        self._target_length = target_length
        if self.settings:
            self.settings.setValue("countdown/target_length", target_length)
        self.consider_starting()
        logging.info(f"Set target length to {target_length} at {datetime.now()}")

    @property
    def extra_time(self):
        return self._extra_time

    def add_extra_time(self, extra_time):
        self._extra_time.append(extra_time)
        if self.settings:
            self.settings.setValue("countdown/extra_time", self._extra_time)

    def set_start_time(self):
        if self.start_time is not None:
            doublecheck = QMessageBox.question(
                self,
                "Are you sure?",
                "This will overwrite your existing start time! Are you sure?",
                QMessageBox.Ok | QMessageBox.Cancel,
                QMessageBox.Cancel,
            )
            if doublecheck != QMessageBox.Ok:
                return

        dialog = DateTimeDialog(default_datetime=self.start_time, parent=self)
        if dialog.exec_():
            self.start_time = (
                dialog.datetimepicker.dateTime().toPyDateTime().astimezone()
            )

    def prompt_add_extra_time(self):
        extra_time, accept = QInputDialog.getDouble(
            self,
            "Add time",
            "Enter the amount of time to add, in hours:",
            0,
        )
        if accept:
            self.add_extra_time(timedelta(hours=extra_time))

    def prompt_set_target_length(self):
        default_length = 0
        if self.settings:
            current_length = self.settings.value("countdown/target_length")
            if current_length:
                default_length = current_length.total_seconds() / (60 * 60)

        target_length, accept = QInputDialog.getDouble(
            self,
            "Set target length",
            "Enter the minimum event length, in hours:",
            default_length,
        )
        if accept:
            self.target_length = timedelta(hours=target_length)

    def start_now(self):
        if not self.target_length:
            QMessageBox.warning(
                self, "Can't start", "You can't start until you set a duration."
            )
            return

        if self.start_time is not None:
            doublecheck = QMessageBox.question(
                self,
                "Are you sure?",
                "This will overwrite your existing start time! Are you sure?",
                QMessageBox.Ok | QMessageBox.Cancel,
                QMessageBox.Cancel,
            )
            if doublecheck != QMessageBox.Ok:
                return

        self.start_time = datetime.now(timezone.utc)

    def reset(self):
        doublecheck = QMessageBox.question(
            self,
            "Are you sure?",
            "This will reset your entire setup! Are you sure?",
            QMessageBox.Ok | QMessageBox.Cancel,
            QMessageBox.Cancel,
        )
        if doublecheck != QMessageBox.Ok:
            return

        self.timer.stop()
        self.label.setText("...")

        self.start_time = None
        self.target_length = None
        self._extra_time = []

        if self.settings:
            self.settings.setValue("countdown/extra_time", [])
