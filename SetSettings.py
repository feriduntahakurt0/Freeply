"""
SetSettings.py — Freeply Theme & Settings Editor
Opens as a standalone window; reads and rewrites Settings/settings.py
"""

import os
import re
import sys
from customtkinter import *

# ── Resolve paths ─────────────────────────────────────────────────────────────
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(BASE_DIR, "Settings", "settings.py")

sys.path.insert(0, os.path.join(BASE_DIR, "Settings"))
from settings import *          # noqa: F403, E402  (pull current values)

# ── Read the current Theme from file ──────────────────────────────────────────
def read_current_theme():
    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            m = re.match(r'^Theme\s*=\s*["\'](\w+)["\']', line.strip())
            if m:
                return m.group(1)
    return "Grape"

# ── Write a new Theme value into the file ─────────────────────────────────────
def write_theme(new_theme: str):
    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    content = re.sub(
        r'^(Theme\s*=\s*)["\'](\w+)["\']',
        lambda m: f'{m.group(1)}"{new_theme}"',
        content,
        flags=re.MULTILINE
    )
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        f.write(content)

# ── Available themes ──────────────────────────────────────────────────────────
THEMES = ["Grape", "Midnight", "Forest", "Sunset", "Arctic", "Rose", "Charcoal", "Gold"]

THEME_PREVIEWS = {
    "Grape":    ("#F5EEF8", "#6A0572"),
    "Midnight": ("#0D0D1A", "#7EB8FF"),
    "Forest":   ("#F0F7F0", "#1B4D2E"),
    "Sunset":   ("#FFF4EC", "#C0392B"),
    "Arctic":   ("#EAF4FB", "#1A5276"),
    "Rose":     ("#FFF0F3", "#880E2F"),
    "Charcoal": ("#2B2B2B", "#E0E0E0"),
    "Gold":     ("#FFFBF0", "#7D5A00"),
}

# ── App setup ─────────────────────────────────────────────────────────────────
set_appearance_mode("light")
set_default_color_theme("blue")

root = CTk()
root.title("Freeply — Settings")
root.geometry("640x520")
root.resizable(False, False)
root.configure(fg_color=BackGroundColor)   # noqa: F405

# ── Header ────────────────────────────────────────────────────────────────────
header_frame = CTkFrame(root, fg_color=SideBarColor, corner_radius=0)   # noqa: F405
header_frame.pack(fill="x", padx=0, pady=0)

CTkLabel(
    header_frame,
    text=f"Freeply {version} — Settings",   # noqa: F405
    font=HeaderFont,                         # noqa: F405
    text_color=HeaderColor                   # noqa: F405
).pack(pady=18, padx=20, anchor="w")

# ── Subtitle ──────────────────────────────────────────────────────────────────
CTkLabel(
    root,
    text="Choose a colour theme for Freeply:",
    font=SubHeaderFont,        # noqa: F405
    text_color=SubHeaderColor, # noqa: F405
    fg_color=BackGroundColor   # noqa: F405
).pack(anchor="w", padx=24, pady=(20, 8))

# ── Theme selection variable ──────────────────────────────────────────────────
selected_theme = StringVar(value=read_current_theme())

# ── Theme grid ────────────────────────────────────────────────────────────────
grid_frame = CTkFrame(root, fg_color=BackGroundColor, corner_radius=0)  # noqa: F405
grid_frame.pack(padx=24, pady=4, fill="x")

def make_theme_card(parent, theme_name, row, col):
    bg, fg = THEME_PREVIEWS[theme_name]

    card = CTkFrame(parent, fg_color=bg, corner_radius=12, width=130, height=80)
    card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
    card.grid_propagate(False)

    label = CTkLabel(card, text=theme_name, font=BodyFont,   # noqa: F405
                     text_color=fg, fg_color=bg)
    label.place(relx=0.5, rely=0.38, anchor="center")

    rb = CTkRadioButton(
        card,
        text="",
        variable=selected_theme,
        value=theme_name,
        fg_color=fg,
        border_color=fg,
        hover_color=fg
    )
    rb.place(relx=0.5, rely=0.72, anchor="center")

for i, name in enumerate(THEMES):
    make_theme_card(grid_frame, name, row=i // 4, col=i % 4)

for c in range(4):
    grid_frame.columnconfigure(c, weight=1)

# ── Font size note ────────────────────────────────────────────────────────────
CTkLabel(
    root,
    text="Font size and spacing are managed directly in Settings/settings.py.",
    font=SmallFont,          # noqa: F405
    text_color=BodyColor,    # noqa: F405
    fg_color=BackGroundColor # noqa: F405
).pack(anchor="w", padx=24, pady=(8, 0))

# ── Save / Cancel ─────────────────────────────────────────────────────────────
btn_frame = CTkFrame(root, fg_color=BackGroundColor, corner_radius=0)  # noqa: F405
btn_frame.pack(fill="x", padx=24, pady=20)

status_label = CTkLabel(
    btn_frame, text="", font=SmallFont,   # noqa: F405
    text_color=SubHeaderColor,            # noqa: F405
    fg_color=BackGroundColor              # noqa: F405
)
status_label.pack(side="left")

def save_settings():
    new = selected_theme.get()
    write_theme(new)
    status_label.configure(
        text=f"✓ Theme saved as '{new}'. Restart Freeply to apply."
    )

def cancel():
    root.destroy()

CTkButton(
    btn_frame, text="Cancel",
    command=cancel,
    font=BodyFont,                 # noqa: F405
    fg_color=ButtonColor,          # noqa: F405
    text_color=SubHeaderColor,     # noqa: F405
    hover_color=AccentColor,       # noqa: F405
    width=110
).pack(side="right", padx=(6, 0))

CTkButton(
    btn_frame, text="Save",
    command=save_settings,
    font=BodyFont,                 # noqa: F405
    fg_color=HeaderColor,          # noqa: F405
    text_color="#FFFFFF",
    hover_color=SubHeaderColor,    # noqa: F405
    width=110
).pack(side="right")

root.mainloop()
