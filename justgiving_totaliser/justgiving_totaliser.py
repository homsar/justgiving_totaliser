from datetime import timedelta
from decimal import Decimal
from functools import partial
import logging
import sys

import pkg_resources

from PyQt5.QtCore import Qt, QEvent, QSettings, QThreadPool, QTimer
from PyQt5.QtGui import QColor, QIcon
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QColorDialog,
    QDesktopWidget,
    QInputDialog,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .announcer import Announcement, Announcer
from .scrape import DataGetter, fake_get_data, get_data
from .settings import DEFAULT_FONT
from .types import Donor, Total

from .widgets.about import AboutDialog
from .widgets.bonuses import BonusDialog
from .widgets.countdown import Countdown
from .widgets.donorlist import DonorList
from .widgets.latestdonor import LatestDonor
from .widgets.marquee import Marquee
from .widgets.progressbar import ProgressBarWindow
from .widgets.timer import StatusDisplayingTimer, TimerStatusDisplay


class ShowButton(QPushButton):
    def __init__(self, caption, parent, target):
        super().__init__(caption, parent)
        self.target = target
        self.clicked.connect(self.target.show)


class JustGivingTotaliser(QMainWindow):
    """Create the main window that stores all of the widgets necessary for the application."""

    donors = None

    def __init__(self, debug=False, parent=None):
        """Initialize the components of the main window."""
        super(JustGivingTotaliser, self).__init__(parent)

        self.setWindowTitle("JustGiving Main Menu")
        window_icon = pkg_resources.resource_filename(
            "justgiving_totaliser.images", "ic_insert_drive_file_black_48dp_1x.png"
        )
        self.setWindowIcon(QIcon(window_icon))

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.progress_bar = ProgressBarWindow()
        self.latest_donor = LatestDonor()
        self.donor_list = DonorList()
        self.marquee = Marquee()
        self.countdown = Countdown()
        self.bonuses = []

        self.layout = QVBoxLayout()

        self.timer_status_display = TimerStatusDisplay()
        self.layout.addWidget(self.timer_status_display)

        for widget, caption in [
            (self.progress_bar, "Progress bar"),
            (self.latest_donor, "Latest donor"),
            (self.donor_list, "Donor list"),
            (self.marquee, "Donor marquee"),
            (self.countdown, "Countdown"),
        ]:
            button = ShowButton(caption, self, widget)
            self.layout.addWidget(button)
            widget.show()

        self.central_widget.setLayout(self.layout)

        self.menu_bar = self.menuBar()
        self.about_dialog = AboutDialog()

        self.file_menu()
        self.time_menu()
        self.audio_menu()
        self.help_menu()
        if debug:
            logging.debug("Enabling debug menu")
            self.debug_menu()

        self.init_timers()
        self.init_settings()

        self.init_colours()
        self.init_announcements()

    def init_announcements(self):
        self.stop_announcement_action = QAction("Stop announcement", self)
        self.stop_announcement_action.setStatusTip(
            "Stop any current announcements from playing"
        )
        self.stop_announcement_action.setShortcut("CTRL+K")
        self.stop_announcement_action.triggered.connect(self.stop_all_announcements)
        self.audio_menu.addAction(self.stop_announcement_action)

        tts_enabled = self.settings.value("use_voice", True)
        self.announcer = Announcer(tts=tts_enabled)

        self.use_voice_action = QAction("Use TTS for announcements", self)
        self.use_voice_action.setCheckable(True)
        self.use_voice_action.setStatusTip("Enable reading announcements with TTS")
        self.use_voice_action.setChecked(tts_enabled)
        self.use_voice_action.toggled.connect(
            lambda checked: self.announcer.toggle_voice(checked)
        )
        self.use_voice_action.toggled.connect(
            lambda checked: self.settings.setValue("use_voice", checked)
        )
        self.audio_menu.addAction(self.use_voice_action)

        self.countdown.event_finish.connect(
            lambda: self.announcer.announce(
                Announcement(
                    fanfare="end",
                    message="Congratulations! You did it! Now go to bed!",
                )
            )
        )

    def init_timers(self):
        self.thread_pool = QThreadPool()

        self.timer = StatusDisplayingTimer(self.timer_status_display)
        self.timer.timeout.connect(self.start_update_data)

        self.repaint_timer = QTimer()
        self.repaint_timer.timeout.connect(self.repaint_all)
        self.repaint_timer.start(60_000)

    def init_settings(self):
        self.settings = QSettings("h0m54r", "justgiving_totaliser")
        self.url = self.settings.value("url", defaultValue=None)
        self.default_target = self.settings.value("default_target", defaultValue=1000)
        self.timer_interval = int(
            self.settings.value("timer_interval", defaultValue=60_000)
        )
        if self.url:
            try:
                self.start_update_data(synchronous=True)
            except Exception as ex:
                print("Swallowing exception:", ex)
            else:
                self.pause(force_resume=True)

        for widget, key, default_width, default_height in [
            (self.progress_bar, "bar", 500, 150),
            (self.latest_donor, "latest", 500, 150),
            (self.donor_list, "list", 250, 250),
            (self.marquee, "marquee", 500, 150),
            (self.countdown, "countdown", 250, 150),
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

        self.show_hide_title_bars(self.settings.value("hide_title_bars", False))
        self.marquee.speed = float(self.settings.value("marquee/speed", 50))
        self.donor_list.num_donors = int(
            self.settings.value("donor_list/num_donors", 10)
        )
        self.countdown.load_settings(self.settings)

        self.bonuses = self.settings.value("bonuses", [])
        self.compute_bonuses()

    def file_menu(self):
        """Create a file submenu with an Open File item that opens a file dialog."""
        self.file_sub_menu = self.menu_bar.addMenu("Options")

        self.set_url_action = QAction("Set URL", self)
        self.set_url_action.setStatusTip("Pick the JustGiving page to scrape.")
        self.set_url_action.setShortcut("CTRL+U")
        self.set_url_action.triggered.connect(self.set_url)

        self.set_default_target_action = QAction("Set default target", self)
        self.set_default_target_action.setStatusTip(
            "Set a default target for if JustGiving won't give us one."
        )
        self.set_default_target_action.triggered.connect(self.set_default_target)

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

        self.hide_title_bars_action = QAction("Hide title bars", self)
        self.hide_title_bars_action.setStatusTip(
            "Hide the title bars of the windows intended to be streamed"
        )
        self.hide_title_bars_action.setShortcut("CTRL+B")
        self.hide_title_bars_action.triggered.connect(
            lambda: self.show_hide_title_bars(hide=True)
        )

        self.show_title_bars_action = QAction("Show title bars", self)
        self.show_title_bars_action.setStatusTip(
            "Show the title bars of the windows intended to be streamed"
        )
        self.show_title_bars_action.setShortcut("CTRL+B")
        self.show_title_bars_action.setVisible(False)
        self.show_title_bars_action.triggered.connect(
            lambda: self.show_hide_title_bars(hide=False)
        )

        self.exit_action = QAction("Exit Application", self)
        self.exit_action.setStatusTip("Exit the application.")
        self.exit_action.setShortcut("CTRL+Q")
        self.exit_action.triggered.connect(lambda: QApplication.quit())

        self.file_sub_menu.addAction(self.set_url_action)
        self.file_sub_menu.addAction(self.set_default_target_action)
        self.file_sub_menu.addAction(self.pause_action)
        self.file_sub_menu.addAction(self.refresh_time_action)
        self.file_sub_menu.addAction(self.marquee_speed_action)
        self.file_sub_menu.addAction(self.num_donors_action)
        self.file_sub_menu.addAction(self.hide_title_bars_action)
        self.file_sub_menu.addAction(self.show_title_bars_action)
        self.file_sub_menu.addAction(self.exit_action)

    def time_menu(self):
        self.time_menu = self.menu_bar.addMenu("Time")
        self.countdown.set_up_menu(self.time_menu)

        self.bonuses_action = QAction("Set bonuses", self)
        self.bonuses_action.setStatusTip("Set up bonus time for donation thresholds.")
        self.bonuses_action.triggered.connect(self.set_bonuses)
        self.time_menu.addAction(self.bonuses_action)

    def init_colours(self):
        self.migrate_text_colour_settings()
        self.colour_menu = self.menu_bar.addMenu("Colours")
        self.colour_menu_items = []

        for widget, attrname, text, default in [
            (self.progress_bar, "bar_colour", "progress bar", QColor(Qt.green)),
            (
                self.progress_bar,
                "bar_text_colour",
                "progress bar text",
                QColor(Qt.darkGreen),
            ),
            (
                self.progress_bar,
                "text_colour",
                "progress bar lower text",
                QColor(Qt.white),
            ),
            (self.latest_donor, "text_colour", "latest donor text", QColor(Qt.white)),
            (self.donor_list, "text_colour", "donor list text", QColor(Qt.white)),
            (self.marquee, "text_colour", "marquee text", QColor(Qt.white)),
            (self.countdown, "text_colour", "countdown text", QColor(Qt.white)),
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

    def migrate_text_colour_settings(self):
        if (
            text_colour := self.settings.value("bar/text_colour", None)
        ) and not self.settings.value("bar/bar_text_colour", None):
            self.settings.setValue("bar/bar_text_colour", text_colour)
            self.settings.setValue("bar/text_colour", QColor(Qt.white))

    def audio_menu(self):
        test_donations = [
            Donor("Test donor", "Testing, one two, three.", "NOTHING!"),
            Donor(
                "Another test donor",
                "This is a test of the Emergency Broadcast System. "
                "This is only a test.",
                None,
            ),
        ]

        self.audio_menu = self.menu_bar.addMenu("Audio")

        self.test_audio_action = QAction("Test audio", self)
        self.test_audio_action.setStatusTip(
            "Play a test announcement to check audio levels."
        )
        self.test_audio_action.setShortcut("CTRL+T")
        self.test_audio_action.triggered.connect(
            lambda: self.announcer.announce(
                Announcement.from_donations(donations=test_donations)
            )
        )

        self.play_last_action = QAction("Play previous announcements", self)
        self.play_last_action.setStatusTip(
            "Replay some number of previous announcements."
        )
        self.play_last_action.setShortcut("CTRL+L")
        self.play_last_action.triggered.connect(lambda: self.play_last())

        self.force_extra_hour_action = QAction("Force extra hour announcement", self)
        self.force_extra_hour_action.setStatusTip(
            "Play a fanfare for an extra hour even if you don't deserve one."
        )
        self.force_extra_hour_action.triggered.connect(
            lambda: self.announcer.announce(
                Announcement(
                    "And that takes us over the next bonus threshold, adding an extra hour! Woo! ",
                    "bonus",
                )
            )
        )

        self.audio_menu.addAction(self.test_audio_action)
        self.audio_menu.addAction(self.play_last_action)
        self.audio_menu.addAction(self.force_extra_hour_action)

    def play_last(self):
        num_announcements, accept = QInputDialog.getInt(
            self,
            "Enter number of announcements",
            "Enter the number of announcements to replay",
            1,
        )
        if accept:
            self.announcer.play_last(num_announcements)

    def stop_all_announcements(self):
        self.announcer.stop()

    def debug_menu(self):
        self.debug_menu = self.menu_bar.addMenu("Debug")

        self.test_audio_queue_action = QAction("Test queued audio", self)
        self.test_audio_queue_action.setStatusTip("Play a test bonus announcement.")
        self.test_audio_queue_action.triggered.connect(
            lambda: self.announcer.announce(
                Announcement(
                    message="This is a bonus announcement.",
                    fanfare="bonus",
                )
            )
        )

        self.add_500_donation_action = QAction("Add £500 donation", self)
        self.add_500_donation_action.setStatusTip(
            "Pretend our total just went up by £500."
        )
        self.add_500_donation_action.triggered.connect(
            lambda: self.check_threshold_crossings(
                self.progress_bar.totals[0],
                self.progress_bar.totals[0] + 500,
                self.progress_bar.totals[1],
                self.progress_bar.totals[2],
            )
        )

        self.fake_justgiving_action = QAction("Fake JustGiving", self)
        self.fake_justgiving_action.setStatusTip(
            "Pretend we have made £2000, but with no donors"
        )

        def patch_get_data():
            DataGetter.local_get_data = staticmethod(fake_get_data)

        self.fake_justgiving_action.triggered.connect(patch_get_data)

        self.debug_menu.addAction(self.test_audio_queue_action)
        self.debug_menu.addAction(self.add_500_donation_action)
        self.debug_menu.addAction(self.fake_justgiving_action)

    def set_background_colours(self, colour=None):
        if not colour:
            colour = QColorDialog.getColor(
                initial=self.background_colour,
                parent=self,
                title="Choose window background colour",
            )
        if colour.isValid():
            self.settings.setValue(f"background_colour", colour)

            for window in self, self.marquee:
                window.setStyleSheet(f"background-color: {colour.name()}")

            for window in (
                self,
                self.progress_bar,
                self.latest_donor,
                self.donor_list,
                self.countdown,
            ):
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
            self.timer.status_display.status = "Connecting"
            self.timer.status_display.last_check = "Waiting to connect..."
            self.settings.setValue("url", url)
            self.pause(force_resume=True)
            self.start_update_data(synchronous=True)

    def set_default_target(self):
        target, accept = QInputDialog.getText(
            self,
            "Enter default target",
            "Enter the target amount to fall back to if JustGiving doesn't return one:",
        )

        if accept:
            self.default_target = Decimal(target)
            self.settings.setValue("default_target", target)
            self.pause(force_resume=True)
            self.start_update_data(synchronous=True)

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

    def set_bonuses(self):
        current_bonuses = self.settings.value("bonuses", [])
        bonuses_dialog = BonusDialog()
        bonuses_dialog.bonuses = current_bonuses
        if bonuses_dialog.exec_():
            self.bonuses = bonuses_dialog.bonuses
            self.settings.setValue("bonuses", self.bonuses)
            self.compute_bonuses()

    def compute_bonuses(self):
        achieved_bonuses = []
        if self.progress_bar.totals:
            current_total, *_ = self.progress_bar.totals
            for threshold, bonus in self.bonuses:
                if current_total > threshold:
                    achieved_bonuses.append(timedelta(hours=bonus))

            self.countdown.bonus_time = achieved_bonuses
        else:
            current_total = 0
            self.countdown.bonus_time = []

        remaining_thresholds = [
            threshold for threshold, _ in self.bonuses if threshold > current_total
        ]
        if remaining_thresholds:
            logging.debug(f"Setting threshold to {min(remaining_thresholds)}")
            self.progress_bar.next_threshold = min(remaining_thresholds)
        else:
            logging.debug("No thresholds available...")
            self.progress_bar.next_threshold = None
        self.progress_bar.update()

    def new_donors(self, donors):
        if not self.donors:
            return None

        if len(donors) < len(self.donors):
            # If the number of donations goes down, something has gone wrong
            return None

        if self.donors[0] not in donors:
            # List has completely changed; probably something has gone wrong
            return None

        new_donors = []
        for donor in donors:
            if donor not in self.donors:
                new_donors.append(donor)
            else:
                return new_donors

    def show_hide_title_bars(self, hide):
        for window in (
            self.progress_bar,
            self.latest_donor,
            self.donor_list,
            self.marquee,
        ):
            visible = window.isVisible()
            window.title_bar_hidden = hide
            if visible:
                window.show()

        if hide:
            self.hide_title_bars_action.setVisible(False)
            self.show_title_bars_action.setVisible(True)
        else:
            self.hide_title_bars_action.setVisible(True)
            self.show_title_bars_action.setVisible(False)

        self.settings.setValue("hide_title_bars", hide)

    def format_bonus(self, bonus):
        if bonus == 1:
            return "one hour"
        elif bonus.is_integer():
            return f"{int(bonus)} hours"
        else:
            return f"{bonus} hours"

    def check_threshold_crossings(self, old_total, new_total, target, currency):
        if old_total is None:
            return

        new_bonuses = [
            bonus for bonus in self.bonuses if old_total < bonus.threshold <= new_total
        ]

        message = ""
        if len(new_bonuses) == 1:
            bonus = new_bonuses[0].bonus
            message += f"And that takes us over the next bonus threshold, adding an extra {self.format_bonus(bonus)}! Woo! "
        elif len(new_bonuses) > 1:
            total_bonus = sum(bonus.bonus for bonus in new_bonuses)
            message += f"And that takes us over the next {len(new_bonuses)} bonus thresholds, adding an extra {self.format_bonus(total_bonus)} in all! Woo! "

        if old_total < target <= new_total:
            message += f"And that {'also ' if message else ''} takes us past our {currency}{target} target! Well done everyone!"

        if message:
            self.announcer.announce(Announcement(message=message, fanfare="bonus"))

    def start_update_data(self, synchronous=False, reraise=False):
        if synchronous:
            return self.complete_update_data(
                reraise=reraise,
                new_data=get_data(self.url, len(self.donor_list.donor_widgets)),
            )
        if not self.url:
            return

        data_getter = DataGetter(self.url, len(self.donor_list.donor_widgets))
        data_getter.signals.finished.connect(
            lambda new_data: self.complete_update_data(reraise, new_data)
        )
        self.thread_pool.start(data_getter)

    def complete_update_data(self, reraise=False, new_data=None):
        logging.debug("Entered complete_update_data")

        if self.url and new_data is not None:
            new_totals, donors = new_data
            if isinstance(new_totals, Exception):
                logging.debug("Hit an error: new_totals.")
                self.timer.update_failedcheck(verb="checked")
                if reraise:
                    logging.debug("Raising this")
                    raise new_totals
                return

            old_total, *_ = self.progress_bar.totals or (None, None)

            new_total, target, currency = new_totals or (0, 0, "£")
            if target is None:
                target = self.default_target
                new_totals = Total(new_total, target, currency)

            self.progress_bar.totals = new_totals

            self.check_threshold_crossings(old_total, new_total, target, currency)
            self.compute_bonuses()
            if new_donors := self.new_donors(donors):
                self.announcer.announce(Announcement.from_donations(new_donors))
            self.donors = donors
            if donors:
                self.latest_donor.donor = donors[0]
            self.donor_list.donors = donors[:]
            self.marquee.donors = donors[:]

        self.update()
        self.progress_bar.update()
        self.timer.update_last_check(verb="checked", success=True)

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
            self.start_update_data()
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


def main(debug):
    application = QApplication(sys.argv)
    window = JustGivingTotaliser(debug=debug)
    desktop = QDesktopWidget().availableGeometry()
    width = (desktop.width() - window.width()) // 2
    height = (desktop.height() - window.height()) // 2
    window.show()
    window.move(width, height)
    sys.exit(application.exec_())
