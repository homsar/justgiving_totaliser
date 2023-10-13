from datetime import datetime
from functools import partial
from html import escape
from itertools import zip_longest
import sys

import pkg_resources

from PyQt5.QtCore import Qt, QEvent, QRect, QSettings, QSize, QTimer, pyqtSlot
from PyQt5.QtGui import (
    QColor,
    QIcon,
    QPainter,
    QBrush,
    QFont,
    QPen,
    QTextDocument,
    QFontMetrics,
)
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QColorDialog,
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


class SaveSizeAndPositionOnClose:
    def closeEvent(self, event):
        self.settings.setValue(f"{self.key}/width", self.size().width())
        self.settings.setValue(f"{self.key}/height", self.size().height())
        self.settings.setValue(f"{self.key}/left", self.pos().x())
        self.settings.setValue(f"{self.key}/top", self.pos().y())

        event.accept()


class ControllableBackgroundAndTextColour:
    _background_colour = QColor(Qt.magenta)
    _text_colour = QColor(Qt.white)

    @property
    def background_colour(self):
        return self._background_colour

    @background_colour.setter
    def background_colour(self, colour):
        self._background_colour = colour
        self.update_stylesheet()

    @property
    def text_colour(self):
        return self._text_colour

    @text_colour.setter
    def text_colour(self, colour):
        self._text_colour = colour
        self.update_stylesheet()

    def update_stylesheet(self):
        self.setStyleSheet(
            f"color: {self.text_colour.name()};"
            f"background-color: {self.background_colour.name()};"
        )


class Marquee(QWidget, SaveSizeAndPositionOnClose):
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
            self.setText(self.format_donor(self.get_next_donor()))
            self.paused = False

    def format_donor(self, donor):
        return f"{donor.name} donated {donor.amount}{(', commenting “' + donor.comment + '”') if donor.comment else ''}"

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
                self.setText(self.format_donor(self.get_next_donor()))
        self.repaint()

    def paintEvent(self, event):
        if self.document:
            p = QPainter(self)
            p.setBrush(QBrush(Qt.white, Qt.SolidPattern))
            p.translate(self.x, 0)
            self.document.drawContents(p)
        return super().paintEvent(event)


class ProgressBar(QWidget, SaveSizeAndPositionOnClose):
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


class LatestDonor(
    QWidget, SaveSizeAndPositionOnClose, ControllableBackgroundAndTextColour
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
        self.name.setText(f"{donor.name}: {donor.amount}")
        self.message.setText(donor.comment)


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
            self.amount.setText(donor.amount.split()[0])
        else:
            self.amount.setText("")


class DonorList(
    QWidget, SaveSizeAndPositionOnClose, ControllableBackgroundAndTextColour
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


class ShowButton(QPushButton):
    def __init__(self, caption, parent, target):
        super().__init__(caption, parent)
        self.target = target
        self.clicked.connect(self.target.show)


class TimerStatusDisplay(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.layout = QVBoxLayout()

        self.status = QLabel("Inactive")
        self.status.setFont(QFont(DEFAULT_FONT, 48))
        self.status.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.status)

        self.lastcheck = QLabel("Not yet started")
        self.lastcheck.setFont(QFont(DEFAULT_FONT, 14))
        self.lastcheck.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.lastcheck)

        self.setLayout(self.layout)


class StatusDisplayingTimer(QTimer):
    def __init__(self, status_display, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status_display = status_display
        self.timeout.connect(self.update_lastcheck)

    def start(self, *args, **kwargs):
        super().start(*args, **kwargs)
        self.status_display.setStyleSheet("color: #00a000")
        self.status_display.status.setText("Running")

    def stop(self, *args, **kwargs):
        super().stop(*args, **kwargs)
        self.status_display.setStyleSheet("color: #c00000")
        self.status_display.status.setText("Stopped!")

    def update_lastcheck(self, verb=None):
        self.status_display.lastcheck.setText(
            f"Last {verb if verb else 'called'}: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )


class JustGivingTotaliser(QMainWindow):
    """Create the main window that stores all of the widgets necessary for the application."""

    donors = None

    def __init__(self, parent=None):
        """Initialize the components of the main window."""
        super(JustGivingTotaliser, self).__init__(parent)

        self.setWindowTitle("JustGiving Main Menu")
        window_icon = pkg_resources.resource_filename(
            "justgiving_totaliser.images", "ic_insert_drive_file_black_48dp_1x.png"
        )
        self.setWindowIcon(QIcon(window_icon))

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.progress_bar = ProgressBar()
        self.latest_donor = LatestDonor()
        self.donor_list = DonorList()
        self.marquee = Marquee()

        self.layout = QVBoxLayout()

        self.timer_status_display = TimerStatusDisplay()
        self.layout.addWidget(self.timer_status_display)

        for widget, caption in [
            (self.progress_bar, "Progress bar"),
            (self.latest_donor, "Latest donor"),
            (self.donor_list, "Donor list"),
            (self.marquee, "Donor marquee"),
        ]:
            button = ShowButton(caption, self, widget)
            self.layout.addWidget(button)
            widget.show()

        self.central_widget.setLayout(self.layout)

        self.menu_bar = self.menuBar()
        self.about_dialog = AboutDialog()

        self.file_menu()
        self.help_menu()

        self.init_timers()
        self.init_settings()

        self.init_colours()

    def init_timers(self):
        self.timer = StatusDisplayingTimer(self.timer_status_display)
        self.timer.timeout.connect(self.update_data)

        self.repaint_timer = QTimer()
        self.repaint_timer.timeout.connect(self.repaint_all)
        self.repaint_timer.start(60_000)

    def init_settings(self):
        self.settings = QSettings("h0m54r", "justgiving_totaliser")
        self.url = self.settings.value("url", defaultValue=None)
        self.timer_interval = int(
            self.settings.value("timer_interval", defaultValue=60_000)
        )
        if self.url:
            try:
                self.update_data()
            except Exception as ex:
                print("Swallowing exception:", ex)
                print("Resetting url to None just in case")
                self.url = None
            else:
                self.pause(force_resume=True)

        for widget, key, default_width, default_height in [
            (self.progress_bar, "bar", 500, 150),
            (self.latest_donor, "latest", 500, 150),
            (self.donor_list, "list", 250, 250),
            (self.marquee, "marquee", 500, 150),
            (self, "mainWindow", 250, 250),
        ]:
            widget.settings = self.settings
            widget.key = key

            width = int(self.settings.value(f"{key}/width", default_width))
            height = int(self.settings.value(f"{key}/height", default_height))
            left = self.settings.value(f"{key}/left", None)
            top = self.settings.value(f"{key}/top", None)

            widget.resize(width, height)
            if left and top:
                widget.move(int(left), int(top))

        self.marquee.speed = float(self.settings.value("marquee/speed", 50))
        self.donor_list.num_donors = int(
            self.settings.value("donor_list/num_donors", 10)
        )

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
        self.refresh_time_action.setShortcut("CTRL+R")
        self.refresh_time_action.triggered.connect(self.set_refresh_time)

        self.marquee_speed_action = QAction("Set marquee speed", self)
        self.marquee_speed_action.setStatusTip(
            "Set the speed at which the marquee moves."
        )
        self.marquee_speed_action.setShortcut("CTRL+S")
        self.marquee_speed_action.triggered.connect(self.set_marquee_speed)

        self.num_donors_action = QAction("Set number of donations", self)
        self.num_donors_action.setStatusTip("Set the number of donations to display")
        self.num_donors_action.setShortcut("CTRL+N")
        self.num_donors_action.triggered.connect(self.set_num_donors)

        self.exit_action = QAction("Exit Application", self)
        self.exit_action.setStatusTip("Exit the application.")
        self.exit_action.setShortcut("CTRL+Q")
        self.exit_action.triggered.connect(lambda: QApplication.quit())

        self.file_sub_menu.addAction(self.set_url_action)
        self.file_sub_menu.addAction(self.pause_action)
        self.file_sub_menu.addAction(self.refresh_time_action)
        self.file_sub_menu.addAction(self.marquee_speed_action)
        self.file_sub_menu.addAction(self.num_donors_action)
        self.file_sub_menu.addAction(self.exit_action)

    def init_colours(self):
        self.colour_menu = self.menu_bar.addMenu("Colours")
        self.colour_menu_items = []

        for widget, attrname, text, default in [
            (self.progress_bar, "bar_colour", "progress bar", QColor(Qt.green)),
            (
                self.progress_bar,
                "text_colour",
                "progress bar text",
                QColor(Qt.darkGreen),
            ),
            (self.latest_donor, "text_colour", "latest donor text", QColor(Qt.white)),
            (self.donor_list, "text_colour", "donor list text", QColor(Qt.white)),
            (self.marquee, "text_colour", "marquee text", QColor(Qt.white)),
        ]:

            def set_colour(colour, widget, attrname, text):
                colour = QColorDialog.getColor(
                    initial=getattr(widget, attrname),
                    parent=self,
                    title=f"Choose {text} colour",
                )
                if colour.isValid():
                    setattr(widget, attrname, colour)
                    self.settings.setValue(f"{widget.key}/{attrname}", colour)

            action = QAction(f"Set {text} colour")
            action.triggered.connect(
                partial(set_colour, widget=widget, attrname=attrname, text=text)
            )
            self.colour_menu.addAction(action)
            self.colour_menu_items.append(action)

            setattr(
                widget,
                attrname,
                QColor(self.settings.value(f"{widget.key}/{attrname}", default)),
            )

        background_colour_action = QAction("Set window background colour")
        background_colour_action.triggered.connect(self.set_background_colours)
        self.set_background_colours(
            self.settings.value("background_colour", QColor(Qt.magenta))
        )
        self.colour_menu.addAction(background_colour_action)
        self.colour_menu_items.append(background_colour_action)

    def set_background_colours(self, colour=None):
        if not colour:
            colour = QColorDialog.getColor(
                initial=self.background_colour,
                parent=self,
                title="Choose window background colour",
            )
        if colour.isValid():
            self.settings.setValue(f"background_colour", colour)

            for window in self, self.progress_bar, self.marquee:
                window.setStyleSheet(f"background-color: {colour.name()}")

            for window in self, self.latest_donor, self.donor_list:
                window.background_colour = colour

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

    def set_marquee_speed(self):
        marquee_speed, accept = QInputDialog.getDouble(
            self,
            "Enter speed",
            "Enter the speed at which you want the marquee to move."
            "(One pixel every 1 / N seconds.)",
            self.marquee.speed,
        )

        if accept:
            self.marquee.speed = marquee_speed

    def set_num_donors(self):
        num_donors, accept = QInputDialog.getInt(
            self,
            "Enter number of donors",
            "Enter the number of donors to retrieve and display",
            self.donor_list.num_donors,
        )

        if accept:
            self.donor_list.num_donors = num_donors
            self.settings.setValue("donor_list/num_donors", num_donors)

    def update_data(self):
        if self.url:
            self.progress_bar.totals, donors = get_data(
                self.url, len(self.donor_list.donor_widgets)
            )
            self.latest_donor.donor = donors[0]
            self.donor_list.donors = donors[:]
            self.marquee.donors = donors[:]

        self.update()
        self.progress_bar.update()
        self.timer.update_lastcheck(verb="checked")

    def repaint_all(self):
        self.update()
        self.progress_bar.update()
        self.latest_donor.update()
        self.donor_list.update()
        self.marquee.update()

    def pause(self, force_resume=False):
        if not self.timer.isActive() or force_resume:
            self.timer.start(self.timer_interval)
            self.pause_action.setText("Pause")

            # Don't want to wait for timer to time out after resuming
            self.update_data()
        else:
            self.timer.stop()
            self.pause_action.setText("Resume")

    def closeEvent(self, event):
        self.settings.setValue(f"{self.key}/width", self.size().width())
        self.settings.setValue(f"{self.key}/height", self.size().height())
        self.settings.setValue(f"{self.key}/left", self.pos().x())
        self.settings.setValue(f"{self.key}/top", self.pos().y())

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
