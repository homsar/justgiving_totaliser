from itertools import zip_longest
import sys

import pkg_resources

from PyQt5.QtCore import Qt, QRect, QSettings, QSize, QTimer
from PyQt5.QtGui import QIcon, QPainter, QBrush, QFont, QPen
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QDesktopWidget,
    QDialog,
    QInputDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .scrape import get_data, NULL_DONOR

DEFAULT_FONT = "Arial"


def closeEvent(self, event):
    self.settings.setValue(f"{self.key}/width", self.size().width())
    self.settings.setValue(f"{self.key}/height", self.size().height())
    self.settings.setValue(f"{self.key}/left", self.pos().x())
    self.settings.setValue(f"{self.key}/top", self.pos().y())

    event.accept()


class ProgressBar(QWidget):
    totals = None

    closeEvent = closeEvent

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.resize(512, 150)

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
            painter.setBrush(QBrush(Qt.green, Qt.SolidPattern))
            painter.drawRect(
                margin, margin, int(min(raised / target, 1) * box_width), box_height
            )

            painter.setPen(Qt.darkGreen)
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


class LatestDonor(QWidget):
    _donor = None

    closeEvent = closeEvent

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

    @property
    def donor(self):
        return self._donor

    @donor.setter
    def donor(self, donor):
        self._donor = donor
        self.name.setText(f"{donor.name}: {donor.amount}")
        self.message.setText(donor.comment)


class SingleDonor(QWidget):
    _donor = None

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.layout = QHBoxLayout()
        self.name = QLabel("")
        self.name.setFont(QFont(DEFAULT_FONT, 24))
        self.amount = QLabel("")
        self.amount.setFont(QFont(DEFAULT_FONT, 24))
        self.amount.setAlignment(Qt.AlignRight)

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
            self.amount.setText(donor.amount.split()[0])
        else:
            self.amount.setText("")


class DonorList(QWidget):
    _donors = None

    closeEvent = closeEvent

    def __init__(self, num_donors=5, parent=None):
        super().__init__(parent=parent)

        self.resize(200, 250)

        self.layout = QVBoxLayout()
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(10, 0, 10, 0)

        self.donor_widgets = []
        for _ in range(num_donors):
            donor_widget = SingleDonor()
            self.donor_widgets.append(donor_widget)
            self.layout.addWidget(donor_widget)

        self.setLayout(self.layout)

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


class ShowButton(QPushButton):
    def __init__(self, caption, parent, target):
        super().__init__(caption, parent)
        self.target = target
        self.clicked.connect(self.target.show)


class JustGivingTotaliser(QMainWindow):
    """Create the main window that stores all of the widgets necessary for the application."""

    donors = None

    def __init__(self, parent=None):
        """Initialize the components of the main window."""
        super(JustGivingTotaliser, self).__init__(parent)

        self.setWindowTitle("JustGivingTotaliser")
        window_icon = pkg_resources.resource_filename(
            "justgiving_totaliser.images", "ic_insert_drive_file_black_48dp_1x.png"
        )
        self.setWindowIcon(QIcon(window_icon))

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.progress_bar = ProgressBar()
        self.latest_donor = LatestDonor()
        self.donor_list = DonorList()

        self.layout = QVBoxLayout()

        for widget, caption in [
                (self.progress_bar, "Progress bar"),
                (self.latest_donor, "Latest donor"),
                (self.donor_list, "Donor list"),
        ]:
            button = ShowButton(caption, self, widget)
            self.layout.addWidget(button)
            widget.show()

        self.central_widget.setLayout(self.layout)

        self.menu_bar = self.menuBar()
        self.about_dialog = AboutDialog()

        self.file_menu()
        self.help_menu()

        self.init_timer()
        self.init_settings()

    def init_timer(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_data)

    def init_settings(self):
        self.settings = QSettings("h0m54r", "justgiving_totaliser")
        self.url = self.settings.value("url", defaultValue=None)
        self.timer_interval = self.settings.value("timer_interval", defaultValue=60_000)
        if self.url:
            try:
                self.update_data()
            except Exception:
                self.url = None
            else:
                self.pause(force_resume=True)

        for widget, key, width, height in [
                (self.progress_bar, "bar", 500, 150),
                (self.latest_donor, "latest", 500, 150),
                (self.donor_list, "list", 250, 250),
                (self, "mainWindow", 250, 250),
        ]:
            widget.settings = self.settings
            widget.key = key

            width = self.settings.value(f"{key}/width", width)
            height = self.settings.value(f"{key}/height", height)
            left = self.settings.value(f"{key}/left", None)
            top = self.settings.value(f"{key}/top", None)

            widget.resize(width, height)
            if left and top:
                widget.move(left, top)

    def file_menu(self):
        """Create a file submenu with an Open File item that opens a file dialog."""
        self.file_sub_menu = self.menu_bar.addMenu("Options")

        self.set_url_action = QAction("Set URL", self)
        self.set_url_action.setStatusTip("Pick the JustGiving page to scrape.")
        self.set_url_action.setShortcut("CTRL+U")
        self.set_url_action.triggered.connect(self.set_url)

        self.pause_action = QAction("Pause", self)
        self.pause_action.setStatusTip("Pause/resume scraping")
        self.pause_action.setShortcut("CTRL+P")
        self.pause_action.triggered.connect(self.pause)

        self.refresh_time_action = QAction("Set refresh time", self)
        self.refresh_time_action.setStatusTip(
            "Set the amount of time to wait between updates."
        )
        self.refresh_time_action.setShortcut("CTRL+U")
        self.refresh_time_action.triggered.connect(self.set_refresh_time)

        self.exit_action = QAction("Exit Application", self)
        self.exit_action.setStatusTip("Exit the application.")
        self.exit_action.setShortcut("CTRL+Q")
        self.exit_action.triggered.connect(lambda: QApplication.quit())

        self.file_sub_menu.addAction(self.set_url_action)
        self.file_sub_menu.addAction(self.pause_action)
        self.file_sub_menu.addAction(self.refresh_time_action)
        self.file_sub_menu.addAction(self.exit_action)

    def help_menu(self):
        """Create a help submenu with an About item tha opens an about dialog."""
        self.help_sub_menu = self.menu_bar.addMenu("Help")

        self.about_action = QAction("About", self)
        self.about_action.setStatusTip("About the application.")
        self.about_action.setShortcut("CTRL+H")
        self.about_action.triggered.connect(lambda: self.about_dialog.exec_())

        self.help_sub_menu.addAction(self.about_action)

    def set_url(self):
        url, accept = QInputDialog.getText(
            self, "Enter URL", "Enter the JustGiving URL to scrape:"
        )

        if accept:
            self.url = url
            self.settings.setValue("url", url)
            self.pause(force_resume=True)
            self.update_data()

    def set_refresh_time(self):
        refresh_time, accept = QInputDialog.getDouble(
            self,
            "Enter time",
            "Enter the time to wait between refreshes, in seconds:",
            self.timer_interval / 1000,
        )

        if accept:
            self.timer_interval = int(refresh_time * 1000)
            self.settings.setValue("timer_interval", self.timer_interval)
            if self.timer.isActive():
                self.timer.stop()
                self.timer.start(self.timer_interval)

    def update_data(self):
        if self.url:
            self.progress_bar.totals, donors = get_data(self.url)
            self.latest_donor.donor = donors[0]
            self.donor_list.donors = donors[:]

        self.update()

    def pause(self, force_resume=False):
        if not self.timer.isActive() or force_resume:
            self.timer.start(self.timer_interval)
            self.pause_action.setText("Pause")
        else:
            self.timer.stop()
            self.pause_action.setText("Resume")

    def closeEvent(self, event):
        QApplication.closeAllWindows()
        event.accept()


class AboutDialog(QDialog):
    """Create the necessary elements to show helpful text in a dialog."""

    def __init__(self, parent=None):
        """Display a dialog that shows application information."""
        super(AboutDialog, self).__init__(parent)

        self.setWindowTitle("About")
        help_icon = pkg_resources.resource_filename(
            "justgiving_totaliser.images", "ic_help_black_48dp_1x.png"
        )
        self.setWindowIcon(QIcon(help_icon))
        self.resize(300, 200)

        author = QLabel("Tachibana Kanade")
        author.setAlignment(Qt.AlignCenter)

        icons = QLabel("Material design icons created by Google")
        icons.setAlignment(Qt.AlignCenter)

        github = QLabel("GitHub: homsar")
        github.setAlignment(Qt.AlignCenter)

        self.layout = QVBoxLayout()
        self.layout.setAlignment(Qt.AlignVCenter)

        self.layout.addWidget(author)
        self.layout.addWidget(icons)
        self.layout.addWidget(github)

        self.setLayout(self.layout)


def main():
    application = QApplication(sys.argv)
    window = JustGivingTotaliser()
    desktop = QDesktopWidget().availableGeometry()
    width = (desktop.width() - window.width()) // 2
    height = (desktop.height() - window.height()) // 2
    window.show()
    window.move(width, height)
    sys.exit(application.exec_())
