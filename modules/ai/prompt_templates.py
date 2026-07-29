from jinja2 import Template

REELS_TEMPLATE = """
Role: Senior Social Media Strategist & Short-Form Video Producer.
Topic: {{ topic }}
Research Summary: {{ research_summary }}
User Brand Voice / Style Rules: {{ user_preferences }}

Generate a structured 30-Second Instagram Reel / TikTok Script in JSON format with keys:
{
  "hook": "0-3s high-impact visual & verbal hook",
  "body": [
    {"timestamp": "3-10s", "spoken_text": "...", "visual_cue": "..."},
    {"timestamp": "10-20s", "spoken_text": "...", "visual_cue": "..."}
  ],
  "call_to_action": "20-30s strong CTA",
  "caption": "Post caption",
  "hashtags": ["#tag1", "#tag2"]
}
Only output valid JSON.
"""

CAROUSEL_TEMPLATE = """
Role: Lead Content Designer & Visual Copywriter.
Topic: {{ topic }}
Research Summary: {{ research_summary }}
User Brand Voice / Style Rules: {{ user_preferences }}

Generate a 7-Slide Instagram Carousel breakdown in JSON format with keys:
{
  "title_slide": {"headline": "...", "subtext": "...", "visual_prompt": "..."},
  "content_slides": [
    {"slide_number": 2, "headline": "...", "bullet_points": ["..."], "visual_prompt": "..."},
    {"slide_number": 3, "headline": "...", "bullet_points": ["..."], "visual_prompt": "..."}
  ],
  "cta_slide": {"headline": "...", "subtext": "..."}
}
Only output valid JSON.
"""

STORIES_TEMPLATE = """
Role: Content Creator & Audience Engagement Specialist.
Topic: {{ topic }}
Research Summary: {{ research_summary }}

Generate 4 Instagram Stories frames in JSON format with keys:
{
  "frames": [
    {"frame": 1, "type": "Question Poll", "text": "...", "sticker_idea": "..."},
    {"frame": 2, "type": "Value Drop", "text": "..."},
    {"frame": 3, "type": "Behind The Scenes / Insight", "text": "..."},
    {"frame": 4, "type": "CTA / Link Sticker", "text": "..."}
  ]
}
Only output valid JSON.
"""

IMAGE_PROMPTS_TEMPLATE = """
Role: AI Art Director & Prompt Engineer.
Topic: {{ topic }}
Context: {{ research_summary }}

Generate 3 Midjourney v6 / FLUX text-to-image prompts for social media assets:
1. Cover Graphic Prompt
2. Abstract Conceptual Graphic Prompt
3. Minimalist Editorial Graphic Prompt
Output as a clean JSON list of strings.
"""

class PromptLibrary:
    @staticmethod
    def render_reels_prompt(topic: str, research_summary: str, user_preferences: str = "") -> str:
        return Template(REELS_TEMPLATE).render(
            topic=topic, research_summary=research_summary, user_preferences=user_preferences
        )

    @staticmethod
    def render_carousel_prompt(topic: str, research_summary: str, user_preferences: str = "") -> str:
        return Template(CAROUSEL_TEMPLATE).render(
            topic=topic, research_summary=research_summary, user_preferences=user_preferences
        )

    @staticmethod
    def render_stories_prompt(topic: str, research_summary: str) -> str:
        return Template(STORIES_TEMPLATE).render(topic=topic, research_summary=research_summary)

    @staticmethod
    def render_image_prompts(topic: str, research_summary: str) -> str:
        return Template(IMAGE_PROMPTS_TEMPLATE).render(topic=topic, research_summary=research_summary)

prompt_library = PromptLibrary()
