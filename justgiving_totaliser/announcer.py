from datetime import datetime, timezone
import logging
import os
import pathlib
from time import sleep

from PyQt5.QtCore import QObject, QTimer, QUrl
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer
from PyQt5.QtTextToSpeech import QTextToSpeech
from PyQt5.QtWidgets import QAction

from .common import format_donor


_fanfares = {
    "donation": "fanfare.mp3",
    "bonus": "fanfare_bonus.mp3",
    "end": "fanfare_end.mp3",
}


class Announcement:
    announced = None

    def __init__(self, message="", fanfare=None):
        logging.debug(f"Creating announcement, {message=}, {fanfare=}")
        fanfare_path = pathlib.Path(__file__).parent / "assets"
        if fanfare:
            self.fanfare = str(fanfare_path / _fanfares[fanfare])
        else:
            self.fanfare = None

        self.message = message
        self.created = datetime.now(timezone.utc)

    @classmethod
    def from_donations(cls, donations):
        return cls(
            message=". ".join(
                format_donor(donation, quotes="straight") for donation in donations
            ),
            fanfare="donation",
        )


class Announcer(QObject):
    def __init__(self, *, tts=False):
        self.previous_announcements = []
        self.pending_announcements = []
        self.toggle_voice(tts)
        self.fanfare = QMediaPlayer()
        self.fanfare.setVolume(100)

    @property
    def is_announcing(self):
        if self.fanfare.state() == QMediaPlayer.PlayingState:
            return True
        if self.tts and self.tts.state() == QTextToSpeech.Speaking:
            return True
        return False

    def announce_next(self, state=None):
        if not (
            self.is_announcing
            or (self.tts and state == QTextToSpeech.Speaking)
            or ((not self.tts) and state == QMediaPlayer.PlayingState)
        ):
            if self.pending_announcements:
                announcement = self.pending_announcements.pop(0)
                if not announcement.announced:
                    announcement.announced = datetime.now(timezone.utc)
                self.previous_announcements.append(announcement)
                self._announce(announcement)

    def _announce(self, announcement):
        if announcement.fanfare:
            self.fanfare.setMedia(
                QMediaContent(QUrl.fromLocalFile(announcement.fanfare))
            )
            if self.tts:
                self.fanfare.stateChanged.connect(
                    lambda state: self.speak(announcement, state)
                )
            self.fanfare.play()
        elif tts:
            self.speak(announcement)
        else:
            self.announce_next()

    def speak(self, announcement, state=None):
        if state == QMediaPlayer.StoppedState or state is None:
            self.fanfare.stateChanged.disconnect()
            self.tts.say(announcement.message)

    def stop(self):
        self.fanfare.stop()
        if self.tts and self.tts.state() == QTextToSpeech.Speaking:
            self.tts.stop()

        self.previous_announcements.extend(self.pending_announcements)
        self.pending_announcements = []

    def announce(self, announcement):
        self.pending_announcements.append(announcement)
        self.announce_next()

    def play_last(self, count):
        self.pending_announcements.extend(self.previous_announcements[-count:])
        self.announce_next()

    def toggle_voice(self, use_voice):
        if use_voice:
            self.tts = QTextToSpeech()
            if self.tts.state() == QTextToSpeech.BackendError:
                logging.warn("Unable to set up TTS.")
                self.tts = None
                self.fanfare.stateChanged.connect(
                    lambda state: self.announce_next(state=state)
                )
            else:
                self.tts.stateChanged.connect(
                    lambda state: self.announce_next(state=state)
                )
        else:
            self.tts = None
