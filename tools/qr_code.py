"""QR code generation."""
from __future__ import annotations

from pathlib import Path

from core.config import PROJECT_ROOT
from tools import tool


@tool(
    name="generate_qr_code",
    description="Generate a QR code image from text or a URL. Saves as PNG and returns the path.",
    parameters={
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "Text or URL to encode in the QR code",
            },
            "output_path": {
                "type": "string",
                "description": "Output file path (default: data/qr_code_TIMESTAMP.png)",
            },
            "size": {
                "type": "integer",
                "description": "QR code pixel size (default 300)",
            },
        },
        "required": ["text"],
    },
)
def generate_qr_code(text: str, output_path: str = "", size: int = 300) -> str:
    try:
        import qrcode
    except ImportError:
        return "error: qrcode package not installed. Run: pip install qrcode[pil]"

    from datetime import datetime

    out_dir = PROJECT_ROOT / "data"
    out_dir.mkdir(parents=True, exist_ok=True)

    if not output_path:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = str(out_dir / f"qr_code_{ts}.png")

    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(text)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        img = img.resize((size, size))
        img.save(output_path)

        return f"QR code generated for: {text[:60]}{'...' if len(text) > 60 else ''}\nSaved to: {output_path} ({size}x{size}px)"
    except Exception as e:
        return f"error generating QR code: {e}"
