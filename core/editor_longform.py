"""
Long-form video editor — produces 5-20 min horizontal videos (1920x1080).
Optimized for YouTube main feed and Smart TV viewing.
"""
from pathlib import Path
from moviepy.editor import (
    VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip,
    concatenate_videoclips, ImageClip, ColorClip
)
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from core.fonts import get_font


def make_branded_scene(
    footage_path: str | None,
    scene: dict,
    duration: float,
    branding: dict,
    scene_index: int,
    total_scenes: int
) -> CompositeVideoClip:
    """Create a branded scene with footage + overlays."""
    W, H = 1920, 1080

    # Base layer: footage or color background
    if footage_path and Path(footage_path).exists():
        try:
            raw = VideoFileClip(footage_path).without_audio().resize((W, H))
            if raw.duration < duration:
                n = int(duration / raw.duration) + 1
                raw = concatenate_videoclips([raw] * n)
            base = raw.subclip(0, duration)
        except Exception:
            base = ColorClip((W, H), color=_hex_to_rgb(branding["primary_color"])).set_duration(duration)
    else:
        base = ColorClip((W, H), color=_hex_to_rgb(branding["primary_color"])).set_duration(duration)

    overlays = [base]

    # Progress bar (top)
    progress = (scene_index + 1) / total_scenes
    prog_bar = _make_progress_bar(progress, W, branding["accent_color"], duration)
    overlays.append(prog_bar)

    # Text overlay (bottom)
    text = scene.get("on_screen_text", "")
    if text:
        text_overlay = _make_text_bar(text, duration, W, H, branding)
        overlays.append(text_overlay)

    # Channel watermark (top-left, subtle)
    watermark = _make_watermark(branding["channel_watermark"], duration, branding)
    overlays.append(watermark)

    return CompositeVideoClip(overlays)


def _make_progress_bar(progress: float, width: int, accent_hex: str, duration: float) -> ImageClip:
    img = Image.new("RGBA", (width, 6), (0, 0, 0, 80))
    draw = ImageDraw.Draw(img)
    fill_w = int(width * progress)
    r, g, b = _hex_to_rgb(accent_hex)
    draw.rectangle([0, 0, fill_w, 6], fill=(r, g, b, 220))
    return ImageClip(np.array(img)).set_duration(duration).set_position(("center", 0))


def _make_text_bar(text: str, duration: float, W: int, H: int, branding: dict) -> ImageClip:
    img = Image.new("RGBA", (W, 100), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    pr, pg, pb = _hex_to_rgb(branding["primary_color"])
    draw.rectangle([0, 5, W, 95], fill=(pr, pg, pb, 210))
    ar, ag, ab = _hex_to_rgb(branding["accent_color"])
    draw.rectangle([0, 5, W, 9], fill=(ar, ag, ab, 255))

    font = get_font(32, bold=True)

    bbox = draw.textbbox((0, 0), text, font=font)
    x = (W - (bbox[2] - bbox[0])) // 2
    draw.text((x, 32), text, fill=(255, 255, 255, 255), font=font)

    return (ImageClip(np.array(img))
            .set_duration(duration)
            .set_position(("center", H - 105)))


def _make_watermark(text: str, duration: float, branding: dict) -> ImageClip:
    img = Image.new("RGBA", (300, 36), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    pr, pg, pb = _hex_to_rgb(branding["primary_color"])
    draw.rectangle([0, 0, 300, 36], fill=(pr, pg, pb, 160))
    font = get_font(16, bold=False)
    draw.text((10, 10), text, fill=(200, 200, 200, 180), font=font)
    return (ImageClip(np.array(img))
            .set_duration(duration)
            .set_position((20, 20)))


def _hex_to_rgb(hex_color: str) -> tuple:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def assemble_longform(scenes, footage_files, audio_path, output_path, branding):
    """Assemble final long-form video."""
    print("  Assembling long-form video...")
    full_audio = AudioFileClip(audio_path)
    total_duration = full_audio.duration
    total_estimated = sum(s.get("duration_seconds", 60) if isinstance(s, dict) else s.duration_seconds for s in scenes)

    compiled = []
    for i, (scene, footage) in enumerate(zip(scenes, footage_files)):
        s = scene if isinstance(scene, dict) else scene.model_dump()
        ratio = s.get("duration_seconds", 60) / max(total_estimated, 1)
        dur = total_duration * ratio
        clip = make_branded_scene(footage, s, dur, branding, i, len(scenes))
        compiled.append(clip)

    final = concatenate_videoclips(compiled, method="compose").set_audio(full_audio)
    if final.duration > total_duration:
        final = final.subclip(0, total_duration)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    final.write_videofile(
        output_path, fps=30, codec="libx264", audio_codec="aac",
        temp_audiofile="temp_lf.m4a", remove_temp=True,
        logger=None, preset="fast", ffmpeg_params=["-crf", "23"]
    )
    return output_path
