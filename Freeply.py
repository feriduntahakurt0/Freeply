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
import random
import threading
import subprocess
import webbrowser
import tkinter as tk

from customtkinter import *

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
MUSICS_DIR = os.path.join(BASE_DIR, "Musics")
os.makedirs(MUSICS_DIR, exist_ok=True)

sys.path.insert(0, os.path.join(BASE_DIR, "Settings"))
from settings import *    # noqa: F403

AUDIO_EXTS = (".mp3", ".wav", ".flac", ".aac", ".m4a", ".ogg")

# ── Optional pygame ───────────────────────────────────────────────────────────
try:
    import pygame
    pygame.mixer.init(frequency=44100)
    PYGAME_OK = True
except ImportError:
    PYGAME_OK = False

# ── App window ────────────────────────────────────────────────────────────────
set_appearance_mode("light")
set_default_color_theme("blue")

PLAYER_BAR_H  = 120
VISUALISER_H  = 80
SIDEBAR_W     = 210
_vis_expanded = False

root = CTk()
root.geometry(windowSize)
root.title(f"Freeply {version}")
root.configure(fg_color=BackGroundColor)
root.resizable(True, True)

# ═════════════════════════════════════════════════════════════════════════════
#  PLAYER STATE
# ═════════════════════════════════════════════════════════════════════════════
_playlist      = []
_current_index = 0
_repeat_mode   = False
_is_playing    = False
_song_length   = 0.0
_seek_dragging = False
_seek_offset   = 0.0   # saniye cinsinden seek sonrası başlangıç noktası
_play_start_t  = 0.0   # seek/play anındaki time.time() değeri

import time as _time

# ── EQ State ──────────────────────────────────────────────────────────────────
_eq_bass   = 0.0   # dB, -12 … +12
_eq_mid    = 0.0
_eq_treble = 0.0
_eq_panel_open    = False
_current_filepath = None

# ── PCM Cache — decode bir kez yapılır, EQ defalarca uygulanır ───────────────
_pcm_cache        = None   # numpy float32 array, shape (N, ch)
_pcm_sr           = 44100
_pcm_channels     = 2
_pcm_filepath     = None   # hangi dosya cache'lendi
_pcm_ready        = False  # cache hazır mı


def get_audio_files():
    try:
        files = sorted([
            f for f in os.listdir(MUSICS_DIR)
            if os.path.isfile(os.path.join(MUSICS_DIR, f))
            and not f.startswith(".")
            and f.lower().endswith(AUDIO_EXTS)
        ])
        return [os.path.join(MUSICS_DIR, f) for f in files]
    except FileNotFoundError:
        return []


def get_song_length(filepath):
    try:
        from mutagen import File as MutagenFile
        audio = MutagenFile(filepath)
        if audio and audio.info:
            return float(audio.info.length)
    except Exception:
        pass
    if PYGAME_OK:
        try:
            snd = pygame.mixer.Sound(filepath)
            return snd.get_length()
        except Exception:
            pass
    return 0.0


def _decode_to_cache(filepath):
    """Dosyayı bir kez PCM float32'ye çevirir, cache'e yazar. Arka thread'de çalışır."""
    global _pcm_cache, _pcm_sr, _pcm_channels, _pcm_filepath, _pcm_ready
    _pcm_ready    = False
    _pcm_filepath = filepath
    try:
        import numpy as np
        try:
            from pydub import AudioSegment
            seg           = AudioSegment.from_file(filepath)
            _pcm_sr       = seg.frame_rate
            _pcm_channels = seg.channels
            raw           = np.frombuffer(seg.raw_data, dtype=np.int16)
            _pcm_cache    = raw.reshape(-1, _pcm_channels).astype(np.float32)
        except Exception:
            # pydub yoksa pygame fallback
            snd           = pygame.mixer.Sound(filepath)
            arr           = pygame.sndarray.array(snd)
            _pcm_sr       = pygame.mixer.get_init()[0]
            _pcm_channels = 2 if arr.ndim == 2 else 1
            _pcm_cache    = arr.astype(np.float32)
            if arr.ndim == 1:
                _pcm_cache = _pcm_cache.reshape(-1, 1)
        _pcm_ready = True
    except Exception:
        _pcm_cache = None
        _pcm_ready = False


def _biquad_vectorized(data, ftype, freq, gain_db, sr, Q=0.707):
    """
    Biquad IIR filtresi — tamamen vektörel, Python döngüsü yok.
    scipy varsa lfilter (C'de), yoksa numpy cumsum trick.
    """
    import math, numpy as np
    A  = 10 ** (gain_db / 40.0)
    w0 = 2 * math.pi * freq / sr
    cw, sw, sq = math.cos(w0), math.sin(w0), math.sqrt(A)
    alpha = sw / (2 * Q)

    if ftype == "low":
        b0=A*((A+1)-(A-1)*cw+2*sq*alpha); b1=2*A*((A-1)-(A+1)*cw); b2=A*((A+1)-(A-1)*cw-2*sq*alpha)
        a0=(A+1)+(A-1)*cw+2*sq*alpha;     a1=-2*((A-1)+(A+1)*cw);  a2=(A+1)+(A-1)*cw-2*sq*alpha
    elif ftype == "high":
        b0=A*((A+1)+(A-1)*cw+2*sq*alpha); b1=-2*A*((A-1)+(A+1)*cw); b2=A*((A+1)+(A-1)*cw-2*sq*alpha)
        a0=(A+1)-(A-1)*cw+2*sq*alpha;     a1=2*((A-1)-(A+1)*cw);    a2=(A+1)-(A-1)*cw-2*sq*alpha
    else:
        b0=1+alpha*A; b1=-2*cw; b2=1-alpha*A
        a0=1+alpha/A; a1=-2*cw; a2=1-alpha/A

    b = np.array([b0/a0, b1/a0, b2/a0])
    a = np.array([1.0,   a1/a0, a2/a0])

    try:
        from scipy.signal import lfilter
        return lfilter(b, a, data, axis=0).astype(np.float32)
    except ImportError:
        pass

    # Pure numpy: Direct Form II transposed, tüm kanallar paralel
    n, ch = data.shape
    x = data.astype(np.float64)
    y = np.empty_like(x)
    z0 = np.zeros(ch); z1 = np.zeros(ch)
    # Vektörel olmayan tek alternatif burada kaçınılmaz ama
    # numba/cython olmadan saf numpy'de IIR döngüsüz uygulanamaz.
    # Ancak float64 numpy döngüsü Python int döngüsünden ~10x hızlıdır.
    for i in range(n):
        y[i] = b[0]*x[i] + z0
        z0   = b[1]*x[i] - a[1]*y[i] + z1
        z1   = b[2]*x[i] - a[2]*y[i]
    return y.astype(np.float32)


def _apply_eq_and_play(filepath, start_pos=0.0):
    """
    EQ uygula ve çal. Cache hazırsa decode yok — sadece filtre.
    EQ sıfırsa direkt orijinal dosyayı çalar (en hızlı yol).
    """
    bass, mid, treble = _eq_bass, _eq_mid, _eq_treble

    def _do():
        try:
            if bass == 0 and mid == 0 and treble == 0:
                root.after(0, lambda: _play_processed(filepath, start_pos))
                return

            import numpy as np, wave, tempfile

            # Cache hazır ve aynı dosyaysa decode atla
            if _pcm_ready and _pcm_filepath == filepath and _pcm_cache is not None:
                data = _pcm_cache.copy()
                sr   = _pcm_sr
                ch   = _pcm_channels
            else:
                # Cache yoksa decode et (ve cache'e yaz)
                _decode_to_cache(filepath)
                if _pcm_cache is None:
                    root.after(0, lambda: _play_processed(filepath, start_pos))
                    return
                data = _pcm_cache.copy()
                sr   = _pcm_sr
                ch   = _pcm_channels

            if bass   != 0: data = _biquad_vectorized(data, "low",  200,  bass,   sr)
            if mid    != 0: data = _biquad_vectorized(data, "peak", 1000, mid,    sr, Q=1.4)
            if treble != 0: data = _biquad_vectorized(data, "high", 4000, treble, sr)

            out = np.clip(data, -32768, 32767).astype(np.int16)
            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            tmp.close()
            with wave.open(tmp.name, "w") as wf:
                wf.setnchannels(ch)
                wf.setsampwidth(2)
                wf.setframerate(sr)
                wf.writeframes(out.tobytes())

            root.after(0, lambda: _play_processed(tmp.name, start_pos))
        except Exception:
            root.after(0, lambda: _play_processed(filepath, start_pos))

    threading.Thread(target=_do, daemon=True).start()


def _play_processed(path, start_pos=0.0):
    global _play_start_t, _seek_offset
    pygame.mixer.music.load(path)
    if start_pos > 0:
        pygame.mixer.music.play(start=start_pos)
    else:
        pygame.mixer.music.play()
    _seek_offset  = start_pos
    _play_start_t = _time.time()
    vol_var.set(vol_var.get())
    pygame.mixer.music.set_volume(vol_var.get())


def fmt_time(seconds):
    seconds = max(0, int(seconds))
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


# ═════════════════════════════════════════════════════════════════════════════
#  MARQUEE LABEL  — Spotify tarzı kayan metin
# ═════════════════════════════════════════════════════════════════════════════
class MarqueeLabel(tk.Canvas):
    """
    Tek satır metin gösterir. Metin görüntü alanına sığmıyorsa
    Spotify tarzı ileri→bekle→geri→bekle döngüsüyle kayar.
    """
    STEP_PX   = 1      # her adımda kaç piksel kayar
    INTERVAL  = 30     # ms, ~33 fps
    PAUSE_MS  = 1800   # uçlarda bekleme süresi (ms)

    def __init__(self, parent, text="", font=None, fg=None,
                 bg=None, height=22, **kwargs):
        _bg = bg or "black"
        _fg = fg or "white"
        super().__init__(parent, bg=_bg, highlightthickness=0,
                         height=height, **kwargs)
        self._text    = text
        self._font    = font or ("Arial", 13, "bold")
        self._fg      = _fg
        self._bg      = _bg
        self._offset  = 0
        self._dir     = 1          # 1=ileri, -1=geri
        self._job     = None
        self._text_w  = 0
        self.bind("<Configure>", self._on_resize)
        self._draw()
        self._schedule()

    # ── Public ────────────────────────────────────────────────────────────────
    def configure(self, text=None, fg=None, bg=None, **kwargs):
        if text is not None and text != self._text:
            self._text   = text
            self._offset = 0
            self._dir    = 1
            self._measure()
            self._draw()
        if fg is not None:
            self._fg = fg
        if bg is not None:
            self._bg = bg
            super().configure(bg=bg)
        super().configure(**kwargs)

    # keep CTk-style alias
    def cget(self, key):
        if key == "text":
            return self._text
        return super().cget(key)

    # ── Internal ──────────────────────────────────────────────────────────────
    def _measure(self):
        """Metnin piksel genişliğini ölç."""
        import tkinter.font as tkfont
        try:
            f = tkfont.Font(font=self._font)
            self._text_w = f.measure(self._text)
        except Exception:
            self._text_w = len(self._text) * 8

    def _on_resize(self, event=None):
        self._measure()
        self._draw()

    def _draw(self):
        self.delete("all")
        self.create_text(
            -self._offset, self.winfo_reqheight() // 2,
            text=self._text, anchor="w",
            font=self._font, fill=self._fg
        )

    def _canvas_w(self):
        w = self.winfo_width()
        return w if w > 1 else 200

    def _schedule(self):
        self._job = self.after(self.INTERVAL, self._tick)

    def _tick(self):
        if not self.winfo_exists():
            return
        cw = self._canvas_w()
        if self._text_w <= cw:
            # Metin sığıyor — sabit dur
            self._offset = 0
            self._draw()
            self._job = self.after(self.INTERVAL, self._tick)
            return

        max_offset = self._text_w - cw + 10

        if self._dir == 1:                       # ileri kayıyor
            self._offset += self.STEP_PX
            if self._offset >= max_offset:
                self._offset = max_offset
                self._draw()
                self._job = self.after(self.PAUSE_MS, self._reverse)
                return
        else:                                    # geri kayıyor
            self._offset -= self.STEP_PX
            if self._offset <= 0:
                self._offset = 0
                self._draw()
                self._job = self.after(self.PAUSE_MS, self._reverse)
                return

        self._draw()
        self._job = self.after(self.INTERVAL, self._tick)

    def _reverse(self):
        if not self.winfo_exists():
            return
        self._dir *= -1
        self._job = self.after(self.INTERVAL, self._tick)


def parse_filename(filepath):
    """'Sanatçı - Şarkı adı.mp3' → (artist, title). Tire yoksa ('', name)."""
    stem = os.path.splitext(os.path.basename(filepath))[0]
    if " - " in stem:
        artist, _, title = stem.partition(" - ")
        return artist.strip(), title.strip()
    return "", stem.strip()


def song_card(parent, filepath, on_play, width=420):
    """İki satırlı şarkı kartı: bold şarkı adı + italic sanatçı."""
    artist, title = parse_filename(filepath)

    card = CTkFrame(parent, fg_color=SideBarColor,
                    corner_radius=8, width=width, height=52)
    card.pack(anchor="w", pady=3)
    card.pack_propagate(False)

    # Sol: play ikonu
    play_btn = CTkButton(
        card, text="♪", width=36, height=52,
        font=("Arial", 16), fg_color=SideBarColor,
        text_color=SubHeaderColor, hover_color=ButtonColor,
        corner_radius=8, command=on_play
    )
    play_btn.pack(side="left")

    # Sağ: şarkı adı + sanatçı
    text_frame = CTkFrame(card, fg_color=SideBarColor, corner_radius=0)
    text_frame.pack(side="left", fill="both", expand=True, padx=(4, 8))

    CTkLabel(
        text_frame, text=title,
        font=("Arial", 13, "bold"),
        text_color=SubHeaderColor,
        fg_color=SideBarColor, anchor="w"
    ).pack(anchor="w")

    if artist:
        CTkLabel(
            text_frame, text=artist,
            font=("Arial", 11, "italic"),
            text_color=BodyColor,
            fg_color=SideBarColor, anchor="w"
        ).pack(anchor="w")

    # Kartın tamamına tıklanınca da çalsın
    for widget in (card, text_frame):
        widget.bind("<Button-1>", lambda e: on_play())

    return card


# ═════════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ═════════════════════════════════════════════════════════════════════════════
sidebar = CTkFrame(root, width=SIDEBAR_W, fg_color=SideBarColor, corner_radius=0)
sidebar.place(x=0, y=0, relheight=1.0)
sidebar.pack_propagate(False)

CTkLabel(
    sidebar, text=f"Freeply {version}",
    font=HeaderFont, text_color=HeaderColor,
    fg_color=SideBarColor, anchor="w"
).pack(fill="x", padx=emptyBetweenCorner, pady=(emptyBetweenCorner + 6, 2))

CTkLabel(
    sidebar, text="Free Music Player",
    font=SmallFont, text_color=BodyColor,
    fg_color=SideBarColor, anchor="w"
).pack(fill="x", padx=emptyBetweenCorner, pady=(0, 14))

CTkFrame(sidebar, fg_color=AccentColor, height=2, corner_radius=1).pack(
    fill="x", padx=emptyBetweenCorner, pady=(0, 12))

# ═════════════════════════════════════════════════════════════════════════════
#  CONTENT AREA
# ═════════════════════════════════════════════════════════════════════════════
content = CTkFrame(root, fg_color=BackGroundColor, corner_radius=0)
content.place(x=SIDEBAR_W, y=0, relwidth=1.0, relheight=1.0)


def clear_content():
    for w in content.winfo_children():
        w.destroy()


def section_title(text):
    CTkLabel(
        content, text=text,
        font=HeaderFont, text_color=HeaderColor,
        fg_color=BackGroundColor, anchor="w"
    ).pack(anchor="w", padx=28, pady=(26, 6))
    CTkFrame(content, fg_color=AccentColor, height=2, corner_radius=1
             ).pack(fill="x", padx=28, pady=(0, 16))


def body_text(text, padx=28, pady=(0, 10)):
    CTkLabel(
        content, text=text,
        font=BodyFont, text_color=BodyColor,
        fg_color=BackGroundColor,
        anchor="w", wraplength=680, justify="left"
    ).pack(anchor="w", padx=padx, pady=pady)


# ═════════════════════════════════════════════════════════════════════════════
#  VISUALISER  (sits above the player bar, drawn on a tk.Canvas)
# ═════════════════════════════════════════════════════════════════════════════
vis_canvas = tk.Canvas(
    root, height=VISUALISER_H,
    bg=PlayerBarColor, highlightthickness=0
)
vis_canvas.place(
    x=SIDEBAR_W, rely=1.0,
    y=-(PLAYER_BAR_H + VISUALISER_H),
    relwidth=1.0, height=VISUALISER_H
)

# ── Büyük görünüm overlay — içerik alanını tamamen kaplar ─────────────────────
# tk.Frame kullanıyoruz çünkü CTkFrame place() ile width/height kabul etmiyor
vis_overlay = tk.Frame(root, bg=PlayerBarColor)
# Başta gizli, _toggle_visualiser çağrılınca gösterilir

# Üstte ortalı şarkı adı + sanatçı
vis_title_lbl = tk.Label(
    vis_overlay, text="No song playing",
    font=("Arial", 22, "bold"), fg=HeaderColor,
    bg=PlayerBarColor, anchor="center"
)
vis_title_lbl.place(relx=0.5, y=22, anchor="n")

vis_artist_lbl = tk.Label(
    vis_overlay, text="",
    font=("Arial", 14, "italic"), fg=BodyColor,
    bg=PlayerBarColor, anchor="center"
)
vis_artist_lbl.place(relx=0.5, y=58, anchor="n")

# Büyük visualiser canvas — overlay içinde, başlık alanı altından başlar
vis_big_canvas = tk.Canvas(
    vis_overlay, bg=PlayerBarColor, highlightthickness=0
)
vis_big_canvas.place(x=0, y=88, relwidth=1.0, relheight=1.0)

VIS_BAR_COUNT = 48
_vis_heights  = [3.0] * VIS_BAR_COUNT
_vis_targets  = [3.0] * VIS_BAR_COUNT
_vis_job      = None
_current_filepath = None  # track which file is loaded for numpy analysis

# Try to load numpy for real audio analysis
try:
    import numpy as np
    NUMPY_OK = True
except ImportError:
    NUMPY_OK = False

# Audio sample cache
_audio_samples  = None   # numpy array of normalised mono samples
_audio_sr       = 44100  # sample rate


def _load_audio_samples(filepath):
    """Load audio into a mono float32 numpy array via pygame's sndarray."""
    global _audio_samples, _audio_sr
    _audio_samples = None
    if not NUMPY_OK or not PYGAME_OK:
        return
    try:
        snd     = pygame.mixer.Sound(filepath)
        arr     = pygame.sndarray.array(snd)
        # Convert stereo → mono
        if arr.ndim == 2:
            arr = arr.mean(axis=1)
        # Normalise to [-1, 1]
        maxval = max(abs(arr.max()), abs(arr.min()), 1)
        _audio_samples = arr.astype(np.float32) / maxval
        _audio_sr      = pygame.mixer.get_init()[0]
    except Exception:
        _audio_samples = None


def _get_vis_targets_from_audio():
    """
    Compute per-bar amplitude from the audio window around the current
    playback position. Returns a list of VIS_BAR_COUNT floats in [0,1].
    """
    if _audio_samples is None or not PYGAME_OK:
        return None
    pos_ms = pygame.mixer.music.get_pos()
    if pos_ms < 0:
        return None

    pos_s      = pos_ms / 1000.0
    win_size   = 0.08                          # 80 ms window
    start_s    = max(0.0, pos_s - win_size / 2)
    end_s      = start_s + win_size
    start_i    = int(start_s * _audio_sr)
    end_i      = int(end_s   * _audio_sr)
    end_i      = min(end_i, len(_audio_samples))
    chunk      = _audio_samples[start_i:end_i]

    if len(chunk) < VIS_BAR_COUNT:
        return None

    # Split chunk into VIS_BAR_COUNT frequency-like bands using FFT
    fft_vals   = np.abs(np.fft.rfft(chunk))
    fft_vals   = fft_vals[:len(fft_vals) // 2 + 1]   # keep positive freqs

    if len(fft_vals) < VIS_BAR_COUNT:
        return None

    # Map FFT bins to bars (log-spaced feels more natural)
    indices    = np.logspace(0, np.log10(len(fft_vals) - 1),
                             VIS_BAR_COUNT + 1, dtype=int)
    indices    = np.clip(indices, 0, len(fft_vals) - 1)
    bars       = []
    for j in range(VIS_BAR_COUNT):
        lo, hi = indices[j], max(indices[j] + 1, indices[j + 1])
        bars.append(float(fft_vals[lo:hi].mean()))

    # Normalise
    peak = max(bars) or 1.0
    return [v / peak for v in bars]


def _vis_update():
    global _vis_job
    if not vis_canvas.winfo_exists():
        return

    # Küçük canvas her zaman çizilir
    vis_canvas.delete("all")
    w = vis_canvas.winfo_width()
    h = vis_canvas.winfo_height() or VISUALISER_H
    if w < 10:
        _vis_job = root.after(40, _vis_update)
        return

    bar_w = w / VIS_BAR_COUNT
    gap   = max(1, bar_w * 0.18)
    bw    = bar_w - gap

    if _is_playing:
        audio_vals = _get_vis_targets_from_audio()
        if audio_vals is not None:
            for i, v in enumerate(audio_vals):
                _vis_targets[i] = v * (h - 4)
        else:
            for i in range(VIS_BAR_COUNT):
                if random.random() < 0.3:
                    peak = random.uniform(0.04, 1.0) ** 1.5
                    _vis_targets[i] = peak * (h - 4)
    else:
        for i in range(VIS_BAR_COUNT):
            _vis_targets[i] = 3.0

    for i in range(VIS_BAR_COUNT):
        _vis_heights[i] += (_vis_targets[i] - _vis_heights[i]) * 0.25

    for i in range(VIS_BAR_COUNT):
        x0  = i * bar_w + gap / 2
        x1  = x0 + bw
        bh  = max(3, _vis_heights[i])
        y0  = h - bh
        col = HeaderColor if (bh / h) > 0.55 else AccentColor
        vis_canvas.create_rectangle(x0, y0, x1, h, fill=col, outline="")

    # Büyük overlay canvas — genişletilmiş modda da çiz
    if _vis_expanded and vis_big_canvas.winfo_exists():
        vis_big_canvas.delete("all")
        bw2 = vis_big_canvas.winfo_width()
        bh2 = vis_big_canvas.winfo_height()
        if bw2 > 10 and bh2 > 10:
            bar_w2 = bw2 / VIS_BAR_COUNT
            gap2   = max(2, bar_w2 * 0.15)
            b2     = bar_w2 - gap2
            # Büyük modda barların hedef yüksekliğini yeniden hesapla
            big_targets = []
            if _is_playing:
                audio_vals2 = _get_vis_targets_from_audio()
                if audio_vals2 is not None:
                    big_targets = [v * (bh2 - 6) for v in audio_vals2]
            if not big_targets:
                big_targets = [_vis_heights[i] * (bh2 / max(h, 1))
                               for i in range(VIS_BAR_COUNT)]
            for i in range(VIS_BAR_COUNT):
                x0  = i * bar_w2 + gap2 / 2
                x1  = x0 + b2
                bhi = max(4, big_targets[i])
                y0  = bh2 - bhi
                col = HeaderColor if (bhi / bh2) > 0.55 else AccentColor
                vis_big_canvas.create_rectangle(x0, y0, x1, bh2,
                                                fill=col, outline="")

    _vis_job = root.after(40, _vis_update)


def start_visualiser():
    global _vis_job
    if _vis_job is None:
        _vis_update()


# ═════════════════════════════════════════════════════════════════════════════
#  PLAYER BAR  — 2 sütun: Sol=şarkı bilgisi, Sağ=butonlar+seek
# ═════════════════════════════════════════════════════════════════════════════
BAR_BG      = PlayerBarColor   # temaya özgü belirgin bar rengi
BAR_TEXT    = HeaderColor
BAR_SUBTEXT = BodyColor
BAR_ACCENT  = AccentColor
BAR_BTN_FG  = ButtonColor

player_bar = CTkFrame(
    root, fg_color=BAR_BG,
    corner_radius=0, height=PLAYER_BAR_H
)
player_bar.place(
    x=SIDEBAR_W, rely=1.0, y=-PLAYER_BAR_H,
    relwidth=1.0
)
player_bar.pack_propagate(False)

# Sol sütun: şarkı bilgisi
bar_left = CTkFrame(player_bar, fg_color=BAR_BG, corner_radius=0)
bar_left.place(relx=0, rely=0, relwidth=0.28, relheight=1.0)

# ── SOL: müzik notu ikonu + şarkı adı + sanatçı ──────────────────────────────
CTkLabel(
    bar_left, text="♪",
    font=("Arial", 26), text_color=BAR_ACCENT,
    fg_color=BAR_BG
).place(relx=0.05, rely=0.5, anchor="w")

info_frame = CTkFrame(bar_left, fg_color=BAR_BG, corner_radius=0)
info_frame.place(relx=0.18, rely=0.5, anchor="w", relwidth=0.76)

song_label = MarqueeLabel(
    info_frame, text="No song playing",
    font=("Arial", 13, "bold"),
    fg=BAR_TEXT, bg=BAR_BG, height=22
)
song_label.pack(fill="x", anchor="w")

artist_label = CTkLabel(
    info_frame, text="",
    font=("Arial", 11, "italic"), text_color=BAR_SUBTEXT,
    fg_color=BAR_BG, anchor="w"
)
artist_label.pack(anchor="w", pady=(1, 0))

# ── ORTA: butonlar + seek — tüm barın x ortasına hizalı ─────────────────────

def _spoti_btn(parent, text, cmd, size=18, bold=False, width=36):
    fw = "bold" if bold else "normal"
    return CTkButton(
        parent, text=text, command=cmd,
        font=("Arial", size, fw),
        fg_color=BAR_BG, text_color=BAR_SUBTEXT,
        hover_color=BAR_BTN_FG,
        width=width, height=34, corner_radius=18
    )

# center_stack doğrudan player_bar üzerine yerleştirilir,
# relx=0.5 → tüm bar genişliğinin tam ortası
center_stack = CTkFrame(player_bar, fg_color=BAR_BG, corner_radius=0)
center_stack.place(relx=0.5, rely=0.5, anchor="center")

# Kontrol butonları satırı
ctrl_row = CTkFrame(center_stack, fg_color=BAR_BG, corner_radius=0)
ctrl_row.pack(anchor="center")

btn_prev   = _spoti_btn(ctrl_row, "⏮",     lambda: _change_song(-1), size=16)
btn_play   = _spoti_btn(ctrl_row, "▶",      lambda: _play_pause(),    size=20, bold=True, width=44)
btn_next   = _spoti_btn(ctrl_row, "⏭",     lambda: _change_song(+1), size=16)
btn_repeat = _spoti_btn(ctrl_row, "Repeat", lambda: _toggle_repeat(), size=12, width=66)
btn_eq     = _spoti_btn(ctrl_row, "EQ",     lambda: _toggle_eq_panel(), size=12, width=44)

btn_play.configure(
    fg_color=BAR_TEXT, text_color=BAR_BG,
    hover_color=BAR_ACCENT, corner_radius=22
)

for b in (btn_prev, btn_play, btn_next, btn_repeat, btn_eq):
    b.pack(side="left", padx=5)

# ── EQ Panel (player_bar'ın üstünde açılır) ──────────────────────────────────
eq_panel = CTkFrame(root, fg_color=BAR_BG, corner_radius=12,
                    border_width=1, border_color=BAR_ACCENT)
# Başta gizli

_eq_bass_var   = tk.DoubleVar(value=0.0)
_eq_mid_var    = tk.DoubleVar(value=0.0)
_eq_treble_var = tk.DoubleVar(value=0.0)

# Panel başlığı
eq_header = CTkFrame(eq_panel, fg_color=BAR_BG, corner_radius=0)
eq_header.pack(fill="x", padx=14, pady=(10, 4))
CTkLabel(eq_header, text="Equalizer", font=("Arial", 13, "bold"),
         text_color=BAR_TEXT, fg_color=BAR_BG).pack(side="left")
CTkButton(eq_header, text="✕", width=24, height=24,
          font=("Arial", 11), fg_color=BAR_BG, text_color=BAR_SUBTEXT,
          hover_color=BAR_BTN_FG, corner_radius=6,
          command=lambda: _toggle_eq_panel()).pack(side="right")

# Separator
CTkFrame(eq_panel, fg_color=BAR_ACCENT, height=1, corner_radius=0
         ).pack(fill="x", padx=14, pady=(0, 10))

# Slider satırı yardımcısı
def _eq_slider_row(parent, label, var, cmd):
    row = CTkFrame(parent, fg_color=BAR_BG, corner_radius=0)
    row.pack(fill="x", padx=14, pady=3)
    CTkLabel(row, text=label, font=("Arial", 11, "bold"),
             text_color=BAR_SUBTEXT, fg_color=BAR_BG, width=52, anchor="w"
             ).pack(side="left")
    CTkLabel(row, text="-12", font=("Arial", 9),
             text_color=BAR_SUBTEXT, fg_color=BAR_BG).pack(side="left", padx=(0,2))
    sl = CTkSlider(row, from_=-12, to=12, variable=var, command=cmd,
                   button_color=BAR_TEXT, button_hover_color=BAR_ACCENT,
                   progress_color=BAR_TEXT, fg_color=BAR_BTN_FG,
                   width=160, height=14)
    sl.pack(side="left")
    CTkLabel(row, text="+12", font=("Arial", 9),
             text_color=BAR_SUBTEXT, fg_color=BAR_BG).pack(side="left", padx=(2,8))
    val_lbl = CTkLabel(row, text=" 0 dB", font=("Arial", 10),
                       text_color=BAR_TEXT, fg_color=BAR_BG, width=46)
    val_lbl.pack(side="left")
    return sl, val_lbl

_eq_debounce_job = None

def _on_eq_change(_=None):
    global _eq_bass, _eq_mid, _eq_treble, _eq_debounce_job
    _eq_bass   = _eq_bass_var.get()
    _eq_mid    = _eq_mid_var.get()
    _eq_treble = _eq_treble_var.get()
    bass_val.configure(text=f"{_eq_bass:+.0f} dB" if _eq_bass != 0 else " 0 dB")
    mid_val.configure( text=f"{_eq_mid:+.0f} dB"  if _eq_mid  != 0 else " 0 dB")
    treb_val.configure(text=f"{_eq_treble:+.0f} dB" if _eq_treble != 0 else " 0 dB")
    # Debounce: kullanıcı 600ms durunca işlemi başlat
    if _eq_debounce_job:
        root.after_cancel(_eq_debounce_job)
    def _commit():
        if _is_playing and _current_filepath:
            cur_pos = min(_seek_offset + (_time.time() - _play_start_t), _song_length)
            _apply_eq_and_play(_current_filepath, max(0.0, cur_pos))
    _eq_debounce_job = root.after(800, _commit)

_, bass_val   = _eq_slider_row(eq_panel, "Bass",   _eq_bass_var,   _on_eq_change)
_, mid_val    = _eq_slider_row(eq_panel, "Mid",    _eq_mid_var,    _on_eq_change)
_, treb_val   = _eq_slider_row(eq_panel, "Treble", _eq_treble_var, _on_eq_change)

# Preset butonları
preset_row = CTkFrame(eq_panel, fg_color=BAR_BG, corner_radius=0)
preset_row.pack(fill="x", padx=14, pady=(8, 4))
CTkLabel(preset_row, text="Presets:", font=("Arial", 10),
         text_color=BAR_SUBTEXT, fg_color=BAR_BG).pack(side="left", padx=(0,6))

PRESETS = {
    "Flat":    (0,   0,   0),
    "Bass+":   (8,   0,  -2),
    "Treble+": (-2,  0,   8),
    "Pop":     (-1,  3,   4),
    "Rock":    (5,  -1,   4),
    "Jazz":    (3,   2,  -1),
}

def _apply_preset(b, m, t):
    _eq_bass_var.set(b); _eq_mid_var.set(m); _eq_treble_var.set(t)
    _on_eq_change()

for name, (b, m, t) in PRESETS.items():
    CTkButton(preset_row, text=name, width=54, height=24,
              font=("Arial", 10), fg_color=BAR_BTN_FG,
              text_color=BAR_SUBTEXT, hover_color=BAR_ACCENT,
              corner_radius=6,
              command=lambda b=b, m=m, t=t: _apply_preset(b, m, t)
              ).pack(side="left", padx=3)

CTkFrame(eq_panel, fg_color=BAR_BG, height=10, corner_radius=0).pack()

def _toggle_eq_panel():
    global _eq_panel_open
    if _eq_panel_open:
        eq_panel.place_forget()
        btn_eq.configure(fg_color=BAR_BG, text_color=BAR_SUBTEXT)
        _eq_panel_open = False
    else:
        # Player bar'ın üstüne, ortaya hizalı konumlandır
        root.update_idletasks()
        pw = root.winfo_width()
        ph = eq_panel.winfo_reqheight()
        bar_y = root.winfo_height() - PLAYER_BAR_H - VISUALISER_H
        eq_panel.place(x=pw//2 - 220, y=bar_y - ph - 8)
        eq_panel.lift()
        btn_eq.configure(fg_color=BAR_BTN_FG, text_color=BAR_TEXT)
        _eq_panel_open = True

# Seek satırı — butonların hemen altında, genişlik sabit
seek_row = CTkFrame(center_stack, fg_color=BAR_BG, corner_radius=0)
seek_row.pack(fill="x", pady=(6, 0))

time_left_lbl = CTkLabel(
    seek_row, text="0:00",
    font=("Arial", 11), text_color=BAR_SUBTEXT,
    fg_color=BAR_BG, width=34
)
time_left_lbl.pack(side="left")

seek_var = tk.DoubleVar(value=0)
seek_slider = CTkSlider(
    seek_row, from_=0, to=100, variable=seek_var,
    button_color=BAR_TEXT,
    button_hover_color=BAR_ACCENT,
    progress_color=BAR_TEXT,
    fg_color=BAR_BTN_FG,
    width=500, height=6
)
seek_slider.pack(side="left", padx=4)

time_right_lbl = CTkLabel(
    seek_row, text="0:00",
    font=("Arial", 11), text_color=BAR_SUBTEXT,
    fg_color=BAR_BG, width=34
)
time_right_lbl.pack(side="left")

# ── Ses kontrolü — seek satırının hemen sağında ──────────────────────────────
CTkFrame(seek_row, fg_color=BAR_SUBTEXT, width=1, height=14,
         corner_radius=0).pack(side="left", padx=(10, 6))

vol_var = tk.DoubleVar(value=1.0)

vol_icon = CTkLabel(
    seek_row, text="Vol",
    font=("Arial", 10, "bold"), text_color=BAR_SUBTEXT,
    fg_color=BAR_BG, width=24
)
vol_icon.pack(side="left")

def _on_volume_change(val):
    v = float(val)
    if PYGAME_OK:
        pygame.mixer.music.set_volume(v)
    if v == 0:
        vol_icon.configure(text="Mute")
    else:
        vol_icon.configure(text="Vol")

vol_slider = CTkSlider(
    seek_row, from_=0, to=1, variable=vol_var,
    command=_on_volume_change,
    button_color=BAR_TEXT,
    button_hover_color=BAR_ACCENT,
    progress_color=BAR_TEXT,
    fg_color=BAR_BTN_FG,
    height=6, width=90
)
vol_slider.pack(side="left", padx=(2, 0))

# ── Visualiser genişlet butonu — bar_left alt kısmı ─────────────────────────
btn_vis_expand = CTkButton(
    bar_left,
    text="⌃  Vis",
    command=lambda: _toggle_visualiser(),
    font=("Arial", 9, "bold"),
    fg_color=BAR_BTN_FG, text_color=BAR_SUBTEXT,
    hover_color=BAR_ACCENT,
    width=52, height=18, corner_radius=5
)
btn_vis_expand.place(relx=0.18, rely=0.88, anchor="sw")


# ── Playback functions (defined before buttons) ───────────────────────────────
def _open_fallback(filepath):
    if sys.platform == "win32":
        os.startfile(filepath)
    elif sys.platform == "darwin":
        subprocess.call(["open", filepath])
    else:
        subprocess.call(["xdg-open", filepath])


def _load_and_play(filepath, start_pos=0.0):
    global _is_playing, _song_length, _current_index, _seek_offset, _play_start_t, _current_filepath
    if not PYGAME_OK:
        _open_fallback(filepath)
        song_label.configure(text=f"♪  {os.path.splitext(os.path.basename(filepath))[0]}  (external player)")
        return

    _current_filepath = filepath
    _is_playing    = True
    _seek_offset   = start_pos
    _play_start_t  = _time.time()

    # Uzunluk: mutagen en hızlı (dosyayı decode etmez)
    _song_length = get_song_length(filepath) or 1.0

    # PCM cache'i arka planda doldur (ilk EQ isteğinde hazır olsun)
    if _pcm_filepath != filepath:
        threading.Thread(target=_decode_to_cache, args=(filepath,), daemon=True).start()

    # EQ sıfırsa doğrudan çal, değilse pipeline
    _apply_eq_and_play(filepath, start_pos)

    # Visualiser için audio samples da paralel yükle
    threading.Thread(target=_load_audio_samples, args=(filepath,), daemon=True).start()

    artist, title = parse_filename(filepath)
    song_label.configure(text=title if title else filepath)
    artist_label.configure(text=artist)
    btn_play.configure(text="⏸", fg_color=BAR_TEXT, text_color=BAR_BG)
    time_left_lbl.configure(text=fmt_time(start_pos))
    time_right_lbl.configure(text=fmt_time(_song_length))
    seek_slider.configure(from_=0, to=_song_length)
    seek_var.set(start_pos)
    _update_vis_overlay_labels()
    start_visualiser()


def play_file(filepath, playlist=None, index=0):
    global _playlist, _current_index
    if playlist is not None:
        _playlist      = playlist
        _current_index = index
    elif filepath not in _playlist:
        _playlist      = [filepath]
        _current_index = 0
    else:
        _current_index = _playlist.index(filepath)
    _load_and_play(filepath)


def _play_pause():
    global _is_playing, _seek_offset, _play_start_t
    if not PYGAME_OK:
        return
    if _is_playing:
        pygame.mixer.music.pause()
        # Duraklatılan anki konumu offset olarak kaydet
        _seek_offset = _seek_offset + (_time.time() - _play_start_t)
        _seek_offset = max(0.0, min(_seek_offset, _song_length))
        _is_playing = False
        btn_play.configure(text="▶", fg_color=BAR_TEXT, text_color=BAR_BG)
    else:
        if pygame.mixer.music.get_pos() == -1 and _playlist:
            _load_and_play(_playlist[_current_index])
        else:
            pygame.mixer.music.unpause()
            _play_start_t = _time.time()   # unpause anından itibaren say
            _is_playing = True
            btn_play.configure(text="⏸", fg_color=BAR_TEXT, text_color=BAR_BG)
            start_visualiser()


def _change_song(direction):
    global _current_index
    if not _playlist:
        return
    # Repeat açıksa sonraki/önceki butonu mevcut şarkıyı yeniden başlatır
    if _repeat_mode:
        _load_and_play(_playlist[_current_index])
        return
    _current_index = (_current_index + direction) % len(_playlist)
    _load_and_play(_playlist[_current_index])


def _toggle_repeat():
    global _repeat_mode
    _repeat_mode = not _repeat_mode
    btn_repeat.configure(
        text="Repeat: ON" if _repeat_mode else "Repeat",
        text_color=BAR_TEXT if _repeat_mode else BAR_SUBTEXT,
        fg_color=BAR_BTN_FG if _repeat_mode else BAR_BG
    )


# ── Seek drag ─────────────────────────────────────────────────────────────────
def _seek_start(event):
    global _seek_dragging
    _seek_dragging = True


def _seek_end(event):
    global _seek_dragging, _seek_offset, _play_start_t
    if not PYGAME_OK or not _playlist:
        _seek_dragging = False
        return
    pos = seek_var.get()
    pos = max(0.0, min(pos, _song_length))

    # Konuma git — EQ aktifse pipeline üzerinden, değilse direkt
    if _eq_bass == 0 and _eq_mid == 0 and _eq_treble == 0:
        if _is_playing:
            pygame.mixer.music.set_pos(pos)
        else:
            pygame.mixer.music.load(_playlist[_current_index])
            pygame.mixer.music.play(start=pos)
            pygame.mixer.music.pause()
        _seek_offset  = pos
        _play_start_t = _time.time()
    else:
        # EQ açıkken: orijinal dosyayı yeniden işle + seek konumundan başlat
        if _current_filepath:
            was_playing = _is_playing
            _apply_eq_and_play(_current_filepath, pos)
            if not was_playing:
                root.after(300, lambda: pygame.mixer.music.pause())

    # Slider ve etiketleri hemen güncelle
    seek_var.set(pos)
    time_left_lbl.configure(text=fmt_time(pos))
    time_right_lbl.configure(text=fmt_time(max(0, _song_length - pos)))

    def _release_drag():
        global _seek_dragging
        _seek_dragging = False

    root.after(200, _release_drag)


seek_slider.bind("<ButtonPress-1>",   _seek_start)
seek_slider.bind("<ButtonRelease-1>", _seek_end)


# ── Progress ticker ────────────────────────────────────────────────────────────
def _tick():
    global _is_playing, _current_index
    if PYGAME_OK and _is_playing and not _seek_dragging:
        # Wall-clock tabanlı konum: get_pos() seek sonrası güvenilmez
        pos_s = _seek_offset + (_time.time() - _play_start_t)
        pos_s = max(0.0, min(pos_s, _song_length))

        if pos_s >= _song_length - 0.3:
            # pygame'in de durduğunu doğrula
            if pygame.mixer.music.get_pos() == -1 or pos_s >= _song_length:
                _is_playing = False
                btn_play.configure(text="▶", fg_color=BAR_TEXT, text_color=BAR_BG)
                seek_var.set(_song_length)
                time_left_lbl.configure(text=fmt_time(_song_length))
                time_right_lbl.configure(text="0:00")
                if _repeat_mode and _playlist:
                    _load_and_play(_playlist[_current_index])
                elif _playlist and _current_index < len(_playlist) - 1:
                    _change_song(+1)
        else:
            seek_var.set(pos_s)
            time_left_lbl.configure(text=fmt_time(pos_s))
            time_right_lbl.configure(text=fmt_time(max(0, _song_length - pos_s)))
    root.after(500, _tick)


root.after(500, _tick)
start_visualiser()


# ═════════════════════════════════════════════════════════════════════════════
#  LAYOUT: keep content above bars
# ═════════════════════════════════════════════════════════════════════════════
def _on_resize(event=None):
    if not root.winfo_exists():
        return
    h     = root.winfo_height()
    taken = PLAYER_BAR_H + VISUALISER_H
    # CTkFrame place() width/height kabul etmez, sadece rely/relheight kullanılır.
    # Content yüksekliğini dolaylı olarak ayarlıyoruz:
    # player_bar + vis_canvas zaten altta fixed, content relheight=1 ile başladı.
    # Sidebar her zaman üstte kalır.
    try:
        sidebar.lift()
    except Exception:
        pass
    if _vis_expanded:
        _place_vis_overlay()


def _place_vis_overlay():
    root.update_idletasks()
    h = root.winfo_height()
    w = root.winfo_width()
    overlay_h = h - PLAYER_BAR_H
    vis_overlay.place(x=SIDEBAR_W, y=0,
                      width=w - SIDEBAR_W,
                      height=overlay_h)
    vis_overlay.lift()
    # vis_big_canvas zaten relwidth/relheight ile yerleşiyor,
    # sadece y'yi güncelle (başlık yüksekliği sonrası)
    vis_big_canvas.place(x=0, y=88,
                         width=w - SIDEBAR_W,
                         height=max(1, overlay_h - 88))


def _toggle_visualiser():
    global _vis_expanded
    _vis_expanded = not _vis_expanded
    if _vis_expanded:
        _place_vis_overlay()
        btn_vis_expand.configure(text="⌄  Vis")
        # Şarkı bilgisini güncelle
        _update_vis_overlay_labels()
    else:
        vis_overlay.place_forget()
        btn_vis_expand.configure(text="⌃  Vis")


def _update_vis_overlay_labels():
    if not _vis_expanded:
        return
    artist, title = ("", "No song playing")
    if _current_filepath:
        artist, title = parse_filename(_current_filepath)
    vis_title_lbl.configure(text=title)
    vis_artist_lbl.configure(text=artist)


root.bind("<Configure>", _on_resize)


# ═════════════════════════════════════════════════════════════════════════════
#  PAGE FUNCTIONS
# ═════════════════════════════════════════════════════════════════════════════
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


def DownloadingMusicMenu():
    clear_content()
    section_title("Download a Song")
    body_text(
        "Enter a YouTube URL, the song name and the artist name below.\n"
        "The song will be downloaded as an MP3 into your Musics folder.\n"
        "Requires yt-dlp and ffmpeg to be installed on your system."
    )

    def _labeled_entry(label_text, placeholder):
        row = CTkFrame(content, fg_color=BackGroundColor, corner_radius=0)
        row.pack(anchor="w", padx=28, pady=(10, 0))
        CTkLabel(row, text=label_text, font=BodyFont,
                 text_color=BodyColor, fg_color=BackGroundColor,
                 width=100, anchor="w").pack(side="left", padx=(0, 10))
        entry = CTkEntry(row, width=380, placeholder_text=placeholder,
                         font=BodyFont, fg_color=EntryColor,
                         text_color=BodyColor, border_color=AccentColor)
        entry.pack(side="left")
        return entry

    url_entry    = _labeled_entry("YouTube URL:", "https://www.youtube.com/watch?v=…")
    name_entry   = _labeled_entry("Song name:  ", "e.g. Infinity Repeating")
    artist_entry = _labeled_entry("Artist:       ", "e.g. Disclosure")

    status_lbl = CTkLabel(content, text="", font=SmallFont,
                          text_color=SubHeaderColor, fg_color=BackGroundColor,
                          wraplength=680, justify="left")
    status_lbl.pack(anchor="w", padx=28, pady=(12, 0))

    progress_bar = CTkProgressBar(content, width=500,
                                  fg_color=EntryColor, progress_color=HeaderColor)

    def do_download():
        url    = url_entry.get().strip()
        name   = name_entry.get().strip()
        artist = artist_entry.get().strip()
        if not url:
            status_lbl.configure(text="⚠ Please enter a YouTube URL.")
            return
        if not name:
            status_lbl.configure(text="⚠ Please enter a song name.")
            return

        # Dosya adı: "Artist - Song name" ya da sadece "Song name"
        file_stem    = f"{artist} - {name}" if artist else name
        out_template = os.path.join(MUSICS_DIR, f"{file_stem}.%(ext)s")

        ytdlp = None
        for candidate in ("yt-dlp", "yt_dlp"):
            if subprocess.run(["which", candidate], capture_output=True).returncode == 0:
                ytdlp = candidate
                break
        if ytdlp is None:
            status_lbl.configure(
                text="✗ yt-dlp not found.\n"
                     "Install it with:  pip install yt-dlp\n"
                     "and make sure ffmpeg is also installed (brew install ffmpeg).")
            return

        cmd = [ytdlp, "--extract-audio", "--audio-format", "mp3",
               "--audio-quality", "0", "-o", out_template, url]

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
                    text=f"✓ Downloaded successfully as '{file_stem}.mp3'.")
            else:
                err  = result.stderr.strip().splitlines()
                last = err[-1] if err else "Unknown error."
                status_lbl.configure(text=f"✗ Download failed:\n{last}")
            download_btn.configure(state="normal")

        threading.Thread(target=run, daemon=True).start()

    download_btn = CTkButton(
        content, text="⬇  Download", command=do_download,
        font=SubHeaderFont, fg_color=HeaderColor,
        text_color="#FFFFFF", hover_color=SubHeaderColor,
        width=160, height=38, corner_radius=8)
    download_btn.pack(anchor="w", padx=28, pady=(14, 0))

    CTkLabel(
        content,
        text="Tip: install dependencies with  →  pip install yt-dlp  and  brew install ffmpeg",
        font=SmallFont, text_color=BodyColor, fg_color=BackGroundColor, anchor="w"
    ).pack(anchor="w", padx=28, pady=(18, 0))


def PlayingMusicMenu():
    clear_content()
    section_title("Play a Song")
    body_text("Write the song's name to search. Click the result to play.")

    entry_frame = CTkFrame(content, fg_color=BackGroundColor, corner_radius=0)
    entry_frame.pack(anchor="w", padx=28, pady=(4, 0))

    search_entry = CTkEntry(entry_frame, width=360,
                            placeholder_text="Song name…",
                            font=BodyFont, fg_color=EntryColor,
                            text_color=BodyColor, border_color=AccentColor)
    search_entry.pack(side="left", padx=(0, 10))

    status_lbl = CTkLabel(content, text="", font=SmallFont,
                          text_color=SubHeaderColor, fg_color=BackGroundColor)
    status_lbl.pack(anchor="w", padx=28, pady=(8, 0))

    result_frame = CTkFrame(content, fg_color=BackGroundColor, corner_radius=0)
    result_frame.pack(anchor="w", padx=28, pady=(6, 0))

    def _highlight_card(parent, filepath, query, on_play, width=420):
        """song_card gibi ama başlıkta eşleşen kısmı farklı renkle gösterir."""
        artist, title = parse_filename(filepath)

        card = CTkFrame(parent, fg_color=SideBarColor,
                        corner_radius=8, width=width, height=52)
        card.pack(anchor="w", pady=3)
        card.pack_propagate(False)

        play_btn = CTkButton(
            card, text="♪", width=36, height=52,
            font=("Arial", 16), fg_color=SideBarColor,
            text_color=SubHeaderColor, hover_color=ButtonColor,
            corner_radius=8, command=on_play
        )
        play_btn.pack(side="left")

        text_frame = CTkFrame(card, fg_color=SideBarColor, corner_radius=0)
        text_frame.pack(side="left", fill="both", expand=True, padx=(4, 8))

        # Başlıkta highlight: tk.Text ile normal + highlight segmentler
        title_canvas = tk.Text(
            text_frame, height=1, bg=SideBarColor,
            bd=0, relief="flat", highlightthickness=0,
            font=("Arial", 13, "bold"), cursor="arrow"
        )
        title_canvas.pack(anchor="w", fill="x")
        title_canvas.configure(state="normal")

        q_low   = query.lower()
        t_low   = title.lower()
        idx_hit = t_low.find(q_low)

        if idx_hit >= 0:
            before = title[:idx_hit]
            match  = title[idx_hit:idx_hit + len(query)]
            after  = title[idx_hit + len(query):]
            title_canvas.insert("end", before, "normal")
            title_canvas.insert("end", match,  "highlight")
            title_canvas.insert("end", after,  "normal")
            title_canvas.tag_config("normal",    foreground=SubHeaderColor)
            title_canvas.tag_config("highlight", foreground=HeaderColor,
                                    background=AccentColor)
        else:
            title_canvas.insert("end", title, "normal")
            title_canvas.tag_config("normal", foreground=SubHeaderColor)

        title_canvas.configure(state="disabled")

        if artist:
            CTkLabel(
                text_frame, text=artist,
                font=("Arial", 11, "italic"), text_color=BodyColor,
                fg_color=SideBarColor, anchor="w"
            ).pack(anchor="w", pady=(1, 0))

        for widget in (card, text_frame, title_canvas):
            widget.bind("<Button-1>", lambda e: on_play())

        return card

    def do_search():
        for w in result_frame.winfo_children():
            w.destroy()

        query     = search_entry.get().strip()
        all_files = get_audio_files()

        if not query:
            status_lbl.configure(text="⚠ Please enter a song name.")
            return

        matches = [
            (i, fp) for i, fp in enumerate(all_files)
            if query.lower() in os.path.splitext(os.path.basename(fp))[0].lower()
        ]

        if not matches:
            status_lbl.configure(text=f"✗ No song matching '{query}' found.")
            return

        status_lbl.configure(text=f"{len(matches)} result(s) — click to play:")

        def make_cmd(fp, idx):
            def cmd():
                play_file(fp, playlist=all_files, index=idx)
            return cmd

        for idx, fp in matches:
            _highlight_card(result_frame, fp, query, on_play=make_cmd(fp, idx))

    CTkButton(entry_frame, text="Search", command=do_search,
              font=BodyFont, fg_color=HeaderColor,
              text_color="#FFFFFF", hover_color=SubHeaderColor).pack(side="left")

    search_entry.bind("<Return>", lambda e: do_search())


def PlaylistMenu():
    clear_content()
    section_title("Playlists")
    body_text("Playlist management is coming in a future version of Freeply.\nStay tuned!")


def SongsMenu():
    clear_content()
    section_title("Your Songs")
    all_files = get_audio_files()
    if not all_files:
        body_text("No songs found. Use the Download page to add music,\n"
                  "or copy MP3/WAV files manually into the Musics folder.")
        return

    # Alfabetik sıralama: şarkı adına göre (sanatçı - şarkı → şarkı kısmına göre)
    def _sort_key(fp):
        _, title = parse_filename(fp)
        return title.lower()

    sorted_files = sorted(all_files, key=_sort_key)
    body_text(f"{len(sorted_files)} song(s)  —  click to play")

    scroll = CTkScrollableFrame(content, fg_color=BackGroundColor,
                                scrollbar_button_color=AccentColor)
    scroll.pack(fill="both", expand=True, padx=28, pady=(0, 4))

    def make_cmd(fp, idx):
        def cmd():
            play_file(fp, playlist=sorted_files, index=idx)
        return cmd

    for idx, fp in enumerate(sorted_files):
        song_card(scroll, fp, on_play=make_cmd(fp, idx))


def SettingsPage():
    set_path = os.path.join(BASE_DIR, "SetSettings.py")
    if os.path.exists(set_path):
        # Kendi PID'imizi argüman olarak geçir — SetSettings restart'ta kapatacak
        subprocess.Popen([sys.executable, set_path, str(os.getpid())])
    else:
        clear_content()
        section_title("Settings")
        body_text("SetSettings.py not found next to Freeply.py.")


def GitHubPage():
    webbrowser.open("https://github.com/feriduntahakurt0")


def GnuLicensePage():
    webbrowser.open("https://www.gnu.org/licenses/gpl-3.0.html")


def ContactPage():
    clear_content()
    section_title("Contact With Me")
    body_text("Have a question, a bug report, or just want to say hello?\nFeel free to reach out:")
    CTkLabel(content, text="📧  feriduntahakurt@gmail.com",
             font=SubHeaderFont, text_color=HeaderColor,
             fg_color=BackGroundColor, anchor="w"
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

for label, fn in _NAV_BUTTONS:
    CTkButton(
        sidebar, text=label, command=fn,
        font=SubHeaderFont, text_color=SubHeaderColor,
        fg_color=SideBarColor, hover_color=ButtonColor,
        anchor="w", height=40, corner_radius=8
    ).pack(fill="x", padx=emptyBetweenCorner, pady=3)


# ═════════════════════════════════════════════════════════════════════════════
#  LAUNCH
# ═════════════════════════════════════════════════════════════════════════════
MainMenu()
root.mainloop()
