import os
import re
import sys
import time
import random
import threading

import keyboard
import requests
import vlc
import yt_dlp

from PIL import Image
from pystray import Icon, Menu, MenuItem

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtWidgets import (QApplication, QFileDialog, QInputDialog, QLabel, QMainWindow, QPushButton)

# variables :

player = vlc.MediaPlayer()
formats = (".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".wma", ".mp4", ".mkv", ".webm", ".avi")
playlist = []
current_index = -1
playing = False
single_file_mode = False
song_end_time = None
image = Image.open("tray_icon.png")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# functions :

def is_arabic(text: str) -> bool:
    return bool(re.search(r'[\u0600-\u06FF]', text))

def format_title(title):

    title = os.path.splitext(title)[0]

    max_line = 14
    max_total = 40

    truncated = False

    if len(title) > max_total:
        title = title[:max_total]
        truncated = True

    lines = []

    while len(title) > max_line:

        part = title[:max_line]

        if not part.endswith(" ") and len(title) > max_line:

            if title[max_line] != " ":
                part += "~"

        lines.append(part)

        title = title[max_line:]

    if title:
        lines.append(title)

    result = "\n".join(lines)

    if truncated:
        result += "..."

    return result

def quit_app(icon, item):
    player.stop()
    os._exit(0)

def next_song2(icon, item):
    window.next_song()

def previous_song2(icon, item):   
    window.prev_song()

def pause2(icon, item):
    if player.is_playing():
        player.pause()
    else:
        player.play()

def play_current():
    global playing

    if 0 <= current_index < len(playlist):
        window.load_song(playlist[current_index])
        print(f"Now Playing: {os.path.basename(playlist[current_index])}")
        playing = True
    else:
        playing = False

def monitor():
    global current_index
    global playing
    global song_end_time

    while True:
        if playing and playlist:
            length = player.get_length()
            current = player.get_time()
            if length > 0:
                if current >= length - 300:
                    if song_end_time is None:
                        song_end_time = time.time()

                    elif time.time() - song_end_time >= 1:
                        if player.get_time() >= length - 300:
                            current_index += 1
                            if current_index < len(playlist):
                                play_current()
                            else:
                                playing = False
                        song_end_time = None
                else:
                    song_end_time = None

        time.sleep(0.1)

def path(name):
    return os.path.join(BASE_DIR, name)

# UI class : 

class UI(QMainWindow):

    open_file_signal = pyqtSignal()
    open_folder_signal = pyqtSignal()
    youtube_signal = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.open_file_signal.connect(self.open_file_dialog)
        self.open_folder_signal.connect(self.open_folder_dialog)
        self.youtube_signal.connect(self.youtube_dialog)

        # areas

        self.play_area = (1081, 639, 1131, 682)
        self.next_area = (1156, 652, 1184, 668)
        self.prev_area = (1023, 650, 1054, 670)
        self.shuffle_area = (1016, 580, 1046, 610)

        # window

        self.setGeometry(670, -400, 1920, 1080)

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint |Qt.WindowType.Tool)

        # base ui

        self.bg = QLabel(self)
        self.bg.setGeometry(0, 0, 1920, 1080)

        self.bg.setPixmap(QPixmap(path("UI base.png")))

        # icons and buttons

        self.play_icon = QIcon(path("play button.png"))
        self.pause_icon = QIcon(path("pause button.png"))
        self.next_icon = QIcon(path("next button.png"))
        self.prev_icon = QIcon(path("prev button.png"))
        self.shuffle_icon = QIcon(path("shuffle icon.png"))

        # image

        self.album_art = QLabel(self)

        self.album_art.setGeometry(720, 440, 260, 260)
        self.default_art = QPixmap(path("icon.jpg"))
        self.album_art.setPixmap(self.default_art)
        self.album_art.setScaledContents(True)

        # label

        self.song_label = QLabel("...", self)

        self.song_label.setAlignment(
            Qt.AlignmentFlag.AlignTop |
            Qt.AlignmentFlag.AlignLeft
        )
        self.song_label.setTextFormat(Qt.TextFormat.PlainText)
        self.song_label.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        self.song_label.setGeometry(990, 450, 600, 220)
        self.song_label.setFixedHeight(170)

        self.song_label.setStyleSheet("""
            color: white;
            font-size: 28px;
            font-weight: bold;
            background: transparent;
            font-family: Arial;
        """)
        # play button

        self.play_btn = QPushButton(self)

        self.play_btn.setGeometry(0, 0, 1920, 1080)

        self.play_btn.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self.play_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
            }
        """)

        self.play_btn.setIcon(self.play_icon)

        self.play_btn.setIconSize(self.play_btn.size())

        self.play_btn.clicked.connect(self.toggle_play)

        # next button

        self.next_btn = QPushButton(self)

        self.next_btn.setGeometry(0, 0, 1920, 1080)

        self.next_btn.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self.next_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
            }
        """)

        self.next_btn.setIcon(self.next_icon)

        self.next_btn.setIconSize(self.next_btn.size())

        self.next_btn.clicked.connect(self.next_song)

        # previous button

        self.prev_btn = QPushButton(self)

        self.prev_btn.setGeometry(0, 0, 1920, 1080)

        self.prev_btn.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self.prev_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
            }
        """)

        self.prev_btn.setIcon(self.prev_icon)

        self.prev_btn.setIconSize(self.prev_btn.size())

        self.prev_btn.clicked.connect(self.prev_song)

        # proggres dot
 
        self.progress_dot = QLabel(self)

        self.progress_dot.setGeometry(1016, 626, 10, 10)

        self.progress_dot.setPixmap(QPixmap(path("prog dot.png")))

        self.progress_dot.setScaledContents(True)

        self.dot_min_x = 1016
        self.dot_max_x = 1200

        self.dot_x = 1016  # initial position (your given value)
        self.dot_y = 626

        self.progress_dot.raise_()

        self.dragging_dot = False
        # volume dot

        self.volume_dot = QLabel(self)

        self.volume_dot.setGeometry(1143, 592, 10, 10)

        self.volume_dot.setPixmap(QPixmap(path("prog dot.png")))
 
        self.volume_dot.setScaledContents(True)

        self.volume_min_x = 1143
        self.volume_max_x = 1198

        self.volume_x = self.volume_max_x
        self.volume_y = 592

        self.volume_dot.move(
            int(self.volume_x),
            self.volume_y
        )

        self.volume_dot.raise_()

        self.dragging_volume = False


        # shuffle icon

        self.shuffle_btn = QPushButton(self)

        self.shuffle_btn.setGeometry(1016, 580, 30, 30)

        self.shuffle_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
            }
        """)
        self.shuffle_btn.setIcon(self.shuffle_icon)

        self.shuffle_btn.setIconSize(self.shuffle_btn.size())

        self.shuffle_btn.clicked.connect(self.shuffle)

        # timer

        self.timer = QTimer()

        self.timer.timeout.connect(self.update_ui)

        self.timer.start(50)

        player.audio_set_volume(100)
    
        self.show()


        self.album_art.lower()
        self.bg.raise_()

        self.song_label.raise_()
        self.play_btn.raise_()
        self.next_btn.raise_()
        self.prev_btn.raise_()
        self.progress_dot.raise_()
        self.shuffle_btn.raise_()
        self.volume_dot.raise_()
        self.song_label.setWordWrap(True)
        self.song_label.setTextFormat(Qt.TextFormat.PlainText)
        self.song_label.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        self.song_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    # functions :

    def toggle_play(self):

        global playing

        if player.is_playing():

            player.pause()

            playing = False

            self.play_btn.setIcon(self.play_icon)

        else:

            player.play()

            playing = True

            self.play_btn.setIcon(self.pause_icon)

    def load_song(self, file_path):

        global playing

        player.set_media(vlc.Media(file_path))

        player.play()

        time.sleep(0.2)

        if player.get_length() <= 0:
            print("Could not play file.")
            return

        playing = True


        title = format_title(os.path.basename(file_path))
        self.song_label.setText(title)

        if is_arabic(title):
            self.song_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.song_label.move(1000, self.song_label.y())
        else:
            self.song_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            self.song_label.move(990, self.song_label.y())

        # DEFAULT IMAGE
        self.album_art.setPixmap(self.default_art)

        # BUTTON ICON
        self.play_btn.setIcon(self.pause_icon)

    def next_song(self):

        global playlist, current_index

        if playlist and current_index + 1 < len(playlist):

            current_index += 1

            self.load_song(playlist[current_index])

    def prev_song(self):

        global playlist, current_index

        if playlist and current_index - 1 >= 0:

            current_index -= 1

            self.load_song(playlist[current_index])

    def shuffle(self):
        global current_index

        if playing and playlist:
            random.shuffle(playlist)
            current_index = 0
            window.load_song(playlist[current_index])

    def play_youtube(self, url):

        global playing

        ydl_opts = {
            "format": "bestaudio/best",
            "quiet": True
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

        except Exception as e:
            print("Invalid YouTube URL or no internet.")
            return

        audio_url = info["url"]
        player.set_media(vlc.Media(audio_url))
        player.play()
        playing = True

        self.song_label.setWordWrap(True)

        title = format_title(info["title"])
        self.song_label.setText(title)

        if is_arabic(title):
            self.song_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.song_label.move(1000, self.song_label.y())  # shift right a bit
        else:
            self.song_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            self.song_label.move(990, self.song_label.y())

        try:
            response = requests.get(info["thumbnail"], timeout=5)

            pix = QPixmap()
            pix.loadFromData(response.content)

            self.album_art.setPixmap(pix)

        except:
            self.album_art.setPixmap(self.default_art)

        pix = QPixmap()

        pix.loadFromData(response.content)

        self.album_art.setPixmap(pix)

        self.play_btn.setIcon(self.pause_icon)

    def update_ui(self):
        if player.is_playing() and not self.dragging_dot:
            current = player.get_time()
            total = player.get_length()
            if total > 0:
                progress = current / total
                x = self.dot_min_x + (self.dot_max_x - self.dot_min_x) * progress
                x = max(self.dot_min_x, min(x, self.dot_max_x))
                self.dot_x = x
                self.progress_dot.move(int(self.dot_x), int(self.dot_y))

            self.play_btn.setIcon(self.pause_icon)
        else:
            self.play_btn.setIcon(self.play_icon)     

    def inside(self, pos, area):

        x, y = pos.x(), pos.y()

        x1, y1, x2, y2 = area

        return x1 <= x <= x2 and y1 <= y <= y2
    
    
    def mousePressEvent(self, event):

        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()

            if self.progress_dot.geometry().contains(pos):
                self.dragging_dot = True
                return
            
            if self.volume_dot.geometry().contains(pos):
                self.dragging_volume = True
                return

            if self.inside(pos, self.play_area):
                self.toggle_play()

            elif self.inside(pos, self.next_area):
                self.next_song()

            elif self.inside(pos, self.prev_area):
                self.prev_song()

            elif self.inside(pos, self.shuffle_area):
                self.shuffle()

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()

        if self.dragging_dot:

            self.dot_x = max(self.dot_min_x, min(pos.x(), self.dot_max_x))
            self.progress_dot.move(int(self.dot_x), self.dot_y)

        elif self.dragging_volume:

            self.volume_x = max(self.volume_min_x, min(pos.x(), self.volume_max_x))
            self.volume_dot.move(int(self.volume_x), self.volume_y)
            volume_ratio = ((self.volume_x - self.volume_min_x)/ (self.volume_max_x - self.volume_min_x))
            volume = int(volume_ratio * 100)
            player.audio_set_volume(volume)

    def mouseReleaseEvent(self, event):

        if self.dragging_dot:

            if player.get_length() > 0:

                ratio = (
                    (self.dot_x - self.dot_min_x)
                    / (self.dot_max_x - self.dot_min_x)
                )

                player.set_time(
                    int(player.get_length() * ratio)
                )

                # force playback resume
                if playing:
                    player.play()

        self.dragging_dot = False
        self.dragging_volume = False

    def open_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Choose File", "", "Audio/Video Files (*.mp3 *.wav *.flac *.ogg *.m4a *.aac *.wma *.mp4 *.mkv *.webm *.avi)")

        if file_path:
            self.load_song(file_path)
            global single_file_mode
            single_file_mode = True

    def open_folder_dialog(self):
        global playlist, current_index

        folder_path = QFileDialog.getExistingDirectory(self, "Choose Folder")
        if folder_path:
            global single_file_mode
            single_file_mode = False

            playlist = sorted(
                os.path.join(folder_path, song)
                for song in os.listdir(folder_path)
                if song.lower().endswith(formats)
                )
            if not playlist:
                print("No supported media files found.")
                return
            if playlist:
                current_index = 0
                self.load_song(playlist[current_index])

    def youtube_dialog(self):

        url, ok = QInputDialog.getText(
            self,
            "YouTube URL",
            "Paste YouTube URL:"
        )
        if ok and url.strip():
            self.play_youtube(url.strip())

app = QApplication(sys.argv)
window = UI()

menu = Menu(

    MenuItem(
        "Choose File        [CTRL + SHIFT + SPACE]",lambda icon, item: window.open_file_signal.emit()),

    MenuItem(
        "Choose Folder    [CTRL + SHIFT]",lambda icon, item: window.open_folder_signal.emit()),

    MenuItem(
        "YouTube URL      [Y + SHIFT]",lambda icon, item: window.youtube_signal.emit()),

    Menu.SEPARATOR,

    MenuItem("Play / Pause", pause2),
    MenuItem("Next Song", next_song2),
    MenuItem("Previous Song", previous_song2),

    Menu.SEPARATOR,

    MenuItem("Quit", quit_app)
)

icon = Icon(
    "MusicPlayer",
    image,
    menu=menu
)
keyboard.add_hotkey(
    "ctrl+shift+space",
    lambda: window.open_file_signal.emit()
)
keyboard.add_hotkey(
    "ctrl+shift",
    lambda: window.open_folder_signal.emit()
)
keyboard.add_hotkey(
    "y+shift",
    lambda: window.youtube_signal.emit()
)
threading.Thread(target=monitor, daemon=True).start()
threading.Thread(target=icon.run, daemon=True).start()
sys.exit(app.exec())