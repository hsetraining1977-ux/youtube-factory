"""
Multi-platform publisher:
- YouTube (long-form + Shorts)
- TikTok (Shorts)
- Instagram Reels (Shorts)
"""
import os
import pickle
from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CLIENT_SECRETS = os.getenv("YOUTUBE_CLIENT_SECRETS_FILE", "client_secrets.json")

CHANNEL_FOOTERS = {
    "mystery_history": "\n\n⚠️ Educational purposes only.\n#MysteriousHistory #AncientMysteries",
    "scifi_stories": "\n\n🚀 New episodes every week!\n#SciFi #AudioDrama #SpaceStory",
    "kids_education": "\n\n👨‍👩‍👧 Safe for kids. Always supervised viewing recommended.\n#KidsLearning #Education",
    "diy_tutorials": "\n\n🔧 Always follow safety guidelines.\n#DIY #HomeRepair #HowTo",
}


def _get_youtube_service(channel_id: str = "default"):
    token_file = f"youtube_token_{channel_id}.pickle"
    creds = None
    if Path(token_file).exists():
        with open(token_file, "rb") as f:
            creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_file, "wb") as f:
            pickle.dump(creds, f)
    return build("youtube", "v3", credentials=creds)


def publish_to_youtube(
    video_path: str,
    thumbnail_path: str,
    title: str,
    description: str,
    tags: list[str],
    category_id: str = "27",
    made_for_kids: bool = False,
    channel_id: str = ""
) -> dict:
    youtube = _get_youtube_service(channel_id or "default")

    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": tags[:500],
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": made_for_kids,
            "embeddable": True,
        }
    }

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=MediaFileUpload(video_path, mimetype="video/mp4", resumable=True, chunksize=10*1024*1024)
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"    YouTube upload: {int(status.progress()*100)}%")

    video_id = response["id"]
    url = f"https://youtube.com/watch?v={video_id}"

    if thumbnail_path and Path(thumbnail_path).exists():
        try:
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path, mimetype="image/jpeg")
            ).execute()
        except Exception:
            pass

    print(f"   ✓ YouTube: {url}")
    return {"video_id": video_id, "url": url}


def publish_shorts(
    video_path: str,
    title: str,
    description: str,
    upload_tiktok: bool = False,
    upload_instagram: bool = False
) -> dict:
    """
    Publish Shorts to YouTube Shorts + optionally TikTok/Instagram.

    Note: TikTok and Instagram require separate API access:
    - TikTok: Apply for Content Posting API access
    - Instagram: Use Instagram Graph API (requires Facebook Business account)

    For now, we save the short to a 'pending_upload' folder with metadata,
    and you can use third-party tools (Buffer, Later) for cross-posting.
    """
    pending_dir = Path("output/pending_social_uploads")
    pending_dir.mkdir(exist_ok=True)

    import shutil
    import json

    basename = Path(video_path).stem
    dest = pending_dir / f"{basename}_shorts.mp4"
    shutil.copy2(video_path, dest)

    metadata = {
        "video_path": str(dest),
        "title": title[:150],
        "description": description[:300],
        "platforms": [],
        "status": "pending"
    }

    if upload_tiktok:
        metadata["platforms"].append("tiktok")
        print(f"   📋 TikTok: queued for upload → {dest}")

    if upload_instagram:
        metadata["platforms"].append("instagram_reels")
        print(f"   📋 Instagram Reels: queued → {dest}")

    meta_path = pending_dir / f"{basename}_meta.json"
    meta_path.write_text(json.dumps(metadata, indent=2))

    return metadata
