"""Screenshot comparison and visual testing tools."""
from __future__ import annotations

from pathlib import Path

from tools import tool


@tool(
    name="compare_images",
    description="Compare two images pixel-by-pixel and report differences.",
    parameters={
        "type": "object",
        "properties": {
            "image1": {
                "type": "string",
                "description": "Path to the first image",
            },
            "image2": {
                "type": "string",
                "description": "Path to the second image",
            },
        },
        "required": ["image1", "image2"],
    },
)
def compare_images(image1: str, image2: str) -> str:
    try:
        from PIL import Image, ImageChops
    except ImportError:
        return "error: Pillow not installed"

    p1, p2 = Path(image1), Path(image2)
    if not p1.exists():
        return f"error: image not found: {image1}"
    if not p2.exists():
        return f"error: image not found: {image2}"

    try:
        img1 = Image.open(p1)
        img2 = Image.open(p2)

        if img1.size != img2.size:
            return f"Images differ in size:\n  {p1.name}: {img1.size}\n  {p2.name}: {img2.size}"

        diff = ImageChops.difference(img1, img2)
        # Count non-zero pixels
        diff_data = list(diff.getdata())
        different = sum(1 for p in diff_data if p != (0, 0, 0))
        total = len(diff_data)
        pct = (different / total) * 100

        if different == 0:
            return f"Images are identical ({img1.size[0]}x{img1.size[1]}, {total:,} pixels)"

        return (
            f"Image Comparison:\n"
            f"  Size: {img1.size[0]}x{img1.size[1]}\n"
            f"  Different pixels: {different:,}/{total:,} ({pct:.1f}%)\n"
            f"  {'Similar' if pct < 1 else 'Very different' if pct > 50 else 'Moderately different'}"
        )
    except Exception as e:
        return f"error: {e}"


@tool(
    name="image_to_ascii",
    description="Convert an image to ASCII art text.",
    parameters={
        "type": "object",
        "properties": {
            "image_path": {
                "type": "string",
                "description": "Path to the image",
            },
            "width": {
                "type": "integer",
                "description": "Output width in characters (default 60)",
            },
        },
        "required": ["image_path"],
    },
)
def image_to_ascii(image_path: str, width: int = 60) -> str:
    try:
        from PIL import Image
    except ImportError:
        return "error: Pillow not installed"

    p = Path(image_path)
    if not p.exists():
        return f"error: image not found: {image_path}"

    try:
        img = Image.open(p).convert("L")  # grayscale
        aspect = img.height / img.width
        new_width = width
        new_height = int(aspect * new_width * 0.5)  # 0.5 for char aspect ratio
        img = img.resize((new_width, new_height))

        chars = "@%#*+=-:. "
        pixels = img.getdata()
        ascii_chars = [chars[p // 32] for p in pixels]
        ascii_str = "".join(ascii_chars)

        lines = [ascii_str[i:i+new_width] for i in range(0, len(ascii_str), new_width)]

        # Limit output
        if len(lines) > 40:
            lines = lines[:40] + ["  ..."]

        return "\n".join(lines)
    except Exception as e:
        return f"error: {e}"
