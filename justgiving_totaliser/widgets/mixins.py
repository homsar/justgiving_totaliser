from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor


class SaveSizeAndPositionOnClose:
    def closeEvent(self, event):
        self.settings.setValue(f"{self.key}/width", self.size().width())
        self.settings.setValue(f"{self.key}/height", self.size().height())
        self.settings.setValue(f"{self.key}/left", self.pos().x())
        self.settings.setValue(f"{self.key}/top", self.pos().y())

        event.accept()


class HideTitleBarOptional:
    _title_bar_hidden = False

    @property
    def title_bar_hidden(self):
        return self._title_bar_hidden

    @title_bar_hidden.setter
    def title_bar_hidden(self, hidden):
        self._title_bar_hidden = hidden

        if hidden:
            self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.FramelessWindowHint)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.__press_pos = event.pos()  # remember starting position

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.__press_pos = None

    def mouseMoveEvent(self, event):
        if self.__press_pos:  # follow the mouse
            self.move(self.pos() + (event.pos() - self.__press_pos))


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
