"""Channel-aware thumbnail generator."""
import os
import httpx
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import numpy as np

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def generate_thumbnail_bg(prompt: str, path: str) -> str:
    r = httpx.post(
        "https://api.openai.com/v1/images/generations",
        json={"model": "dall-e-3", "prompt": prompt + " No text. Cinematic.", "size": "1792x1024", "quality": "standard", "n": 1},
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
        timeout=60
    )
    r.raise_for_status()
    img = Image.open(BytesIO(httpx.get(r.json()["data"][0]["url"], timeout=60).content)).convert("RGB")
    img = img.resize((1280, 720), Image.LANCZOS)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "JPEG", quality=95)
    return path


def _hex(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def add_text_overlay(img_path: str, title: str, branding: dict, output_path: str) -> str:
    img = Image.open(img_path).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Gradient bottom
    for y in range(img.height // 2, img.height):
        a = int(190 * (y - img.height // 2) / (img.height // 2))
        pr, pg, pb = _hex(branding["primary_color"])
        draw.rectangle([0, y, img.width, y + 1], fill=(pr, pg, pb, min(a, 190)))

    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)

    try:
        title_font = ImageFont.truetype("arialbd.ttf", 62)
        small_font = ImageFont.truetype("arialbd.ttf", 28)
    except Exception:
        title_font = small_font = ImageFont.load_default()

    # Title (2 lines max)
    words, lines, line = title.upper().split(), [], ""
    for w in words:
        test = f"{line} {w}".strip()
        if draw.textbbox((0, 0), test, font=title_font)[2] < img.width - 60:
            line = test
        else:
            if line: lines.append(line)
            line = w
        if len(lines) >= 2: break
    if line and len(lines) < 2:
        lines.append(line)

    ar, ag, ab = _hex(branding["accent_color"])
    y = img.height - len(lines) * 80 - 25
    for l in lines:
        bx = draw.textbbox((0, 0), l, font=title_font)
        x = (img.width - (bx[2] - bx[0])) // 2
        draw.text((x + 2, y + 2), l, fill=(0, 0, 0, 255), font=title_font)
        draw.text((x, y), l, fill=(ar, ag, ab, 255), font=title_font)
        y += 80

    # Channel badge
    pr, pg, pb = _hex(branding["primary_color"])
    draw.rectangle([10, 10, 280, 52], fill=(pr, pg, pb, 220))
    draw.rectangle([10, 10, 280, 15], fill=(ar, ag, ab, 255))
    draw.text((20, 18), branding["channel_watermark"][:22], fill=(255, 255, 255, 255), font=small_font)

    final = img.convert("RGB")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    final.save(output_path, "JPEG", quality=95)
    return output_path


def create_thumbnail(prompt: str, title: str, work_dir: str, branding: dict) -> str:
    raw = f"{work_dir}/thumbnail_raw.jpg"
    final = f"{work_dir}/thumbnail.jpg"
    generate_thumbnail_bg(prompt, raw)
    return add_text_overlay(raw, title, branding, final)
