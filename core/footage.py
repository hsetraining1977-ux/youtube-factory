"""Footage fetcher — shared across all channels."""
import os
import random
import httpx
from pathlib import Path

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

KEYWORD_MAP = {
    "space": ["galaxy", "space nebula", "astronaut", "rocket launch", "stars"],
    "scifi": ["futuristic city", "technology neon", "space station", "robot"],
    "ancient": ["ancient ruins", "archaeological site", "old temple", "stone ruins"],
    "mystery": ["dark foggy night", "mysterious corridor", "ancient mystery"],
    "kids": ["colorful playground", "happy children", "animated colorful"],
    "nature": ["nature landscape", "colorful flowers", "forest sunlight"],
    "home": ["house interior", "home tools", "construction work"],
    "garden": ["green garden", "planting flowers", "vegetable garden"],
    "plumbing": ["water pipe", "plumber tools", "bathroom renovation"],
    "water": ["water flowing", "dripping water", "plumbing repair"],
    "castle": ["medieval castle", "ancient fortress", "stone wall"],
    "egypt": ["pyramids", "desert", "ancient egypt"],
    "science": ["laboratory", "science experiment", "chemistry"],
    "animal": ["wild animals", "cute animals", "nature wildlife"],
    "city": ["modern city", "urban landscape", "architecture"],
}


def get_keywords(visual_description: str, niche: str) -> list[str]:
    desc = visual_description.lower()
    keywords = []
    for key, values in KEYWORD_MAP.items():
        if key in desc or key in niche:
            keywords.extend(values[:2])
    if not keywords:
        niche_defaults = {
            "mystery_history": ["ancient ruins", "dark atmosphere", "historical"],
            "episodic_scifi": ["galaxy space", "futuristic technology", "neon city"],
            "kids_edu": ["colorful children", "happy playground", "bright colors"],
            "diy_home": ["home renovation", "tools workshop", "construction"],
        }
        keywords = niche_defaults.get(niche, ["nature landscape", "urban"])
    return keywords[:3]


def fetch_clip(query: str, path: str, min_dur: int = 10) -> str | None:
    if not PEXELS_API_KEY:
        return None
    r = httpx.get(
        "https://api.pexels.com/videos/search",
        headers={"Authorization": PEXELS_API_KEY},
        params={"query": query, "per_page": 15, "orientation": "landscape"},
        timeout=30
    )
    if r.status_code != 200:
        return None
    videos = [v for v in r.json().get("videos", []) if v.get("duration", 0) >= min_dur] or r.json().get("videos", [])
    if not videos:
        return None
    video = random.choice(videos[:5])
    files = sorted(video.get("video_files", []), key=lambda x: x.get("width", 0), reverse=True)
    target = next((f for f in files if f.get("width", 0) <= 1920), files[-1] if files else None)
    if not target:
        return None
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    resp = httpx.get(target["link"], timeout=120, follow_redirects=True)
    Path(path).write_bytes(resp.content)
    return path


def fetch_scene_footage(scenes: list[dict], output_dir: str, niche: str = "") -> list[str | None]:
    results = []
    for i, scene in enumerate(scenes):
        keywords = get_keywords(scene.get("visual_description", ""), niche)
        clip = None
        for kw in keywords:
            path = f"{output_dir}/footage_{i+1:02d}.mp4"
            clip = fetch_clip(kw, path, min_dur=scene.get("duration_seconds", 30))
            if clip:
                print(f"    ✓ Scene {i+1}: '{kw}'")
                break
        if not clip:
            fallback_path = f"{output_dir}/footage_{i+1:02d}.mp4"
            clip = fetch_clip("cinematic landscape", fallback_path)
        results.append(clip)
    return results
