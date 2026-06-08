"""
Multi-Channel YouTube Factory — Main Orchestrator
Produces long-form videos AND Shorts for all 4 channels.

Usage:
  python factory.py --channel mystery_history
  python factory.py --channel scifi_stories --series echo_station --episode 1
  python factory.py --all                    (run all channels)
  python factory.py --schedule               (daily automation)
"""
import os
import sys
import json
import yaml
import random
import argparse
import traceback
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Add core to path
sys.path.insert(0, str(Path(__file__).parent))

from core.script_engine import generate_script
from core.audio import generate_full_narration, generate_audio

# Lazy imports for heavy modules
def get_footage_fetcher():
    from core.footage import fetch_scene_footage
    return fetch_scene_footage

def get_longform_editor():
    from core.editor_longform import assemble_longform
    return assemble_longform

def get_shorts_editor():
    from core.editor_shorts import assemble_shorts
    return assemble_shorts

def get_thumbnail_creator():
    from core.thumbnail import create_thumbnail
    return create_thumbnail

def get_publisher():
    from core.publisher import publish_to_youtube, publish_shorts
    return publish_to_youtube, publish_shorts


# ── Config loader ──────────────────────────────────────────────

def load_config() -> dict:
    with open("config/channels.yaml") as f:
        return yaml.safe_load(f)


def load_topics(channel_id: str, config: dict) -> list[str]:
    """Load topic list for a channel."""
    topics_file = config["channels"][channel_id]["content"]["topics_file"]
    with open(topics_file) as f:
        data = yaml.safe_load(f)

    topics = []
    for category, items in data.get("categories", data).items():
        if isinstance(items, list):
            topics.extend(items)
    return topics


def load_series_data(series_id: str) -> dict:
    """Load series data for episodic content."""
    with open("channels/scifi_stories/series_list.yaml") as f:
        data = yaml.safe_load(f)
    for series in data["series"]:
        if series["id"] == series_id:
            return series
    raise ValueError(f"Series '{series_id}' not found")


# ── State management ───────────────────────────────────────────

def load_channel_state(channel_id: str) -> dict:
    state_file = Path(f"output/{channel_id}/state.json")
    state_file.parent.mkdir(parents=True, exist_ok=True)
    if state_file.exists():
        return json.loads(state_file.read_text())
    return {"used_topics": [], "produced_videos": [], "episode_progress": {}}


def save_channel_state(channel_id: str, state: dict):
    state_file = Path(f"output/{channel_id}/state.json")
    state_file.write_text(json.dumps(state, indent=2))


# ── Core pipeline ──────────────────────────────────────────────

def produce_video(channel_id: str, config: dict, topic: str = None,
                  episode_context: dict = None, force: bool = False) -> dict:
    """
    Full production pipeline for one video.
    Returns dict with paths to long-form and shorts versions.

    force=True bypasses the trading-hours time guard (manual testing only).
    """
    # ── SAFETY GATE: never run during/near trading market hours ──
    from core.time_guard import is_safe_to_run
    allowed, reason = is_safe_to_run()
    print(reason)
    if not allowed and not force:
        return {"channel": channel_id, "status": "blocked_by_time_guard", "reason": reason}

    channel = config["channels"][channel_id]
    global_cfg = config["global"]
    niche = channel["niche"]
    branding = channel["branding"]
    voice_config = channel["voice"]

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    work_dir = Path(f"output/{channel_id}/{ts}")
    work_dir.mkdir(parents=True, exist_ok=True)

    result = {"channel": channel_id, "timestamp": ts, "status": "failed"}

    print(f"\n{'═'*60}")
    print(f"🎬  [{channel['name'].upper()}]  {topic or episode_context.get('episode_title', '')}")
    print(f"{'═'*60}")

    try:
        # ── 1. Script ──────────────────────────────────────────
        print("\n📝 [1/6] Generating script...")
        script = generate_script(niche, topic or "", episode_context)
        (work_dir / "script.json").write_text(script.model_dump_json(indent=2))
        print(f"   ✓ '{script.title}'  (~{script.estimated_duration_seconds//60}min)")

        # ── 2. Audio ───────────────────────────────────────────
        print("\n🎙️  [2/6] Generating narration audio...")
        audio_dir = str(work_dir / "audio")
        narration_path = generate_full_narration(script.scenes, audio_dir, voice_config)
        print(f"   ✓ Narration combined")

        # ── 3. Footage ─────────────────────────────────────────
        print("\n🎥 [3/6] Fetching stock footage...")
        fetch_footage = get_footage_fetcher()
        footage_dir = str(work_dir / "footage")
        footage_files = fetch_footage(
            [s.model_dump() for s in script.scenes], footage_dir
        )
        found = sum(1 for f in footage_files if f)
        print(f"   ✓ Footage: {found}/{len(script.scenes)} scenes")

        # ── 4. Long-form video ─────────────────────────────────
        print("\n🎞️  [4/6] Assembling long-form video (1920×1080)...")
        assemble_lf = get_longform_editor()
        lf_path = str(work_dir / "video_longform.mp4")
        assemble_lf(
            [s.model_dump() for s in script.scenes],
            footage_files,
            narration_path,
            lf_path,
            branding
        )
        print(f"   ✓ Long-form: {lf_path}")

        # ── 5. Shorts video ────────────────────────────────────
        print("\n📱 [5/6] Assembling Shorts/TikTok version (1080×1920)...")
        assemble_short = get_shorts_editor()
        shorts_path = str(work_dir / "video_shorts.mp4")
        assemble_short(
            script.shorts_hook,
            script.shorts_summary,
            footage_files,
            narration_path,
            shorts_path,
            branding
        )
        print(f"   ✓ Shorts: {shorts_path}")

        # ── 6. Thumbnail ───────────────────────────────────────
        print("\n🖼️  [6/6] Creating thumbnail...")
        create_thumb = get_thumbnail_creator()
        thumb_path = create_thumb(
            script.thumbnail_prompt,
            script.title,
            str(work_dir),
            branding
        )
        print(f"   ✓ Thumbnail: {thumb_path}")

        result.update({
            "status": "ready",
            "title": script.title,
            "description": script.description,
            "tags": script.tags,
            "longform_path": lf_path,
            "shorts_path": shorts_path,
            "thumbnail_path": thumb_path,
            "work_dir": str(work_dir),
            "script": script.model_dump()
        })

        print(f"\n✅  Production complete: {script.title}")

    except Exception as e:
        result["error"] = traceback.format_exc()
        print(f"\n❌  Error: {e}\n{traceback.format_exc()}")

    return result


def upload_produced_video(result: dict, channel_id: str, config: dict) -> dict:
    """Upload produced video to YouTube + social platforms."""
    channel = config["channels"][channel_id]
    publish_yt, publish_shorts = get_publisher()

    print(f"\n📤 Uploading long-form to YouTube...")
    yt_result = publish_yt(
        video_path=result["longform_path"],
        thumbnail_path=result["thumbnail_path"],
        title=result["title"],
        description=result["description"],
        tags=result["tags"],
        category_id=channel["seo"]["category_id"],
        made_for_kids=channel["seo"].get("made_for_kids", False),
        channel_id=channel["publishing"].get("youtube_channel_id", "")
    )
    result["youtube_url"] = yt_result.get("url", "")

    if channel["publishing"].get("tiktok") or channel["publishing"].get("instagram_reels"):
        print(f"   📱 Uploading Shorts version...")
        shorts_title = f"{result['title'][:80]} #Shorts"
        publish_shorts(
            video_path=result["shorts_path"],
            title=shorts_title,
            description=result["description"][:150],
            upload_tiktok=channel["publishing"].get("tiktok", False),
            upload_instagram=channel["publishing"].get("instagram_reels", False)
        )

    return result


# ── Channel runners ────────────────────────────────────────────

def run_mystery_history(config: dict, upload: bool = True, force: bool = False) -> dict:
    state = load_channel_state("mystery_history")
    topics = load_topics("mystery_history", config)
    unused = [t for t in topics if t not in state["used_topics"]]
    if not unused:
        unused = topics  # Reset cycle
    topic = random.choice(unused)

    result = produce_video("mystery_history", config, topic=topic, force=force)

    if result["status"] == "ready":
        state["used_topics"].append(topic)
        state["produced_videos"].append(result)
        if upload:
            upload_produced_video(result, "mystery_history", config)
        save_channel_state("mystery_history", state)

    return result


def run_scifi_stories(config: dict, series_id: str = None, episode: int = None,
                      upload: bool = True, force: bool = False) -> dict:
    state = load_channel_state("scifi_stories")
    if not series_id:
        series_id = "echo_station"  # Default to first series

    series = load_series_data(series_id)
    current_ep = state["episode_progress"].get(series_id, 0) + 1
    if episode:
        current_ep = episode

    if current_ep > len(series["episodes"]):
        print(f"   Series '{series_id}' complete! Starting new series...")
        series_id = "last_colony"
        series = load_series_data(series_id)
        current_ep = 1

    ep_data = series["episodes"][current_ep - 1]

    episode_context = {
        "series_id": series_id,
        "series_title": series["title"],
        "series_premise": series["premise"],
        "episode_number": current_ep,
        "episode_title": ep_data["title"],
        "episode_hook": ep_data["hook"],
        "previous_summary": state["episode_progress"].get(f"{series_id}_summary_ep{current_ep-1}", "")
    }

    result = produce_video("scifi_stories", config, episode_context=episode_context, force=force)

    if result["status"] == "ready":
        state["episode_progress"][series_id] = current_ep
        state["produced_videos"].append(result)
        if upload:
            upload_produced_video(result, "scifi_stories", config)
        save_channel_state("scifi_stories", state)

    return result


def run_kids_education(config: dict, upload: bool = True, force: bool = False) -> dict:
    state = load_channel_state("kids_education")
    topics = load_topics("kids_education", config)
    unused = [t for t in topics if t not in state["used_topics"]]
    if not unused:
        unused = topics
    topic = random.choice(unused)

    result = produce_video("kids_education", config, topic=topic, force=force)

    if result["status"] == "ready":
        state["used_topics"].append(topic)
        state["produced_videos"].append(result)
        if upload:
            upload_produced_video(result, "kids_education", config)
        save_channel_state("kids_education", state)

    return result


def run_diy_tutorials(config: dict, upload: bool = True, force: bool = False) -> dict:
    state = load_channel_state("diy_tutorials")
    topics = load_topics("diy_tutorials", config)
    unused = [t for t in topics if t not in state["used_topics"]]
    if not unused:
        unused = topics
    topic = random.choice(unused)

    result = produce_video("diy_tutorials", config, topic=topic, force=force)

    if result["status"] == "ready":
        state["used_topics"].append(topic)
        state["produced_videos"].append(result)
        if upload:
            upload_produced_video(result, "diy_tutorials", config)
        save_channel_state("diy_tutorials", state)

    return result


CHANNEL_RUNNERS = {
    "mystery_history": run_mystery_history,
    "kids_education": run_kids_education,
    "diy_tutorials": run_diy_tutorials,
}


# ── Scheduler ─────────────────────────────────────────────────

def run_scheduled_factory():
    """Run all channels on their configured schedules."""
    import schedule
    import time

    config = load_config()

    def make_job(channel_id: str):
        def job():
            print(f"\n⏰ Scheduled: {channel_id}")
            if channel_id == "scifi_stories":
                run_scifi_stories(config)
            else:
                CHANNEL_RUNNERS[channel_id](config)
        return job

    for ch_id, ch_cfg in config["channels"].items():
        if not ch_cfg["enabled"]:
            continue
        sched = ch_cfg["content"]["upload_schedule"]
        for day in sched["days"]:
            getattr(schedule.every(), day.lower()).at(sched["time"]).do(make_job(ch_id))
        print(f"📅  {ch_cfg['name']}: {', '.join(sched['days'])} at {sched['time']}")

    print("\n🤖 Multi-Channel Factory Running — Press Ctrl+C to stop\n")
    while True:
        schedule.run_pending()
        time.sleep(60)


# ── CLI ────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-Channel YouTube Factory")
    parser.add_argument("--channel", choices=["mystery_history", "scifi_stories", "kids_education", "diy_tutorials", "all"])
    parser.add_argument("--series", type=str, help="Series ID (for scifi_stories)")
    parser.add_argument("--episode", type=int, help="Episode number")
    parser.add_argument("--topic", type=str, help="Override topic")
    parser.add_argument("--no-upload", action="store_true", help="Produce only, don't upload")
    parser.add_argument("--schedule", action="store_true", help="Run on schedule")
    parser.add_argument("--dry-run", action="store_true", help="Script only (no video)")
    parser.add_argument("--force", action="store_true",
                        help="Bypass trading-hours time guard (manual testing only)")

    args = parser.parse_args()
    config = load_config()
    upload = not args.no_upload
    force = args.force

    if args.schedule:
        run_scheduled_factory()
    elif args.channel == "all":
        print("🚀 Running all channels...")
        for ch in ["mystery_history", "kids_education", "diy_tutorials"]:
            CHANNEL_RUNNERS[ch](config, upload=upload, force=force)
        run_scifi_stories(config, upload=upload, force=force)
    elif args.channel == "scifi_stories":
        run_scifi_stories(config, series_id=args.series, episode=args.episode, upload=upload, force=force)
    elif args.channel in CHANNEL_RUNNERS:
        CHANNEL_RUNNERS[args.channel](config, upload=upload, force=force)
    else:
        parser.print_help()
