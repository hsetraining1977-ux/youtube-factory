# Multi-Channel YouTube Factory — Complete Guide

## 4 Channels × 2 Formats = Maximum Revenue

| Channel | Niche | Videos/Week | Format |
|---------|-------|-------------|--------|
| Mysteries of History | Historical mysteries | 5/week | Long + Shorts |
| Cosmic Chronicles | Episodic sci-fi | 3/week | Long + Shorts |
| Wonder World Kids | Kids education | 4/week | Long + Shorts |
| Fix It Fast | DIY home repair | 3/week | Long + Shorts |

**Total output: 15 long-form + 15 Shorts = 30 videos/week across all channels**

---

## Budget: ~$40-60/month for ALL 4 channels

| Cost | Service |
|------|---------|
| ~$8 | Claude Haiku (scripts × 4 channels) |
| $22 | ElevenLabs Creator (1 account, 4 voices) |
| $1-4 | DALL-E 3 (thumbnails) |
| Free | Pexels (footage) |
| Free | YouTube API |
| **~$35-50/mo** | **120 videos/month** |

---

## Setup

### 1. Install
```bash
pip install -r requirements.txt
```

### 2. Configure .env
```bash
cp .env.example .env
# Fill in: ANTHROPIC_API_KEY, ELEVENLABS_API_KEY, OPENAI_API_KEY, PEXELS_API_KEY
```

### 3. YouTube OAuth (once per channel)
Each channel needs its own Google account + OAuth:
```bash
# First run will open browser for auth — do this once per channel
python factory.py --channel mystery_history --no-upload
```

---

## Usage

```bash
# Single channel
python factory.py --channel mystery_history

# Sci-fi episode (auto-progresses through series)
python factory.py --channel scifi_stories

# Specific episode
python factory.py --channel scifi_stories --series echo_station --episode 3

# All channels at once
python factory.py --all

# Test without uploading
python factory.py --channel kids_education --no-upload

# Run on schedule (all channels auto-schedule)
python factory.py --schedule
```

---

## Output Structure

```
output/
├── mystery_history/
│   ├── state.json                  ← tracks used topics
│   └── 20240101_100000/
│       ├── script.json
│       ├── narration_full.mp3
│       ├── video_longform.mp4      ← 1920×1080, 8-15 min
│       ├── video_shorts.mp4        ← 1080×1920, 58 seconds
│       └── thumbnail.jpg
├── scifi_stories/
│   ├── state.json                  ← tracks episode progress
│   └── ...
├── kids_education/
├── diy_tutorials/
└── pending_social_uploads/         ← TikTok/Instagram queue
```

---

## Monetization Timeline

### Month 1-3: Build Library
- 360 total videos across 4 channels
- Focus on SEO-optimized titles
- No monetization yet

### Month 3-6: Hit Thresholds
- Target: 1,000 subscribers + 4,000 watch hours per channel
- Kids channel gets monetized first (high CPM)
- History channel second (strong advertiser interest)

### Month 6+: Revenue Streams
| Revenue Stream | Est. Monthly |
|---------------|--------------|
| YouTube AdSense (4 channels) | $200-800 |
| YouTube Shorts Fund | $50-200 |
| Channel memberships | $100-300 |
| Affiliate links (DIY tools) | $50-200 |
| **Total** | **$400-1500/mo** |

---

## Smart TV Optimization (Long-form)
- Videos 10-20 min → higher session time on YouTube TV
- Episodic content → binge watching behavior
- "Watch later" friendly format

## Shorts/TikTok/Reels Strategy
- Same footage, auto-cropped to 9:16 vertical
- 58 seconds (just under 1-min algorithm sweet spot)
- Strong hook in first 2 seconds
- Caption always visible (auto-generated)

---

## Adding New Series (Sci-Fi)
Edit `channels/scifi_stories/series_list.yaml`:
```yaml
- id: "my_new_series"
  title: "My Series Title"
  premise: "Brief premise..."
  episodes:
    - ep: 1
      title: "Episode Name"
      hook: "Shocking hook line"
```

## Adding New Topics
- History: `channels/mystery_history/topics.yaml`
- Kids: `channels/kids_education/topics.yaml`
- DIY: `channels/diy_tutorials/topics.yaml`
