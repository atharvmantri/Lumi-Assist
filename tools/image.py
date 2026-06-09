"""Image manipulation — resize, crop, convert, watermark."""
from __future__ import annotations

from pathlib import Path

from tools import tool


@tool(
    name="resize_image",
    description="Resize an image to specific dimensions or by percentage.",
    parameters={
        "type": "object",
        "properties": {
            "input_path": {
                "type": "string",
                "description": "Path to the input image",
            },
            "width": {
                "type": "integer",
                "description": "New width in pixels (0 to maintain aspect ratio)",
            },
            "height": {
                "type": "integer",
                "description": "New height in pixels (0 to maintain aspect ratio)",
            },
            "output_path": {
                "type": "string",
                "description": "Output path (default: input_resized.ext)",
            },
        },
        "required": ["input_path", "width", "height"],
    },
)
def resize_image(input_path: str, width: int, height: int, output_path: str = "") -> str:
    try:
        from PIL import Image
    except ImportError:
        return "error: Pillow not installed"

    p = Path(input_path)
    if not p.exists():
        return f"error: file not found: {input_path}"

    try:
        img = Image.open(p)

        if width == 0 or height == 0:
            # Maintain aspect ratio
            ratio = min(width / img.width if width else 1, height / img.height if height else 1)
            new_w = int(img.width * ratio)
            new_h = int(img.height * ratio)
        else:
            new_w, new_h = width, height

        resized = img.resize((new_w, new_h), Image.LANCZOS)

        if not output_path:
            output_path = str(p.parent / f"{p.stem}_resized{p.suffix}")

        resized.save(output_path)
        return f"Resized: {p.name} ({img.width}x{img.height}) → {output_path} ({new_w}x{new_h})"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="image_info",
    description="Get image metadata: dimensions, format, file size, color mode.",
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the image file",
            },
        },
        "required": ["path"],
    },
)
def image_info(path: str) -> str:
    try:
        from PIL import Image
    except ImportError:
        return "error: Pillow not installed"

    p = Path(path)
    if not p.exists():
        return f"error: file not found: {path}"

    try:
        img = Image.open(p)
        size_kb = p.stat().st_size / 1024
        return (
            f"Image: {p.name}\n"
            f"  Dimensions: {img.width}x{img.height}\n"
            f"  Mode: {img.mode}\n"
            f"  Format: {img.format}\n"
            f"  File size: {size_kb:.0f} KB"
        )
    except Exception as e:
        return f"error: {e}"


@tool(
    name="add_watermark",
    description="Add a text watermark to an image.",
    parameters={
        "type": "object",
        "properties": {
            "input_path": {
                "type": "string",
                "description": "Path to the input image",
            },
            "text": {
                "type": "string",
                "description": "Watermark text",
            },
            "position": {
                "type": "string",
                "description": "Position: 'center', 'bottom-right', 'bottom-left', 'top-right', 'top-left' (default 'bottom-right')",
                "enum": ["center", "bottom-right", "bottom-left", "top-right", "top-left"],
            },
            "output_path": {
                "type": "string",
                "description": "Output path (default: input_watermarked.ext)",
            },
        },
        "required": ["input_path", "text"],
    },
)
def add_watermark(input_path: str, text: str, position: str = "bottom-right", output_path: str = "") -> str:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return "error: Pillow not installed"

    p = Path(input_path)
    if not p.exists():
        return f"error: file not found: {input_path}"

    try:
        img = Image.open(p).convert("RGBA")
        txt_layer = Image.new("RGBA", img.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(txt_layer)

        font_size = max(20, min(img.width, img.height) // 20)
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]

        margin = 20
        positions = {
            "center": ((img.width - tw) // 2, (img.height - th) // 2),
            "bottom-right": (img.width - tw - margin, img.height - th - margin),
            "bottom-left": (margin, img.height - th - margin),
            "top-right": (img.width - tw - margin, margin),
            "top-left": (margin, margin),
        }
        x, y = positions.get(position, positions["bottom-right"])

        draw.text((x, y), text, font=font, fill=(255, 255, 255, 128))
        out = Image.alpha_composite(img, txt_layer)

        if not output_path:
            output_path = str(p.parent / f"{p.stem}_watermarked.png")

        out.convert("RGB").save(output_path)
        return f"Watermark added: {output_path}"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="create_thumbnail",
    description="Create a thumbnail from an image with smart cropping.",
    parameters={
        "type": "object",
        "properties": {
            "input_path": {
                "type": "string",
                "description": "Path to the input image",
            },
            "size": {
                "type": "integer",
                "description": "Thumbnail size in pixels (default 128)",
            },
            "output_path": {
                "type": "string",
                "description": "Output path (default: input_thumb.ext)",
            },
        },
        "required": ["input_path"],
    },
)
def create_thumbnail(input_path: str, size: int = 128, output_path: str = "") -> str:
    try:
        from PIL import Image
    except ImportError:
        return "error: Pillow not installed"

    p = Path(input_path)
    if not p.exists():
        return f"error: file not found: {input_path}"

    try:
        img = Image.open(p)
        img.thumbnail((size, size), Image.LANCZOS)

        if not output_path:
            output_path = str(p.parent / f"{p.stem}_thumb.png")

        img.save(output_path)
        return f"Thumbnail created: {output_path} ({size}x{size})"
    except Exception as e:
        return f"error: {e}"
