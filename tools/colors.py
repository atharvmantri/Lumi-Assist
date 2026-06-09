"""Color tools — hex, rgb, hsl conversion and palette generation."""
from __future__ import annotations

import colorsys
import random

from tools import tool


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02x}{g:02x}{b:02x}"


def _rgb_to_hsl(r: int, g: int, b: int) -> tuple[int, int, int]:
    r_norm, g_norm, b_norm = r / 255.0, g / 255.0, b / 255.0
    h, l, s = colorsys.rgb_to_hls(r_norm, g_norm, b_norm)
    return int(h * 360), int(s * 100), int(l * 100)


def _hsl_to_rgb(h: int, s: int, l: int) -> tuple[int, int, int]:
    h_norm, s_norm, l_norm = h / 360.0, s / 100.0, l / 100.0
    r, g, b = colorsys.hls_to_rgb(h_norm, l_norm, s_norm)
    return int(r * 255), int(g * 255), int(b * 255)


@tool(
    name="color_convert",
    description="Convert between color formats: hex, rgb, hsl.",
    parameters={
        "type": "object",
        "properties": {
            "color": {
                "type": "string",
                "description": "Color in hex (#FF5733), rgb (255,87,51), or hsl (14,87,60) format",
            },
            "format": {
                "type": "string",
                "description": "Target format: 'hex', 'rgb', 'hsl'",
                "enum": ["hex", "rgb", "hsl"],
            },
        },
        "required": ["color"],
    },
)
def color_convert(color: str, format: str = "") -> str:
    color = color.strip()

    # Detect input format
    if color.startswith("#"):
        r, g, b = _hex_to_rgb(color)
        input_fmt = "HEX"
    elif color.startswith("rgb"):
        parts = color.replace("rgb(", "").replace(")", "").split(",")
        r, g, b = int(parts[0]), int(parts[1]), int(parts[2])
        input_fmt = "RGB"
    elif color.startswith("hsl"):
        parts = color.replace("hsl(", "").replace(")", "").split(",")
        h, s, l = int(parts[0]), int(parts[1]), int(parts[2])
        r, g, b = _hsl_to_rgb(h, s, l)
        input_fmt = "HSL"
    else:
        return f"error: unrecognized color format. Use #hex, rgb(r,g,b), or hsl(h,s,l)."

    # Compute all formats
    hex_val = _rgb_to_hex(r, g, b)
    h, s, l = _rgb_to_hsl(r, g, b)
    hsl_val = f"hsl({h}, {s}%, {l}%)"
    rgb_val = f"rgb({r}, {g}, {b})"

    if format == "hex":
        return f"{color} ({input_fmt}) → {hex_val}"
    elif format == "rgb":
        return f"{color} ({input_fmt}) → {rgb_val}"
    elif format == "hsl":
        return f"{color} ({input_fmt}) → {hsl_val}"
    else:
        return f"Color conversions:\n  HEX: {hex_val}\n  RGB: {rgb_val}\n  HSL: {hsl_val}"


@tool(
    name="generate_palette",
    description="Generate a color palette (set of harmonious colors) for design work.",
    parameters={
        "type": "object",
        "properties": {
            "style": {
                "type": "string",
                "description": "Palette style: 'complementary', 'triadic', 'pastel', 'vibrant', 'monochrome' (default 'vibrant')",
                "enum": ["complementary", "triadic", "pastel", "vibrant", "monochrome"],
            },
            "count": {
                "type": "integer",
                "description": "Number of colors (default 5)",
            },
        },
        "required": [],
    },
)
def generate_palette(style: str = "vibrant", count: int = 5) -> str:
    count = max(2, min(count, 10))
    base_h = random.randint(0, 360)

    if style == "complementary":
        colors = [(base_h, 70, 50), ((base_h + 180) % 360, 70, 50)]
        # Add lighter/darker variants
        for _ in range(count - 2):
            colors.append((base_h, random.randint(40, 80), random.randint(30, 70)))
    elif style == "triadic":
        colors = [
            (base_h, 65, 50),
            ((base_h + 120) % 360, 65, 50),
            ((base_h + 240) % 360, 65, 50),
        ]
        for _ in range(count - 3):
            colors.append((random.randint(0, 360), 65, random.randint(30, 70)))
    elif style == "pastel":
        colors = [(random.randint(0, 360), 50, 80) for _ in range(count)]
    elif style == "vibrant":
        colors = [(random.randint(0, 360), 80, 55) for _ in range(count)]
    elif style == "monochrome":
        colors = [(base_h, 20, l) for l in range(15, 90, max(1, 75 // count))]
    else:
        colors = [(random.randint(0, 360), 70, 50) for _ in range(count)]

    lines = [f"Color Palette ({style}, {count} colors):"]
    for h, s, l in colors[:count]:
        r, g, b = _hsl_to_rgb(h, s, l)
        hex_val = _rgb_to_hex(r, g, b)
        lines.append(f"  {hex_val}  rgb({r}, {g}, {b})  hsl({h}, {s}%, {l}%)")

    return "\n".join(lines)


@tool(
    name="color_contrast",
    description="Check if two colors have sufficient contrast for accessibility (WCAG AA).",
    parameters={
        "type": "object",
        "properties": {
            "color1": {
                "type": "string",
                "description": "First color in hex (e.g. '#FFFFFF')",
            },
            "color2": {
                "type": "string",
                "description": "Second color in hex (e.g. '#000000')",
            },
        },
        "required": ["color1", "color2"],
    },
)
def color_contrast(color1: str, color2: str) -> str:
    def relative_luminance(hex_color: str) -> float:
        r, g, b = _hex_to_rgb(hex_color)
        def linearize(c: int) -> float:
            c_norm = c / 255.0
            return c_norm / 12.92 if c_norm <= 0.03928 else ((c_norm + 0.055) / 1.055) ** 2.4
        return 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b)

    l1 = relative_luminance(color1)
    l2 = relative_luminance(color2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    ratio = (lighter + 0.05) / (darker + 0.05)

    wcag_aa = ratio >= 4.5
    wcag_aaa = ratio >= 7

    lines = [f"Contrast Ratio: {ratio:.2f}:1"]
    lines.append(f"  WCAG AA (normal text): {'PASS' if wcag_aa else 'FAIL'} (needs 4.5:1)")
    lines.append(f"  WCAG AAA (normal text): {'PASS' if wcag_aaa else 'FAIL'} (needs 7:1)")

    return "\n".join(lines)
