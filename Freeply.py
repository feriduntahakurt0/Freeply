"""
Freeply.py — Main application file
A free music player built with CustomTkinter.

Folder layout expected:
  Freeply.py
  SetSettings.py
  Settings/
      settings.py
  Musics/          ← MP3 files live here
"""

import os
import sys
import threading
import subprocess
import webbrowser
import urllib.request
import urllib.parse

from customtkinter import *

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
MUSICS_DIR  = os.path.join(BASE_DIR, "Musics")
os.makedirs(MUSICS_DIR, exist_ok=True)

sys.path.insert(0, os.path.join(BASE_DIR, "Settings"))
from settings import *    # noqa: F403

# ── Optional pygame for playback ──────────────────────────────────────────────
try:
    import pygame
    pygame.mixer.init()
    PYGAME_OK = True
except ImportError:
    PYGAME_OK = False

# ── App window ────────────────────────────────────────────────────────────────
set_appearance_mode("light")
set_default_color_theme("blue")

root = CTk()
root.geometry(windowSize)   # noqa: F405
root.title(f"Freeply {version}")   # noqa: F405
root.configure(fg_color=BackGroundColor)   # noqa: F405
root.resizable(True, True)

SIDEBAR_W = 210   # fixed pixel width for the left panel

# ═════════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ═════════════════════════════════════════════════════════════════════════════
sidebar = CTkFrame(root, width=SIDEBAR_W, fg_color=SideBarColor, corner_radius=0)   # noqa: F405
sidebar.place(x=0, y=0, relheight=1.0)
sidebar.pack_propagate(False)
sidebar.grid_propagate(False)

CTkLabel(
    sidebar,
    text=f"Freeply {version}",   # noqa: F405
    font=HeaderFont,              # noqa: F405
    text_color=HeaderColor,       # noqa: F405
    fg_color=SideBarColor,        # noqa: F405
    anchor="w"
).pack(fill="x", padx=emptyBetweenCorner, pady=(emptyBetweenCorner + 6, 2))   # noqa: F405

CTkLabel(
    sidebar,
    text="Free Music Player",
    font=SmallFont,          # noqa: F405
    text_color=BodyColor,    # noqa: F405
    fg_color=SideBarColor,   # noqa: F405
    anchor="w"
).pack(fill="x", padx=emptyBetweenCorner, pady=(0, 14))   # noqa: F405

# Separator
CTkFrame(sidebar, fg_color=AccentColor, height=2, corner_radius=1).pack(   # noqa: F405
    fill="x", padx=emptyBetweenCorner, pady=(0, 12))   # noqa: F405

# ═════════════════════════════════════════════════════════════════════════════
#  CONTENT AREA
# ═════════════════════════════════════════════════════════════════════════════
content = CTkFrame(root, fg_color=BackGroundColor, corner_radius=0)   # noqa: F405
content.place(x=SIDEBAR_W, y=0, relwidth=1.0, relheight=1.0)

# Utility: clear the content area
def clear_content():
    for widget in content.winfo_children():
        widget.destroy()

# ── Helper: section title ──────────────────────────────────────────────────
def section_title(text):
    CTkLabel(
        content,
        text=text,
        font=HeaderFont,           # noqa: F405
        text_color=HeaderColor,    # noqa: F405
        fg_color=BackGroundColor,  # noqa: F405
        anchor="w"
    ).pack(anchor="w", padx=28, pady=(26, 6))
    CTkFrame(content, fg_color=AccentColor, height=2, corner_radius=1   # noqa: F405
             ).pack(fill="x", padx=28, pady=(0, 16))

def body_text(text, padx=28, pady=(0, 10)):
    CTkLabel(
        content,
        text=text,
        font=BodyFont,             # noqa: F405
        text_color=BodyColor,      # noqa: F405
        fg_color=BackGroundColor,  # noqa: F405
        anchor="w",
        wraplength=680,
        justify="left"
    ).pack(anchor="w", padx=padx, pady=pady)

# ═════════════════════════════════════════════════════════════════════════════
#  PAGE FUNCTIONS
# ═════════════════════════════════════════════════════════════════════════════

# ── Main Menu ─────────────────────────────────────────────────────────────────
def MainMenu():
    clear_content()
    section_title("Welcome to Freeply")
    body_text("Freeply is a free, open-source music player and downloader.\n"
              "Use the sidebar to navigate between the app's features.")
    body_text("• Download — Download any song from YouTube as MP3.\n"
              "• Play  — Search and play a song stored in your library.\n"
              "• Playlists  — (coming soon) Manage your playlists.\n"
              "• Songs  — Browse all songs in your Musics folder.\n"
              "• Settings  — Customise the look of Freeply.\n"
              "• GitHub  — View the source code.\n"
              "• GNU License  — Read the open-source licence.\n"
              "• Contact With Me  — Get in touch with the developer.")
    body_text("Enjoy your music — for free, forever.")

# ── Download ──────────────────────────────────────────────────────────────────
def DownloadingMusicMenu():
    clear_content()
    section_title("Download a Song")
    body_text(
        "Enter a YouTube URL and the desired file name below.\n"
        "The song will be downloaded as an MP3 into your Musics folder.\n"
        "Requires yt-dlp and ffmpeg to be installed on your system."
    )

    # ── URL row ───────────────────────────────────────────────────────────────
    url_frame = CTkFrame(content, fg_color=BackGroundColor, corner_radius=0)
    url_frame.pack(anchor="w", padx=28, pady=(6, 0))

    CTkLabel(
        url_frame, text="YouTube URL:",
        font=BodyFont, text_color=BodyColor, fg_color=BackGroundColor
    ).pack(side="left", padx=(0, 10))

    url_entry = CTkEntry(
        url_frame, width=380, placeholder_text="https://www.youtube.com/watch?v=…",
        font=BodyFont, fg_color=EntryColor,
        text_color=BodyColor, border_color=AccentColor
    )
    url_entry.pack(side="left")

    # ── Song name row ─────────────────────────────────────────────────────────
    name_frame = CTkFrame(content, fg_color=BackGroundColor, corner_radius=0)
    name_frame.pack(anchor="w", padx=28, pady=(10, 0))

    CTkLabel(
        name_frame, text="Song name:  ",
        font=BodyFont, text_color=BodyColor, fg_color=BackGroundColor
    ).pack(side="left", padx=(0, 10))

    name_entry = CTkEntry(
        name_frame, width=380, placeholder_text="e.g. My Favourite Song",
        font=BodyFont, fg_color=EntryColor,
        text_color=BodyColor, border_color=AccentColor
    )
    name_entry.pack(side="left")

    # ── Status label ──────────────────────────────────────────────────────────
    status_lbl = CTkLabel(
        content, text="", font=SmallFont,
        text_color=SubHeaderColor, fg_color=BackGroundColor,
        wraplength=680, justify="left"
    )
    status_lbl.pack(anchor="w", padx=28, pady=(12, 0))

    # ── Progress bar ──────────────────────────────────────────────────────────
    progress_bar = CTkProgressBar(
        content, width=500,
        fg_color=EntryColor, progress_color=HeaderColor
    )

    def do_download():
        url  = url_entry.get().strip()
        name = name_entry.get().strip()

        if not url:
            status_lbl.configure(text="⚠ Please enter a YouTube URL.")
            return
        if not name:
            status_lbl.configure(text="⚠ Please enter a song name.")
            return

        # Check yt-dlp is available
        ytdlp = None
        for candidate in ("yt-dlp", "yt_dlp"):
            if subprocess.run(
                ["which", candidate], capture_output=True
            ).returncode == 0:
                ytdlp = candidate
                break

        if ytdlp is None:
            status_lbl.configure(
                text="✗ yt-dlp not found.\n"
                     "Install it with:  pip install yt-dlp\n"
                     "and make sure ffmpeg is also installed (brew install ffmpeg)."
            )
            return

        out_template = os.path.join(MUSICS_DIR, f"{name}.%(ext)s")
        cmd = [
            ytdlp,
            "--extract-audio",
            "--audio-format", "mp3",
            "--audio-quality", "0",
            "-o", out_template,
            url
        ]

        status_lbl.configure(text="⏳ Downloading… please wait.")
        progress_bar.pack(anchor="w", padx=28, pady=(8, 0))
        progress_bar.set(0)
        progress_bar.start()
        download_btn.configure(state="disabled")

        def run():
            result = subprocess.run(cmd, capture_output=True, text=True)
            progress_bar.stop()
            progress_bar.set(1)
            if result.returncode == 0:
                status_lbl.configure(
                    text=f"✓ Downloaded successfully as '{name}.mp3' in your Musics folder."
                )
            else:
                err = result.stderr.strip().splitlines()
                last = err[-1] if err else "Unknown error."
                status_lbl.configure(text=f"✗ Download failed:\n{last}")
            download_btn.configure(state="normal")

        threading.Thread(target=run, daemon=True).start()

    # ── Download button ───────────────────────────────────────────────────────
    download_btn = CTkButton(
        content, text="⬇  Download",
        command=do_download,
        font=SubHeaderFont, fg_color=HeaderColor,
        text_color="#FFFFFF", hover_color=SubHeaderColor,
        width=160, height=38, corner_radius=8
    )
    download_btn.pack(anchor="w", padx=28, pady=(14, 0))

    # ── Install hint ──────────────────────────────────────────────────────────
    CTkLabel(
        content,
        text="Tip: install dependencies with  →  pip install yt-dlp  and  brew install ffmpeg",
        font=SmallFont, text_color=BodyColor, fg_color=BackGroundColor, anchor="w"
    ).pack(anchor="w", padx=28, pady=(18, 0))


# ── Play ──────────────────────────────────────────────────────────────────────
_current_song_path = None

def PlayingMusicMenu():
    clear_content()
    section_title("Play a Song")
    body_text("Write the song's name (without extension) in the box below to search "
              "and play your song from the Musics folder.")

    entry_frame = CTkFrame(content, fg_color=BackGroundColor, corner_radius=0)   # noqa: F405
    entry_frame.pack(anchor="w", padx=28, pady=(4, 0))

    search_entry = CTkEntry(
        entry_frame, width=360, placeholder_text="Song name…",
        font=BodyFont,              # noqa: F405
        fg_color=EntryColor,        # noqa: F405
        text_color=BodyColor,       # noqa: F405
        border_color=AccentColor    # noqa: F405
    )
    search_entry.pack(side="left", padx=(0, 10))

    status_lbl = CTkLabel(
        content, text="", font=SmallFont,   # noqa: F405
        text_color=SubHeaderColor,           # noqa: F405
        fg_color=BackGroundColor             # noqa: F405
    )

    def play_song():
        global _current_song_path
        query = search_entry.get().strip()
        if not query:
            status_lbl.configure(text="⚠ Please enter a song name.")
            status_lbl.pack(anchor="w", padx=28, pady=(8, 0))
            return

        # Find any matching file in MUSICS_DIR
        found = None
        for f in os.listdir(MUSICS_DIR):
            name_no_ext = os.path.splitext(f)[0].lower()
            if query.lower() in name_no_ext:
                found = os.path.join(MUSICS_DIR, f)
                break

        if found is None:
            status_lbl.configure(text=f"✗ No song matching '{query}' found in Musics folder.")
        elif PYGAME_OK:
            pygame.mixer.music.load(found)
            pygame.mixer.music.play()
            _current_song_path = found
            status_lbl.configure(
                text=f"▶ Now playing: {os.path.basename(found)}")
        else:
            # Fallback: open with the system default player
            if sys.platform == "win32":
                os.startfile(found)
            elif sys.platform == "darwin":
                subprocess.call(["open", found])
            else:
                subprocess.call(["xdg-open", found])
            status_lbl.configure(
                text=f"▶ Opened: {os.path.basename(found)} in your default player.")
        status_lbl.pack(anchor="w", padx=28, pady=(8, 0))

    CTkButton(
        entry_frame, text="Play",
        command=play_song,
        font=BodyFont,              # noqa: F405
        fg_color=HeaderColor,       # noqa: F405
        text_color="#FFFFFF",
        hover_color=SubHeaderColor  # noqa: F405
    ).pack(side="left")

    status_lbl  # created above; packed inside play_song()

    # Stop button (only useful if pygame is available)
    if PYGAME_OK:
        def stop_song():
            pygame.mixer.music.stop()
            status_lbl.configure(text="⏹ Playback stopped.")
            status_lbl.pack(anchor="w", padx=28, pady=(8, 0))

        CTkButton(
            content, text="Stop",
            command=stop_song,
            font=BodyFont,                  # noqa: F405
            fg_color=ButtonColor,           # noqa: F405
            text_color=SubHeaderColor,      # noqa: F405
            hover_color=AccentColor,        # noqa: F405
            width=100
        ).pack(anchor="w", padx=28, pady=(12, 0))

# ── Playlists (stub) ──────────────────────────────────────────────────────────
def PlaylistMenu():
    clear_content()
    section_title("Playlists")
    body_text("Playlist management is coming in a future version of Freeply.\n"
              "Stay tuned!")

# ── Songs ─────────────────────────────────────────────────────────────────────
def SongsMenu():
    clear_content()
    section_title("Your Songs")
    body_text(f"Scanning: {MUSICS_DIR}")

    try:
        files = [f for f in os.listdir(MUSICS_DIR)
                 if os.path.isfile(os.path.join(MUSICS_DIR, f))]
    except FileNotFoundError:
        files = []

    if not files:
        body_text("No songs found. Use the Download page to add music,\n"
                  "or copy MP3/WAV files manually into the Musics folder.")
        return

    # Scrollable song list
    scroll = CTkScrollableFrame(
        content, fg_color=BackGroundColor,   # noqa: F405
        scrollbar_button_color=AccentColor   # noqa: F405
    )
    scroll.pack(fill="both", expand=True, padx=28, pady=(0, 20))

    status_lbl = CTkLabel(
        content, text="", font=SmallFont,   # noqa: F405
        text_color=SubHeaderColor,           # noqa: F405
        fg_color=BackGroundColor             # noqa: F405
    )
    status_lbl.pack(anchor="w", padx=28)

    def make_play_cmd(filepath, filename):
        def cmd():
            if PYGAME_OK:
                pygame.mixer.music.load(filepath)
                pygame.mixer.music.play()
                status_lbl.configure(text=f"▶ Now playing: {filename}")
            else:
                if sys.platform == "win32":
                    os.startfile(filepath)
                elif sys.platform == "darwin":
                    subprocess.call(["open", filepath])
                else:
                    subprocess.call(["xdg-open", filepath])
                status_lbl.configure(text=f"▶ Opened: {filename}")
        return cmd

    for fname in sorted(files):
        fpath = os.path.join(MUSICS_DIR, fname)
        CTkButton(
            scroll,
            text=f"  ♪  {fname}",
            command=make_play_cmd(fpath, fname),
            font=BodyFont,                  # noqa: F405
            text_color=SubHeaderColor,      # noqa: F405
            fg_color=SideBarColor,          # noqa: F405
            hover_color=ButtonColor,        # noqa: F405
            anchor="w",
            height=38,
            corner_radius=8
        ).pack(fill="x", pady=3)

# ── Settings ───────────────────────────────────────────────────────────────────
def SettingsPage():
    set_path = os.path.join(BASE_DIR, "SetSettings.py")
    if os.path.exists(set_path):
        subprocess.Popen([sys.executable, set_path])
    else:
        clear_content()
        section_title("Settings")
        body_text("SetSettings.py not found next to Freeply.py.")

# ── GitHub ────────────────────────────────────────────────────────────────────
def GitHubPage():
    webbrowser.open("https://github.com/feriduntahakurt0")

# ── GNU License ───────────────────────────────────────────────────────────────
def GnuLicensePage():
    webbrowser.open("https://www.gnu.org/licenses/gpl-3.0.html")

# ── Contact ───────────────────────────────────────────────────────────────────
def ContactPage():
    clear_content()
    section_title("Contact With Me")
    body_text("Have a question, a bug report, or just want to say hello?\n"
              "Feel free to reach out:")
    CTkLabel(
        content,
        text="📧  feriduntahakurt@gmail.com",
        font=SubHeaderFont,        # noqa: F405
        text_color=HeaderColor,    # noqa: F405
        fg_color=BackGroundColor,  # noqa: F405
        anchor="w"
    ).pack(anchor="w", padx=28, pady=(4, 0))
    body_text("\nI try to reply within a few days.", pady=(12, 0))

# ═════════════════════════════════════════════════════════════════════════════
#  SIDEBAR BUTTONS
# ═════════════════════════════════════════════════════════════════════════════
_NAV_BUTTONS = [
    ("⬇  Download",        DownloadingMusicMenu),
    ("▶  Play",            PlayingMusicMenu),
    ("≡  Playlists",       PlaylistMenu),
    ("♪  Songs",           SongsMenu),
    ("⚙  Settings",        SettingsPage),
    ("⌥  GitHub",          GitHubPage),
    ("©  GNU License",     GnuLicensePage),
    ("✉  Contact With Me", ContactPage),
]

def make_nav_cmd(fn):
    def cmd():
        fn()
    return cmd

for label, fn in _NAV_BUTTONS:
    CTkButton(
        sidebar,
        text=label,
        command=make_nav_cmd(fn),
        font=SubHeaderFont,         # noqa: F405
        text_color=SubHeaderColor,  # noqa: F405
        fg_color=SideBarColor,      # noqa: F405
        hover_color=ButtonColor,    # noqa: F405
        anchor="w",
        height=40,
        corner_radius=8
    ).pack(fill="x", padx=emptyBetweenCorner, pady=3)   # noqa: F405

# ═════════════════════════════════════════════════════════════════════════════
#  LAUNCH — show Main Menu on start
# ═════════════════════════════════════════════════════════════════════════════
MainMenu()
root.mainloop()