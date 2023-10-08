import sys

import pkg_resources

from PyQt5.QtCore import Qt, QRect, QSettings, QTimer
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
    QVBoxLayout,
    QWidget,
)

from .scrape import get_data


class JustGivingTotaliser(QMainWindow):
    """Create the main window that stores all of the widgets necessary for the application."""

    timer_interval = 60_000
    url = None

    raised = None
    target = None
    currency = None

    def __init__(self, parent=None):
        """Initialize the components of the main window."""
        super(JustGivingTotaliser, self).__init__(parent)
        self.resize(1024, 150)
        self.setWindowTitle("JustGivingTotaliser")
        window_icon = pkg_resources.resource_filename(
            "justgiving_totaliser.images", "ic_insert_drive_file_black_48dp_1x.png"
        )
        self.setWindowIcon(QIcon(window_icon))

        self.widget = QWidget()
        self.layout = QHBoxLayout(self.widget)

        self.menu_bar = self.menuBar()
        self.about_dialog = AboutDialog()

        self.file_menu()
        self.help_menu()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_data)

        self.settings = QSettings("h0m54r", "justgiving_totaliser")
        self.url = self.settings.value("url", defaultValue=None)
        if self.url:
            self.pause(force_resume=True)
            self.update_data()

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
            self, "Enter time", "Enter the time to wait between refreshes, in seconds:"
        )

        if accept:
            self.timer_interval = refresh_time * 1000
            if self.timer.isActive():
                self.timer.stop()
                self.timer.start(self.timer_interval)

    def update_data(self):
        if self.url:
            self.raised, self.target, self.currency = get_data(self.url)

        self.update()

    def pause(self, force_resume=False):
        if not self.timer.isActive() or force_resume:
            self.timer.start(self.timer_interval)
            self.pause_action.setText("Pause")
        else:
            self.timer.stop()
            self.pause_action.setText("Resume")

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
        if self.raised and self.target:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(Qt.green, Qt.SolidPattern))
            painter.drawRect(
                margin, margin, int((self.raised / self.target) * box_width), box_height
            )

            painter.setPen(Qt.darkGreen)
            painter.setBrush(QBrush(Qt.darkGreen, Qt.SolidPattern))
            painter.setFont(QFont("Arial", 30))
            painter.drawText(
                QRect(margin, margin, box_width, box_height),
                Qt.AlignCenter,
                f"{self.currency}{self.raised} / {self.currency}{self.target}",
            )

        # Draw outer rectangle
        painter.setPen(QPen(Qt.black, 2, Qt.SolidLine))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(margin, margin, box_width, box_height)


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
