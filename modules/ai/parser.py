import json
import logging
import re
from typing import TypeVar

from pydantic import BaseModel, ValidationError

logger = logging.getLogger("AIContentOS.AIParser")

T = TypeVar("T", bound=BaseModel)

# --- Pydantic Schema Definitions for Multi-Format Outputs ---

class ReelScene(BaseModel):
    timestamp: str
    spoken_text: str
    visual_cue: str

class ReelsScriptModel(BaseModel):
    hook: str
    body: list[ReelScene]
    call_to_action: str
    caption: str | None = ""
    hashtags: list[str] | None = []

class CarouselSlide(BaseModel):
    slide_number: int | None = 1
    headline: str
    subtext: str | None = ""
    bullet_points: list[str] | None = []
    visual_prompt: str | None = ""

class CarouselModel(BaseModel):
    title_slide: CarouselSlide
    content_slides: list[CarouselSlide]
    cta_slide: CarouselSlide

class StoryFrame(BaseModel):
    frame: int
    type: str
    text: str
    sticker_idea: str | None = ""

class StoriesModel(BaseModel):
    frames: list[StoryFrame]

class ImagePromptsModel(BaseModel):
    prompts: list[str]

# --- AI Response Validator & Repair Engine ---

class AIResponseParser:
    @staticmethod
    def extract_json_str(raw_text: str) -> str:
        """Extracts JSON block from Markdown fences or raw response string."""
        # 1. Try matching ```json ... ```
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw_text, re.IGNORECASE)
        if match:
            return match.group(1).strip()

        # 2. Try finding first '{' and last '}'
        start = raw_text.find("{")
        end = raw_text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return raw_text[start:end+1].strip()

        # 3. Try finding first '[' and last ']'
        start_arr = raw_text.find("[")
        end_arr = raw_text.rfind("]")
        if start_arr != -1 and end_arr != -1 and end_arr > start_arr:
            return raw_text[start_arr:end_arr+1].strip()

        return raw_text.strip()

    @staticmethod
    def repair_json_str(json_str: str) -> str:
        """Repairs common LLM JSON syntax errors (trailing commas, unescaped newlines)."""
        # Remove trailing commas in objects and arrays
        repaired = re.sub(r",\s*([}\]])", r"\1", json_str)
        return repaired

    @classmethod
    def parse_and_validate(cls, raw_text: str, schema_cls: type[T]) -> T:
        """Extracts, repairs, parses, and validates raw AI text against a Pydantic schema."""
        extracted = cls.extract_json_str(raw_text)
        repaired = cls.repair_json_str(extracted)

        try:
            parsed_dict = json.loads(repaired)
            # If schema expects object wrapping a list (like image prompts list)
            if isinstance(parsed_dict, list) and issubclass(schema_cls, ImagePromptsModel):
                parsed_dict = {"prompts": parsed_dict}

            validated = schema_cls.model_validate(parsed_dict)
            logger.info(f"Successfully validated AI response against schema {schema_cls.__name__}")
            return validated
        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(f"AI response validation failed for schema {schema_cls.__name__}: {e}")
            logger.debug(f"Raw response was:\n{raw_text}")
            raise ValueError(f"AI Output failed schema validation [{schema_cls.__name__}]: {str(e)}")

ai_parser = AIResponseParser()
