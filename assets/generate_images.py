#!/usr/bin/env python3
"""Generate either preview PNGs or update art.c with 1-bit glyph patterns.

Modes:
  previews: write 10 PNGs (pattern1..pattern10) for a glyph codepoint.
  art:      regenerate pattern1..pattern10 bitmaps and overwrite art.c with
            image descriptors (pattern1..pattern10 names).

Examples:
    ./generate_images.py --glyph 0xf005 --mode previews
    ./generate_images.py --glyph 0xf005 --mode art --art-file boards/shields/nice_view_glyphs/widgets/art.c

A nerd font is required, see https://www.nerdfonts.com
Tested with Caskaydia.
"""
import argparse
import os
import sys
from dataclasses import dataclass
from typing import List, Tuple
from PIL import Image, ImageDraw, ImageFont

LANDSCAPE_W, LANDSCAPE_H = 140, 68
PORTRAIT_W, PORTRAIT_H = 68, 140

SEARCH_DIRS = [
    # macOS
    "/Library/Fonts",
    os.path.expanduser("~/Library/Fonts"),
    "/System/Library/Fonts/Supplemental",
    # Linux
    "/usr/share/fonts",
    "/usr/local/share/fonts",
    os.path.expanduser("~/.local/share/fonts"),
    os.path.expanduser("~/.fonts"),
]
PREFERRED = ["Caskaydia", "Cascadia", "Nerd", "Code"]
FALLBACK_FONT_URL = (
    "https://github.com/ryanoasis/nerd-fonts/raw/refs/heads/master/"
    "patched-fonts/CascadiaCode/CaskaydiaCoveNerdFontMono-Regular.ttf"
)


@dataclass
class GlyphPattern:
    name: str
    placements: List[Tuple[int, int, int]]  # (cx, cy, size)


PATTERNS = [
    GlyphPattern("pattern1", [(70, 34, 60)]),
    GlyphPattern("pattern2", [(70, 34, 48), (30, 15, 28), (110, 50, 20)]),
    GlyphPattern("pattern3", [(55, 30, 42), (35, 18, 28), (78, 42, 32), (48, 50, 20)]),
    GlyphPattern(
        "pattern4",
        [
            (50, 28, 50), (28, 16, 32), (88, 44, 40), (42, 54, 26),
            (70, 18, 28), (108, 34, 30),
        ],
    ),
    GlyphPattern("pattern5", [(30, 34, 18), (60, 34, 26), (90, 34, 34), (120, 34, 42)]),
    GlyphPattern(
        "pattern6",
        [
            (15, 50, 20), (25, 18, 24), (60, 12, 30), (85, 48, 26),
            (105, 20, 24), (125, 40, 18),
        ],
    ),
    GlyphPattern(
        "pattern7",
        [
            (70, 34, 28),  # center
            (70, 12, 16), (95, 20, 16), (105, 44, 16), (70, 56, 16),
            (45, 48, 16), (35, 24, 16),
        ],
    ),
    GlyphPattern(
        "pattern8",
        [
            (70, 34, 22),  # center
            (20, 10, 16), (120, 10, 16), (20, 58, 16), (120, 58, 16),  # corners
            (35, 25, 14), (105, 25, 14), (35, 43, 14), (105, 43, 14),  # inner diagonals
        ],
    ),
    GlyphPattern(
        "pattern9",
        [
            (10, 34, 16), (25, 22, 18), (40, 14, 20), (55, 22, 22),
            (70, 34, 24), (85, 46, 22), (100, 54, 20), (115, 46, 18),
            (130, 34, 16),
        ],
    ),
    GlyphPattern(
        "pattern10",
        [
            (20, 20, 18), (50, 15, 22), (80, 12, 16), (110, 18, 20),
            (30, 40, 14), (60, 38, 26), (90, 42, 18), (120, 36, 22),
            (40, 57, 16), (75, 54, 20), (105, 52, 16),
        ],
    ),
]


def load_font():
    candidates = []
    for d in SEARCH_DIRS:
        if not os.path.isdir(d):
            continue
        for fname in os.listdir(d):
            low = fname.lower()
            if low.endswith(".ttf") and any(p.lower() in low for p in PREFERRED):
                candidates.append(os.path.join(d, fname))

    def score(p):
        name = os.path.basename(p).lower()
        return (
            ("nerd" in name)
            + ("caskaydia" in name)
            + ("cascadia" in name)
            + ("code" in name),
            -len(name),
        )

    candidates.sort(key=score, reverse=True)
    for path in candidates:
        try:
            f = ImageFont.truetype(path, 24)
            f.path = path
            return f
        except Exception:
            pass
    # Fallback download attempt
    fonts_dir = os.path.join(os.path.dirname(__file__), "fonts")
    os.makedirs(fonts_dir, exist_ok=True)
    fallback_path = os.path.join(fonts_dir, "CaskaydiaCoveNerdFontMono-Regular.ttf")
    if not os.path.isfile(fallback_path):
        try:
            import urllib.request

            print(
                f"No suitable font found. Downloading fallback Nerd Font from {FALLBACK_FONT_URL} ..."
            )
            urllib.request.urlretrieve(FALLBACK_FONT_URL, fallback_path)
            print("Fallback font downloaded.")
        except Exception as e:
            print(f"Failed to download fallback font: {e}", file=sys.stderr)
            return None
    try:
        f = ImageFont.truetype(fallback_path, 24)
        f.path = fallback_path
        print(f"Using downloaded fallback font: {fallback_path}")
        return f
    except Exception as e:
        print(f"Failed to load fallback font ({fallback_path}): {e}", file=sys.stderr)
        return None


def parse_codepoint(code: str) -> str:
    """Return the Unicode character for a hex codepoint string.

    Enforces strict hex-only format. Accepts optional 0x prefix. Aborts on failure.
    """
    raw = code.strip().lower()
    if raw.startswith("0x"):
        raw = raw[2:]
    if not raw or any(c not in "0123456789abcdef" for c in raw):
        print(f"Invalid hex glyph '{code}'", file=sys.stderr)
        sys.exit(2)
    try:
        return chr(int(raw, 16))
    except Exception as e:
        print(f"Failed to parse glyph '{code}': {e}", file=sys.stderr)
        sys.exit(2)


def draw_glyph(
    draw: ImageDraw.ImageDraw, glyph: str, cx: int, cy: int, size: int, font_obj
):
    font_size = max(8, int(size * 1.2))
    font = ImageFont.truetype(font_obj.path, font_size)
    w, h = draw.textbbox((0, 0), glyph, font=font)[2:]
    draw.text((cx - w // 2, cy - h // 2), glyph, font=font, fill="white")


def make_pattern_image(
    glyph: str, pattern: GlyphPattern, font_obj, orientation: str = "portrait"
) -> Image.Image:
    """Render a pattern image in the requested logical orientation.

    portrait: start with 68x140 canvas; pattern placements defined originally for landscape
              are mapped into portrait space so a later CW rotation produces the intended layout.
    landscape: direct 140x68 rendering.
    """
    if orientation not in ("portrait", "landscape"):
        raise ValueError("orientation must be portrait or landscape")
    base_w, base_h = (
        (PORTRAIT_W, PORTRAIT_H)
        if orientation == "portrait"
        else (LANDSCAPE_W, LANDSCAPE_H)
    )
    img = Image.new("RGB", (base_w, base_h), "black")
    # Transform coordinates if portrait (treat original placements as landscape coords)
    if orientation == "portrait":
        placements = []
        for cx, cy, size in pattern.placements:
            xp = cy  # map landscape y -> portrait x
            yp = PORTRAIT_H - 1 - cx  # invert landscape x into portrait y
            placements.append((xp, yp, size))
    else:
        placements = pattern.placements
    for cx, cy, size in placements:
        # Improved glyph rendering: use metrics, pad, crop.
        font_size = max(8, int(size * 1.2))
        font = ImageFont.truetype(font_obj.path, font_size)
        ascent, descent = font.getmetrics()
        tmp_w = int(font.getlength(glyph) + 4)
        tmp_h = int(ascent + descent + 8)
        glyph_canvas = Image.new("L", (max(8, tmp_w), max(8, tmp_h)), 0)
        gd = ImageDraw.Draw(glyph_canvas)
        gd.text((2, 2), glyph, font=font, fill=255)
        bbox = glyph_canvas.getbbox()
        if bbox:
            glyph_canvas = glyph_canvas.crop(bbox)
        gw, gh = glyph_canvas.size
        if gw > base_w or gh > base_h:
            scale = min(base_w / max(gw, 1), base_h / max(gh, 1)) * 0.95
            new_font_size = max(8, int(font_size * scale))
            font = ImageFont.truetype(font_obj.path, new_font_size)
            ascent, descent = font.getmetrics()
            tmp_w = int(font.getlength(glyph) + 4)
            tmp_h = int(ascent + descent + 8)
            glyph_canvas = Image.new("L", (max(8, tmp_w), max(8, tmp_h)), 0)
            gd = ImageDraw.Draw(glyph_canvas)
            gd.text((2, 2), glyph, font=font, fill=255)
            bbox = glyph_canvas.getbbox()
            if bbox:
                glyph_canvas = glyph_canvas.crop(bbox)
            gw, gh = glyph_canvas.size
        half_w, half_h = gw // 2, gh // 2
        cx = max(half_w, min(base_w - half_w - 1, cx))
        cy = max(half_h, min(base_h - half_h - 1, cy))
        white_rgb = Image.new("RGB", (gw, gh), "white")
        px = int(cx - gw // 2)
        py = int(cy - gh // 2)
        img.paste(white_rgb, (px, py), glyph_canvas)
    return img


def image_to_indexed_1bit_bytes(img: Image.Image, width: int, height: int) -> bytes:
    mono = img.convert("L")
    bits = []
    for y in range(height):
        byte = 0
        bit_count = 0
        for x in range(width):
            pix = mono.getpixel((x, y))
            # getpixel for "L" mode returns int 0..255; guard against unexpected types
            val = pix if isinstance(pix, int) else 0
            bit = 1 if val > 0 else 0
            byte = (byte << 1) | bit
            bit_count += 1
            if bit_count == 8:
                bits.append(byte)
                byte = 0
                bit_count = 0
        if bit_count:
            byte <<= 8 - bit_count
            bits.append(byte)
    return bytes(bits)


def write_entire_art_file(art_file: str, glyph: str, font_obj, orientation: str):
    """Overwrite art_file with a complete generated set of pattern images.

    This replaces any previous content; only the generated patterns and a header remain.
    """
    lines = []
    lines.append(
        "/*\n"
        " * Clean generated pattern assets (pattern1..pattern10)\n"
        " * Auto-generated by generate_images.py --mode art\n"
        " * Do not edit; regenerate instead.\n"
        " */\n\n"
    )
    lines.append("#include <lvgl.h>\n\n")
    lines.append(
        "#ifndef LV_ATTRIBUTE_MEM_ALIGN\n#define LV_ATTRIBUTE_MEM_ALIGN\n#endif\n\n"
    )
    lines.append("/* BEGIN AUTO-GENERATED PATTERN IMAGES (do not edit manually) */\n")
    for pattern in PATTERNS:
        img = make_pattern_image(glyph, pattern, font_obj, orientation=orientation)
        if orientation == "portrait":
            # Rotate portrait canvas clockwise 90° so storage matches original landscape descriptor
            img = img.rotate(270, expand=True)  # CCW 270 == CW 90
        width, height = LANDSCAPE_W, LANDSCAPE_H
        if img.size != (LANDSCAPE_W, LANDSCAPE_H):
            img = img.resize((LANDSCAPE_W, LANDSCAPE_H))
        row_bytes = (width + 7) // 8
        data = image_to_indexed_1bit_bytes(img, width, height)
        lines.append(
            f"#ifndef LV_ATTRIBUTE_IMG_{pattern.name.upper()}\n"
            f"#define LV_ATTRIBUTE_IMG_{pattern.name.upper()}\n"
            "#endif\n"
        )
        lines.append(
            f"const LV_ATTRIBUTE_MEM_ALIGN LV_ATTRIBUTE_LARGE_CONST "
            f"LV_ATTRIBUTE_IMG_{pattern.name.upper()} uint8_t {pattern.name}_map[] = {{\n"
        )
        lines.append(
            "#if CONFIG_NICE_VIEW_WIDGET_INVERTED\n"
            "    0x00,0x00,0x00,0xff, /*Color of index 0*/\n"
            "    0xff,0xff,0xff,0xff, /*Color of index 1*/\n"
            "#else\n"
            "    0xff,0xff,0xff,0xff, /*Color of index 0*/\n"
            "    0x00,0x00,0x00,0xff, /*Color of index 1*/\n"
            "#endif\n"
        )
        for y in range(height):
            offset = y * row_bytes
            row = data[offset : offset + row_bytes]
            hexes = ",".join(f"0x{b:02x}" for b in row)
            lines.append(f"    /* y{y:02d} */ {hexes},\n")
        lines.append("};\n\n")
        lines.append(
            f"const lv_img_dsc_t {pattern.name} = {{\n"
            "  .header.cf = LV_IMG_CF_INDEXED_1BIT,\n"
            "  .header.always_zero = 0,\n"
            "  .header.reserved = 0,\n"
            f"  .header.w = {width},\n"
            f"  .header.h = {height},\n"
            f"  .data_size = {row_bytes * height},\n"
            f"  .data = {pattern.name}_map,\n"
            "};\n\n"
        )
    lines.append("/* END AUTO-GENERATED PATTERN IMAGES */\n")
    with open(art_file, "w") as wf:
        wf.write("".join(lines))


def run():
    parser = argparse.ArgumentParser(
        description="Generate preview PNGs or overwrite art.c with glyph pattern images"
    )
    parser.add_argument(
        "--glyph",
        required=True,
        help="Hex codepoint like 0xf005 (mandatory now; no build-time config)",
    )
    parser.add_argument("--mode", choices=["previews", "art"], default="previews")
    parser.add_argument(
        "--orientation",
        choices=["portrait", "landscape"],
        default="portrait",
        help="Logical design orientation (portrait 68x140 rotated to landscape for art).",
    )
    parser.add_argument(
        "--art-file",
        default="boards/shields/nice_view_glyphs/widgets/art.c",
        help="Path to art.c for --mode art",
    )
    args = parser.parse_args()
    font_obj = load_font()
    if not font_obj:
        print("Required Nerd/Caskaydia/Cascadia font not found. Install and retry.")
        sys.exit(1)

    effective_glyph = args.glyph.strip().lower()
    glyph_char = parse_codepoint(effective_glyph)

    if args.mode == "previews":
        # Save into workspace root previews/ directory, filenames <glyph>_<pattern>.png
        workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        out_dir = os.path.join(workspace_root, "previews")
        os.makedirs(out_dir, exist_ok=True)
        hex_code = effective_glyph.lower().lstrip("0x")
        for pattern in PATTERNS:
            img = make_pattern_image(
                glyph_char, pattern, font_obj, orientation=args.orientation
            )
            path = os.path.join(out_dir, f"{hex_code}_{pattern.name}.png")
            img.save(path)
            print("saved", path)
    else:
        write_entire_art_file(
            os.path.abspath(args.art_file),
            glyph_char,
            font_obj,
            orientation=args.orientation,
        )
        print(
            f"Wrote complete art file to {args.art_file} (orientation={args.orientation})"
        )


if __name__ == "__main__":
    run()
