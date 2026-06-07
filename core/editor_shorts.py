"""
Shorts/TikTok/Reels editor — produces 58-second VERTICAL videos (1080x1920).
Auto-generated from the same script and footage as the long-form video.
"""
from pathlib import Path
from moviepy.editor import (
    VideoFileClip, AudioFileClip, CompositeVideoClip,
    concatenate_videoclips, ImageClip, ColorClip
)
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import random


W_SHORT, H_SHORT = 1080, 1920  # Vertical 9:16


def crop_to_vertical(clip: VideoFileClip) -> VideoFileClip:
    """Crop horizontal 16:9 footage to vertical 9:16 center crop."""
    orig_w, orig_h = clip.size
    target_w = int(orig_h * 9 / 16)
    if target_w > orig_w:
        target_h = int(orig_w * 16 / 9)
        clip = clip.crop(y_center=orig_h / 2, height=target_h)
    else:
        clip = clip.crop(x_center=orig_w / 2, width=target_w)
    return clip.resize((W_SHORT, H_SHORT))


def make_shorts_hook_overlay(hook_text: str, duration: float, branding: dict) -> ImageClip:
    """Large dramatic hook text at top of screen."""
    img = Image.new("RGBA", (W_SHORT, 350), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Gradient overlay
    for y in range(350):
        alpha = int(200 * (1 - y / 350))
        pr, pg, pb = _hex_to_rgb(branding["primary_color"])
        draw.rectangle([0, y, W_SHORT, y + 1], fill=(pr, pg, pb, alpha))

    try:
        font = ImageFont.truetype("arialbd.ttf", 52)
    except Exception:
        font = ImageFont.load_default()

    # Word wrap
    words = hook_text.upper().split()
    lines, line = [], ""
    for word in words:
        test = f"{line} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] < W_SHORT - 80:
            line = test
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    lines = lines[:3]

    ar, ag, ab = _hex_to_rgb(branding["accent_color"])
    y_pos = 40
    for l in lines:
        bbox = draw.textbbox((0, 0), l, font=font)
        x = (W_SHORT - (bbox[2] - bbox[0])) // 2
        draw.text((x + 2, y_pos + 2), l, fill=(0, 0, 0, 180), font=font)
        draw.text((x, y_pos), l, fill=(ar, ag, ab, 255), font=font)
        y_pos += 70

    return ImageClip(np.array(img)).set_duration(duration).set_position(("center", 50))


def make_shorts_caption(text: str, duration: float, branding: dict) -> ImageClip:
    """Caption bar at bottom for shorts."""
    img = Image.new("RGBA", (W_SHORT, 140), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    pr, pg, pb = _hex_to_rgb(branding["primary_color"])
    draw.rectangle([0, 10, W_SHORT, 130], fill=(pr, pg, pb, 230))
    ar, ag, ab = _hex_to_rgb(branding["accent_color"])
    draw.rectangle([0, 10, W_SHORT, 15], fill=(ar, ag, ab, 255))

    try:
        font = ImageFont.truetype("arialbd.ttf", 38)
    except Exception:
        font = ImageFont.load_default()

    # Truncate to fit
    display = text[:50] + "..." if len(text) > 50 else text
    bbox = draw.textbbox((0, 0), display, font=font)
    x = max(20, (W_SHORT - (bbox[2] - bbox[0])) // 2)
    draw.text((x, 38), display, fill=(255, 255, 255, 255), font=font)

    return (ImageClip(np.array(img))
            .set_duration(duration)
            .set_position(("center", H_SHORT - 150)))


def make_subscribe_cta(duration: float, branding: dict) -> ImageClip:
    """Animated-style subscribe CTA for last 5 seconds."""
    img = Image.new("RGBA", (W_SHORT, 200), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    ar, ag, ab = _hex_to_rgb(branding["accent_color"])
    draw.rounded_rectangle([W_SHORT//2 - 200, 30, W_SHORT//2 + 200, 120],
                            radius=35, fill=(ar, ag, ab, 240))
    try:
        font = ImageFont.truetype("arialbd.ttf", 40)
        small = ImageFont.truetype("arial.ttf", 26)
    except Exception:
        font = small = ImageFont.load_default()

    draw.text((W_SHORT//2 - 95, 48), "SUBSCRIBE", fill=(0, 0, 0, 255), font=font)
    draw.text((W_SHORT//2 - 130, 130), "For more stories!", fill=(255, 255, 255, 200), font=small)

    return (ImageClip(np.array(img))
            .set_duration(duration)
            .set_position(("center", H_SHORT // 2 - 50)))


def _hex_to_rgb(hex_color: str) -> tuple:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def assemble_shorts(
    shorts_hook_text: str,
    shorts_narration: str,
    footage_files: list,
    audio_path: str,
    output_path: str,
    branding: dict
) -> str:
    """
    Assemble a 58-second vertical Shorts video.
    Uses best footage clips cropped to vertical format.
    """
    print("  Assembling Shorts/TikTok version...")
    from core.audio import generate_audio

    # Generate separate short audio
    short_audio_path = output_path.replace(".mp4", "_audio.mp3")
    generate_audio(shorts_narration, short_audio_path, branding.get("voice", {}))
    audio = AudioFileClip(short_audio_path)

    target_duration = min(audio.duration, 58.0)

    # Pick best footage clips
    valid_footage = [f for f in footage_files if f and Path(f).exists()]
    clips = []
    per_clip = target_duration / max(len(valid_footage), 1)

    for footage_path in valid_footage:
        try:
            raw = VideoFileClip(footage_path).without_audio()
            vertical = crop_to_vertical(raw)
            start = random.uniform(0, max(0, vertical.duration - per_clip - 2))
            segment = vertical.subclip(start, min(start + per_clip, vertical.duration))
            clips.append(segment)
        except Exception:
            clips.append(ColorClip((W_SHORT, H_SHORT),
                                   color=_hex_to_rgb(branding["primary_color"])).set_duration(per_clip))

    if not clips:
        clips = [ColorClip((W_SHORT, H_SHORT),
                           color=_hex_to_rgb(branding["primary_color"])).set_duration(target_duration)]

    base_video = concatenate_videoclips(clips, method="compose")
    if base_video.duration > target_duration:
        base_video = base_video.subclip(0, target_duration)

    # Overlays
    hook_overlay = make_shorts_hook_overlay(shorts_hook_text, min(4.0, target_duration), branding)
    caption = make_shorts_caption(shorts_hook_text[:60], target_duration, branding)
    cta = make_subscribe_cta(min(5.0, target_duration), branding)

    final = (CompositeVideoClip([base_video, caption, cta])
             .set_audio(audio.subclip(0, target_duration)))

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    final.write_videofile(
        output_path, fps=30, codec="libx264", audio_codec="aac",
        temp_audiofile="temp_short.m4a", remove_temp=True,
        logger=None, preset="fast"
    )
    return output_path
