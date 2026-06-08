"""Unified audio generator — shared across all channels."""
import os
import httpx
from pathlib import Path


ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")


def generate_audio(text: str, output_path: str, voice_config: dict) -> str:
    voice_id = voice_config.get("voice_id", "pNInz6obpgDQGcFmaJgB")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    headers = {"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json", "Accept": "audio/mpeg"}
    payload = {
        "text": text,
        "model_id": voice_config.get("model", "eleven_turbo_v2_5"),
        "voice_settings": {
            "stability": voice_config.get("stability", 0.75),
            "similarity_boost": 0.85,
            "style": voice_config.get("style", 0.40),
            "use_speaker_boost": True
        }
    }

    r = httpx.post(url, json=payload, headers=headers, timeout=120)
    r.raise_for_status()
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_bytes(r.content)
    return output_path


def generate_full_narration(scenes: list, output_dir: str, voice_config: dict) -> str:
    """Generate audio per scene, then combine into one file using moviepy."""
    from moviepy.editor import AudioFileClip, concatenate_audioclips
    from pathlib import Path
    import os

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    scene_files = []
    for i, scene in enumerate(scenes):
        text = scene["narration"] if isinstance(scene, dict) else scene.narration
        path = f"{output_dir}/scene_{i+1:02d}.mp3"
        generate_audio(text, path, voice_config)
        scene_files.append(path)

    # Combine all scene audios into one continuous narration track.
    clips = [AudioFileClip(f) for f in scene_files]
    combined = concatenate_audioclips(clips)

    combined_path = os.path.abspath(f"{output_dir}/narration_full.mp3")
    combined.write_audiofile(combined_path, fps=44100, logger=None)

    # Clean up
    for c in clips:
        try:
            c.close()
        except Exception:
            pass

    if not Path(combined_path).exists():
        raise RuntimeError(f"Failed to create combined narration: {combined_path}")

    return combined_path
