import logging
from time import sleep

from PyQt5.QtCore import QObject, QTimer, QUrl
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer
from PyQt5.QtTextToSpeech import QTextToSpeech
from PyQt5.QtWidgets import QAction

from .common import format_donor


class Announcer(QObject):
    def __init__(self, fanfare, stop_action=None):
        self.pending_announcements = []
        self.tts = QTextToSpeech()
        if self.tts.state() == QTextToSpeech.BackendError:
            logging.warn("Unable to set up TTS.")
            self.tts = None

        self.fanfare = QMediaPlayer()
        self.fanfare.setMedia(QMediaContent(QUrl.fromLocalFile(fanfare)))
        self.fanfare.setVolume(100)
        self.fanfare_timer = QTimer()
        self.fanfare_timer.timeout.connect(lambda: self.speak())

        if stop_action:
            stop_action.triggered.connect(self.stop_announcement)

    @property
    def is_announcing(self):
        if self.fanfare_timer.isActive():
            return True
        if self.tts and self.tts.state() == QTextToSpeech.Speaking:
            return True
        return False

    def speak(self):
        max_wait_time = 10
        logging.debug(f"Speaking - wait time {self.fanfare_wait_time}")
        if (
            self.fanfare.state() == QMediaPlayer.StoppedState
            or self.fanfare_wait_time >= max_wait_time
        ):
            self.fanfare_timer.stop()
            self.tts.say(self.tts_to_say)
        else:
            self.fanfare_wait_time += 1

    def announce_text(self, text):
        logging.debug(f"Announcing text {text}")
        self.stop_announcement()
        self.fanfare.play()
        if self.tts:
            logging.debug("TTS present")
            self.fanfare_wait_time = 0
            self.tts_to_say = text
            self.fanfare_timer.start(500)

    def announce_donors(self, new_donors):
        self.announce_text(". ".join(format_donor(donor) for donor in new_donors))

    def wait_and_announce_text(self, text, wait_on):
        logging.debug(f"Enqueueing announcement of {text}")

        if not wait_on.is_announcing:
            self.announce_text(text)
            return

        # Using a closure here because we only want the signal to be caught once
        def announce_after_waiting(state):
            logging.debug(f"State changed, trying to announce {text}")
            if state == QTextToSpeech.Ready:
                self.announce_text(text)
                wait_on.tts.stateChanged.disconnect(announce_after_waiting)
                try:
                    self.pending_announcements.remove(announce_after_waiting)
                except ValueError:
                    from PyQt5.QtCore import pyqtRemoveInputHook

                    pyqtRemoveInputHook()
                    breakpoint()
                    logging.warning("Couldn't garbage collect current announcement.")

        self.pending_announcements.append(announce_after_waiting)
        wait_on.tts.stateChanged.connect(announce_after_waiting)

    def stop_announcement(self):
        self.fanfare_timer.stop()
        self.fanfare.stop()
        if self.tts and self.tts.state() == QTextToSpeech.Speaking:
            self.tts.stop()
