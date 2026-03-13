# ============================================================
#  Freeply 1.0.0 — Settings File
# ============================================================
# Do manual changes if only you know what you are doing!

# Defaults
windowSize = "1100x680"
version    = "1.0.0"
emptyBetweenCorner = 15
emptyBetweenTexts  = 8

# Fonts
HeaderFont    = ("Arial", 22, "bold")
SubHeaderFont = ("Arial", 15, "bold")
BodyFont      = ("Arial", 13)
SmallFont     = ("Arial", 11)

# ============================================================
#  Themes
# ============================================================

# ── Grape ────────────────────────────────────────────────────
GrapeTheme_BackGroundColor  = "#F5EEF8"
GrapeTheme_SideBarColor     = "#EAD7F2"
GrapeTheme_HeaderColor      = "#6A0572"
GrapeTheme_SubHeaderColor   = "#8E44AD"
GrapeTheme_ButtonColor      = "#D7BDE2"
GrapeTheme_EntryColor       = "#F2E6FA"
GrapeTheme_BodyColor        = "#5D3472"
GrapeTheme_AccentColor      = "#C39BD3"

# ── Midnight ─────────────────────────────────────────────────
MidnightTheme_BackGroundColor  = "#0D0D1A"
MidnightTheme_SideBarColor     = "#12122B"
MidnightTheme_HeaderColor      = "#7EB8FF"
MidnightTheme_SubHeaderColor   = "#A0CFFF"
MidnightTheme_ButtonColor      = "#1E2040"
MidnightTheme_EntryColor       = "#1A1A35"
MidnightTheme_BodyColor        = "#C8D8F0"
MidnightTheme_AccentColor      = "#3A4080"

# ── Forest ───────────────────────────────────────────────────
ForestTheme_BackGroundColor  = "#F0F7F0"
ForestTheme_SideBarColor     = "#D8EDD8"
ForestTheme_HeaderColor      = "#1B4D2E"
ForestTheme_SubHeaderColor   = "#2E7D50"
ForestTheme_ButtonColor      = "#A8D5A2"
ForestTheme_EntryColor       = "#E8F5E8"
ForestTheme_BodyColor        = "#2C5F3A"
ForestTheme_AccentColor      = "#5CB87A"

# ── Sunset ───────────────────────────────────────────────────
SunsetTheme_BackGroundColor  = "#FFF4EC"
SunsetTheme_SideBarColor     = "#FFE0C8"
SunsetTheme_HeaderColor      = "#C0392B"
SunsetTheme_SubHeaderColor   = "#E67E22"
SunsetTheme_ButtonColor      = "#F5CBA7"
SunsetTheme_EntryColor       = "#FEF0E7"
SunsetTheme_BodyColor        = "#A04000"
SunsetTheme_AccentColor      = "#F0A070"

# ── Arctic ───────────────────────────────────────────────────
ArcticTheme_BackGroundColor  = "#EAF4FB"
ArcticTheme_SideBarColor     = "#D6EAF8"
ArcticTheme_HeaderColor      = "#1A5276"
ArcticTheme_SubHeaderColor   = "#2980B9"
ArcticTheme_ButtonColor      = "#AED6F1"
ArcticTheme_EntryColor       = "#EBF5FB"
ArcticTheme_BodyColor        = "#154360"
ArcticTheme_AccentColor      = "#85C1E9"

# ── Rose ─────────────────────────────────────────────────────
RoseTheme_BackGroundColor  = "#FFF0F3"
RoseTheme_SideBarColor     = "#FFD6DE"
RoseTheme_HeaderColor      = "#880E2F"
RoseTheme_SubHeaderColor   = "#C0395A"
RoseTheme_ButtonColor      = "#F5A8BB"
RoseTheme_EntryColor       = "#FFECF0"
RoseTheme_BodyColor        = "#7B1535"
RoseTheme_AccentColor      = "#F08098"

# ── Charcoal ─────────────────────────────────────────────────
CharcoalTheme_BackGroundColor  = "#2B2B2B"
CharcoalTheme_SideBarColor     = "#1F1F1F"
CharcoalTheme_HeaderColor      = "#E0E0E0"
CharcoalTheme_SubHeaderColor   = "#BDBDBD"
CharcoalTheme_ButtonColor      = "#3D3D3D"
CharcoalTheme_EntryColor       = "#333333"
CharcoalTheme_BodyColor        = "#9E9E9E"
CharcoalTheme_AccentColor      = "#555555"

# ── Gold ─────────────────────────────────────────────────────
GoldTheme_BackGroundColor  = "#FFFBF0"
GoldTheme_SideBarColor     = "#FFF2C8"
GoldTheme_HeaderColor      = "#7D5A00"
GoldTheme_SubHeaderColor   = "#B8860B"
GoldTheme_ButtonColor      = "#FFE08A"
GoldTheme_EntryColor       = "#FFFAEB"
GoldTheme_BodyColor        = "#5C4000"
GoldTheme_AccentColor      = "#D4A017"

# ============================================================
#  Active Theme Selection
# ============================================================

# Change this value to switch themes:
# "Grape" | "Midnight" | "Forest" | "Sunset" | "Arctic" | "Rose" | "Charcoal" | "Gold"
Theme = "Rose"

BackGroundColor = ""
SideBarColor    = ""
HeaderColor     = ""
SubHeaderColor  = ""
ButtonColor     = ""
EntryColor      = ""
BodyColor       = ""
AccentColor     = ""

# ── Theme Settings ───────────────────────────────────────────

if Theme == "Grape":
    BackGroundColor = GrapeTheme_BackGroundColor
    SideBarColor    = GrapeTheme_SideBarColor
    HeaderColor     = GrapeTheme_HeaderColor
    SubHeaderColor  = GrapeTheme_SubHeaderColor
    ButtonColor     = GrapeTheme_ButtonColor
    EntryColor      = GrapeTheme_EntryColor
    BodyColor       = GrapeTheme_BodyColor
    AccentColor     = GrapeTheme_AccentColor

elif Theme == "Midnight":
    BackGroundColor = MidnightTheme_BackGroundColor
    SideBarColor    = MidnightTheme_SideBarColor
    HeaderColor     = MidnightTheme_HeaderColor
    SubHeaderColor  = MidnightTheme_SubHeaderColor
    ButtonColor     = MidnightTheme_ButtonColor
    EntryColor      = MidnightTheme_EntryColor
    BodyColor       = MidnightTheme_BodyColor
    AccentColor     = MidnightTheme_AccentColor

elif Theme == "Forest":
    BackGroundColor = ForestTheme_BackGroundColor
    SideBarColor    = ForestTheme_SideBarColor
    HeaderColor     = ForestTheme_HeaderColor
    SubHeaderColor  = ForestTheme_SubHeaderColor
    ButtonColor     = ForestTheme_ButtonColor
    EntryColor      = ForestTheme_EntryColor
    BodyColor       = ForestTheme_BodyColor
    AccentColor     = ForestTheme_AccentColor

elif Theme == "Sunset":
    BackGroundColor = SunsetTheme_BackGroundColor
    SideBarColor    = SunsetTheme_SideBarColor
    HeaderColor     = SunsetTheme_HeaderColor
    SubHeaderColor  = SunsetTheme_SubHeaderColor
    ButtonColor     = SunsetTheme_ButtonColor
    EntryColor      = SunsetTheme_EntryColor
    BodyColor       = SunsetTheme_BodyColor
    AccentColor     = SunsetTheme_AccentColor

elif Theme == "Arctic":
    BackGroundColor = ArcticTheme_BackGroundColor
    SideBarColor    = ArcticTheme_SideBarColor
    HeaderColor     = ArcticTheme_HeaderColor
    SubHeaderColor  = ArcticTheme_SubHeaderColor
    ButtonColor     = ArcticTheme_ButtonColor
    EntryColor      = ArcticTheme_EntryColor
    BodyColor       = ArcticTheme_BodyColor
    AccentColor     = ArcticTheme_AccentColor

elif Theme == "Rose":
    BackGroundColor = RoseTheme_BackGroundColor
    SideBarColor    = RoseTheme_SideBarColor
    HeaderColor     = RoseTheme_HeaderColor
    SubHeaderColor  = RoseTheme_SubHeaderColor
    ButtonColor     = RoseTheme_ButtonColor
    EntryColor      = RoseTheme_EntryColor
    BodyColor       = RoseTheme_BodyColor
    AccentColor     = RoseTheme_AccentColor

elif Theme == "Charcoal":
    BackGroundColor = CharcoalTheme_BackGroundColor
    SideBarColor    = CharcoalTheme_SideBarColor
    HeaderColor     = CharcoalTheme_HeaderColor
    SubHeaderColor  = CharcoalTheme_SubHeaderColor
    ButtonColor     = CharcoalTheme_ButtonColor
    EntryColor      = CharcoalTheme_EntryColor
    BodyColor       = CharcoalTheme_BodyColor
    AccentColor     = CharcoalTheme_AccentColor

elif Theme == "Gold":
    BackGroundColor = GoldTheme_BackGroundColor
    SideBarColor    = GoldTheme_SideBarColor
    HeaderColor     = GoldTheme_HeaderColor
    SubHeaderColor  = GoldTheme_SubHeaderColor
    ButtonColor     = GoldTheme_ButtonColor
    EntryColor      = GoldTheme_EntryColor
    BodyColor       = GoldTheme_BodyColor
    AccentColor     = GoldTheme_AccentColor
