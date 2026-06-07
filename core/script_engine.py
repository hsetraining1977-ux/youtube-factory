"""
Universal script engine — generates scripts for any channel type.
Each channel has its own prompt template and output structure.
"""
import json
import anthropic
from pydantic import BaseModel

client = anthropic.Anthropic()


class Scene(BaseModel):
    scene_number: int
    duration_seconds: int
    narration: str
    visual_description: str
    on_screen_text: str
    shorts_clip: str | None = None   # 10-15s clip for Shorts version


class VideoScript(BaseModel):
    title: str
    description: str
    tags: list[str]
    hook: str                        # First 15 seconds
    scenes: list[Scene]
    cta: str
    thumbnail_prompt: str
    shorts_hook: str                 # 3-second hook for Shorts
    shorts_summary: str              # 58-second condensed version
    estimated_duration_seconds: int
    # Episodic only:
    series_id: str | None = None
    episode_number: int | None = None
    previous_recap: str | None = None
    next_episode_teaser: str | None = None


# ─── PROMPT TEMPLATES PER NICHE ───────────────────────────────

PROMPTS = {

    "mystery_history": {
        "system": """You are a YouTube narrator specializing in mysterious historical stories.
Your videos go viral because you blend:
- Shocking opening hooks that create instant curiosity
- Accurate historical facts presented dramatically
- Building tension and suspense throughout
- Satisfying reveals that make viewers want to share
Write in documentary style. Voice: authoritative, mysterious, serious.""",

        "user_template": """Create a complete YouTube video script about: {topic}

Return ONLY valid JSON:
{{
  "title": "Title with mystery + power words (50-60 chars)",
  "description": "200-word description with SEO keywords and hashtags",
  "tags": ["tag1",...up to 15 tags],
  "hook": "15-second shocking opening narration",
  "scenes": [
    {{
      "scene_number": 1,
      "duration_seconds": 90,
      "narration": "Full narration text (3-4 paragraphs, dramatic pacing)",
      "visual_description": "What footage to show (be specific: ancient ruins, old manuscripts, etc.)",
      "on_screen_text": "Key fact displayed on screen",
      "shorts_clip": "Most shocking 10-second excerpt from this scene"
    }}
  ],
  "cta": "Subscribe/like/comment call to action (15 seconds)",
  "thumbnail_prompt": "DALL-E 3 prompt for dramatic historical thumbnail",
  "shorts_hook": "3-second hook for 60-second Shorts version",
  "shorts_summary": "Complete 58-second narration for Shorts (condensed version)",
  "estimated_duration_seconds": 600
}}

Requirements: 7-9 scenes, 8-12 min total, build suspense, end with revelation."""
    },

    "episodic_scifi": {
        "system": """You are a sci-fi audio drama writer for YouTube.
Your episodic stories are binge-worthy because:
- Cinematic, immersive storytelling with rich descriptions
- Characters with real emotions and flaws
- Cliffhangers at episode ends that force clicking "next"
- Each episode reveals one truth while raising two questions
- Sound design notes (for text overlays) enhance immersion
Write as a professional audio drama script.""",

        "user_template": """Write Episode {episode_number} of "{series_title}".

Series premise: {series_premise}
Episode title: "{episode_title}"
Opening hook: "{episode_hook}"
{recap_section}

Return ONLY valid JSON:
{{
  "title": "Series Title - Ep {episode_number}: Episode Title",
  "description": "Episode description with series context and SEO",
  "tags": ["tags",...],
  "hook": "Cold open - first 15 seconds (no recap, straight into action)",
  "scenes": [
    {{
      "scene_number": 1,
      "duration_seconds": 120,
      "narration": "Full scene narration with dialogue and description. Use character names. Include [SOUND: ambient noise] cues.",
      "visual_description": "Space/sci-fi visual to overlay",
      "on_screen_text": "Episode/scene identifier or key dialogue line",
      "shorts_clip": "Most cinematic/shocking 10-second moment"
    }}
  ],
  "cta": "Subscribe for next episode - with cliffhanger tease",
  "thumbnail_prompt": "DALL-E 3: cinematic sci-fi scene for episode thumbnail",
  "shorts_hook": "3-second shocking line for Shorts",
  "shorts_summary": "58-second 'previously on + biggest moment' for Shorts",
  "estimated_duration_seconds": 720,
  "series_id": "{series_id}",
  "episode_number": {episode_number},
  "previous_recap": "30-second recap of previous episode (skip for ep 1)",
  "next_episode_teaser": "15-second teaser for next episode"
}}

Requirements: 8-10 scenes, 12-15 min, end on cliffhanger."""
    },

    "kids_edu": {
        "system": """You create YouTube content for children ages 4-10.
Your videos are beloved by kids AND parents because:
- Simple, clear language children understand
- Fun characters and relatable situations
- Educational content wrapped in engaging stories
- Repetition of key learning points
- Warm, encouraging tone that builds confidence
NEVER include: violence, scary content, complex adult topics.
Always end with a positive lesson or activity suggestion.""",

        "user_template": """Create a kids YouTube video about: {topic}

Return ONLY valid JSON:
{{
  "title": "Fun, curious title for kids (max 50 chars)",
  "description": "Parent-friendly description with educational value",
  "tags": ["kids", "children", "educational",...],
  "hook": "15-second exciting opening that grabs kids' attention",
  "scenes": [
    {{
      "scene_number": 1,
      "duration_seconds": 45,
      "narration": "Simple, fun narration. Short sentences. Use character names. Include [SONG] or [ANIMATION] cues.",
      "visual_description": "Bright animated visuals, simple and colorful",
      "on_screen_text": "Key word or number displayed in big colorful font",
      "shorts_clip": "Most fun/energetic 10-second moment"
    }}
  ],
  "cta": "Subscribe + ask parents to like - in fun kid-friendly way",
  "thumbnail_prompt": "DALL-E 3: bright colorful cartoon style, cute characters, no text",
  "shorts_hook": "3-second exciting question for kids",
  "shorts_summary": "58-second fun mini-lesson for Shorts",
  "estimated_duration_seconds": 420
}}

Requirements: 6-8 scenes, 6-8 min, simple language, fun characters, educational value."""
    },

    "diy_home": {
        "system": """You create practical DIY home repair/improvement tutorials for YouTube.
Your tutorials get 5-star reviews because:
- Clear step-by-step instructions anyone can follow
- Honest about difficulty level and time required
- List of exact tools and materials with approximate costs
- Safety warnings where needed
- Pro tips that save time and money
Tone: friendly neighbor who's really good at this stuff.""",

        "user_template": """Create a DIY tutorial YouTube video about: {topic}

Return ONLY valid JSON:
{{
  "title": "How-to title with benefit/time/cost (50-60 chars)",
  "description": "SEO description with tools list, difficulty, time estimate",
  "tags": ["diy", "how to",...],
  "hook": "15-second hook showing the problem + promise of easy fix",
  "scenes": [
    {{
      "scene_number": 1,
      "duration_seconds": 60,
      "narration": "Clear instruction narration. Mention exact steps. Include safety tips.",
      "visual_description": "Close-up of hands working, specific tool shots, before/after",
      "on_screen_text": "Step number + brief instruction (e.g., 'Step 2: Tighten valve')",
      "shorts_clip": "Most dramatic before/after moment or key tip"
    }}
  ],
  "cta": "Subscribe + comment your results + ask questions",
  "thumbnail_prompt": "DALL-E 3: before/after split image, home repair, professional quality",
  "shorts_hook": "3-second shocking problem or money-saving fact",
  "shorts_summary": "58-second complete quick-fix version for Shorts",
  "estimated_duration_seconds": 600
}}

Requirements: 6-9 scenes, 8-15 min. Include: tools list scene, safety warnings, pro tips."""
    }
}


def generate_script(niche: str, topic: str, episode_context: dict | None = None) -> VideoScript:
    """Generate a complete video script for the given channel niche."""
    template = PROMPTS[niche]

    if niche == "episodic_scifi" and episode_context:
        recap = ""
        if episode_context.get("episode_number", 1) > 1:
            recap = f'Previous episode summary: {episode_context.get("previous_summary", "")}'
        user_content = template["user_template"].format(
            episode_number=episode_context["episode_number"],
            series_title=episode_context["series_title"],
            series_premise=episode_context["series_premise"],
            episode_title=episode_context["episode_title"],
            episode_hook=episode_context["episode_hook"],
            series_id=episode_context["series_id"],
            recap_section=recap
        )
    else:
        user_content = template["user_template"].format(topic=topic)

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=4000,
        system=template["system"],
        messages=[{"role": "user", "content": user_content}]
    )

    data = json.loads(response.content[0].text)
    return VideoScript(**data)
