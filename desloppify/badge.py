"""Scorecard badge image generator — produces a visual health summary PNG."""

from __future__ import annotations

import os
from pathlib import Path

from .utils import PROJECT_ROOT

# Render at 2x for retina/high-DPI crispness
_SCALE = 2


def _score_color(score: float) -> tuple[int, int, int]:
    """Color-code a score with warm tones: sage >= 90, mustard 70-90, dusty rose < 70."""
    if score >= 90:
        return (110, 153, 112)   # sage green
    if score >= 70:
        return (196, 164, 90)    # mustard
    return (185, 110, 110)       # dusty rose


def _load_font(size: int, *, serif: bool = False, bold: bool = False, mono: bool = False):
    """Load a font with cross-platform fallback."""
    from PIL import ImageFont

    size = size * _SCALE
    candidates = []
    if mono:
        candidates = [
            "/System/Library/Fonts/SFNSMono.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
        ]
    elif serif and bold:
        candidates = [
            "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
            "/System/Library/Fonts/NewYork.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
        ]
    elif serif:
        candidates = [
            "/System/Library/Fonts/Supplemental/Georgia.ttf",
            "/System/Library/Fonts/NewYork.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
        ]
    elif bold:
        candidates = [
            "/System/Library/Fonts/SFCompact.ttf",
            "/System/Library/Fonts/HelveticaNeue.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
    else:
        candidates = [
            "/System/Library/Fonts/SFCompact.ttf",
            "/System/Library/Fonts/HelveticaNeue.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def _s(v: int | float) -> int:
    """Scale a layout value."""
    return int(v * _SCALE)


def generate_scorecard(state: dict, output_path: str | Path) -> Path:
    """Render a scorecard PNG from scan state. Returns the output path."""
    from PIL import Image, ImageDraw

    output_path = Path(output_path)
    dim_scores = state.get("dimension_scores", {})
    obj_score = state.get("objective_score")
    obj_strict = state.get("objective_strict")

    main_score = obj_score if obj_score is not None else state.get("score", 0)
    strict_score = obj_strict if obj_strict is not None else state.get("strict_score", 0)

    # Fonts — serif for headings, mono for data
    font_title = _load_font(19, serif=True, bold=True)
    font_big = _load_font(52, serif=True, bold=True)
    font_strict = _load_font(18, serif=True)
    font_label = _load_font(11, serif=True)
    font_header = _load_font(11, mono=True)
    font_row = _load_font(12, mono=True)
    font_tiny = _load_font(9, serif=True)

    # Wes Anderson palette — warm cream with muted accents
    BG = (248, 241, 229)           # warm cream
    BG_TABLE = (241, 233, 219)     # slightly darker cream for table
    TEXT = (62, 52, 42)            # warm dark brown
    DIM = (148, 132, 112)         # warm muted brown
    BORDER = (198, 182, 158)      # warm tan border
    ACCENT = (156, 120, 96)       # warm brown accent
    SCORE_GREEN = (110, 153, 112) # sage green
    FRAME = (178, 158, 132)       # frame color

    # Layout
    active_dims = [(name, data) for name, data in dim_scores.items()
                   if data.get("checks", 0) > 0]
    row_count = len(active_dims)
    W = _s(440)
    pad = _s(24)
    frame_w = _s(2)
    table_top = _s(146)
    row_h = _s(24)
    table_h = _s(26) + row_count * row_h + _s(12)
    H = table_top + table_h + _s(36)

    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # --- Outer frame (Wes Anderson loves deliberate borders) ---
    draw.rectangle((0, 0, W - 1, H - 1), outline=FRAME, width=_s(2))
    # Inner frame with slight inset
    inset = _s(6)
    draw.rectangle((inset, inset, W - 1 - inset, H - 1 - inset), outline=BORDER, width=1)

    # --- Decorative rule under title area ---
    rule_y = _s(44)
    rule_margin = _s(60)
    draw.rectangle((rule_margin, rule_y, W - rule_margin, rule_y), fill=BORDER)
    # Small diamond in center of rule
    diamond_cx = W // 2
    diamond_s = _s(3)
    draw.polygon([
        (diamond_cx, rule_y - diamond_s),
        (diamond_cx + diamond_s, rule_y),
        (diamond_cx, rule_y + diamond_s),
        (diamond_cx - diamond_s, rule_y),
    ], fill=ACCENT)

    # --- Title ---
    title = "Desloppify Score"
    tw = draw.textlength(title, font=font_title)
    draw.text(((W - tw) / 2, _s(18)), title, fill=TEXT, font=font_title)

    # --- Main score ---
    score_str = f"{main_score:.1f}"
    score_color = _score_color(main_score)
    sw = draw.textlength(score_str, font=font_big)

    strict_str = f"strict: {strict_score:.1f}"
    strict_w = draw.textlength(strict_str, font=font_strict)

    # Center the pair
    gap = _s(12)
    total_w = sw + gap + strict_w
    x_start = (W - total_w) / 2
    score_y = _s(54)
    draw.text((x_start, score_y), score_str, fill=score_color, font=font_big)
    strict_y = score_y + _s(22)
    draw.text((x_start + sw + gap, strict_y), strict_str, fill=DIM, font=font_strict)

    # --- Decorative rule above table ---
    rule2_y = table_top - _s(14)
    draw.rectangle((rule_margin, rule2_y, W - rule_margin, rule2_y), fill=BORDER)

    # --- Table area ---
    table_x1 = pad + _s(4)
    table_x2 = W - pad - _s(4)
    draw.rounded_rectangle(
        (table_x1, table_top - _s(2), table_x2, table_top + table_h),
        radius=_s(4), fill=BG_TABLE, outline=BORDER, width=1)

    # --- Table header ---
    col_name = table_x1 + _s(14)
    col_health = _s(280)
    col_strict = _s(366)
    header_y = table_top + _s(4)
    draw.text((col_name, header_y), "Dimension", fill=DIM, font=font_header)
    draw.text((col_health, header_y), "Health", fill=DIM, font=font_header)
    draw.text((col_strict, header_y), "Strict", fill=DIM, font=font_header)

    # Header underline
    line_y = header_y + _s(16)
    draw.rectangle((col_name, line_y, table_x2 - _s(14), line_y), fill=BORDER)

    # --- Dimension rows ---
    y = line_y + _s(6)
    for name, data in active_dims:
        score = data.get("score", 100)
        strict = data.get("strict", score)
        sc = _score_color(score)
        stc = _score_color(strict)
        draw.text((col_name, y), name, fill=TEXT, font=font_row)
        draw.text((col_health, y), f"{score:.1f}%", fill=sc, font=font_row)
        draw.text((col_strict, y), f"{strict:.1f}%", fill=stc, font=font_row)
        y += row_h

    # --- Footer ---
    footer_y = H - _s(22)
    footer = "github.com/peteromallet/desloppify"
    fw = draw.textlength(footer, font=font_tiny)
    draw.text(((W - fw) / 2, footer_y), footer, fill=DIM, font=font_tiny)

    img.save(str(output_path), "PNG", optimize=True)
    return output_path


def get_badge_config(args) -> tuple[Path | None, bool]:
    """Resolve badge output path and whether badge generation is disabled.

    Returns (output_path, disabled). Checks CLI args, then env vars.
    """
    disabled = getattr(args, "no_badge", False) or os.environ.get("DESLOPPIFY_NO_BADGE", "").lower() in ("1", "true", "yes")
    if disabled:
        return None, True
    path_str = getattr(args, "badge_path", None) or os.environ.get("DESLOPPIFY_BADGE_PATH", "scorecard.png")
    path = Path(path_str)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path, False
