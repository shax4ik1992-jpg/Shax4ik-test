"""Edit these to brand the video. Everything else is driven by timeline.py."""
W, H, FPS = 1080, 1920, 30

SERIES = "RAQAMLAR GAPIRADI"   # top-left HUD pill
EPISODE = 1
HANDLE = ""                     # e.g. "@kanal_nomi" -> shown under captions and on the end card
CHANNEL_NAME = ""               # e.g. "Kanal nomi" -> end card title; empty = generic card

# speaking pace used to auto-time captions until a real voice track is aligned
CHARS_PER_SEC = 16.0
GAP_LINE = 0.2
GAP_CHAPTER = 0.55
LEAD_IN = 0.5
