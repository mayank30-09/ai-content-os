"""AI response validation and JSON repair module for AI Content OS.

Extracts JSON substrings from markdown fences, repairs malformed syntax, and validates
payloads against Pydantic models.
"""

import json
import re
from typing import TypeVar

from loguru import logger
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)

class ReelScene(BaseModel):
    """Schema for individual scene in a Reel script."""
    timestamp: str
    spoken_text: str
    visual_cue: str

class ReelsScriptModel(BaseModel):
    """Schema for 30s Reel script."""
    hook: str
    body: list[ReelScene]
    call_to_action: str
    caption: str | None = ""
    hashtags: list[str] | None = []

class CarouselSlide(BaseModel):
    """Schema for individual slide in a Carousel breakdown."""
    slide_number: int | None = 1
    headline: str
    subtext: str | None = ""
    bullet_points: list[str] | None = []
    visual_prompt: str | None = ""

class CarouselModel(BaseModel):
    """Schema for multi-slide Carousel breakdown."""
    title_slide: CarouselSlide
    content_slides: list[CarouselSlide]
    cta_slide: CarouselSlide

class StoryFrame(BaseModel):
    """Schema for individual Story frame."""
    frame: int
    type: str
    text: str
    sticker_idea: str | None = ""

class StoriesModel(BaseModel):
    """Schema for sequential Story frames."""
    frames: list[StoryFrame]

class ImagePromptsModel(BaseModel):
    """Schema for text-to-image prompts list."""
    prompts: list[str]

class AIResponseParser:
    """Validator & repair engine for AI response text."""

    @staticmethod
    def extract_json_str(raw_text: str) -> str:
        """Extracts JSON block from markdown fences or bracket boundaries."""
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw_text, re.IGNORECASE)
        if match:
            return match.group(1).strip()

        start = raw_text.find("{")
        end = raw_text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return raw_text[start:end+1].strip()

        start_arr = raw_text.find("[")
        end_arr = raw_text.rfind("]")
        if start_arr != -1 and end_arr != -1 and end_arr > start_arr:
            return raw_text[start_arr:end_arr+1].strip()

        return raw_text.strip()

    @staticmethod
    def repair_json_str(json_str: str) -> str:
        """Repairs trailing commas in JSON strings."""
        return re.sub(r",\s*([}\]])", r"\1", json_str)

    @classmethod
    def parse_and_validate(cls, raw_text: str, schema_cls: type[T]) -> T:
        """Extracts, repairs, parses, and validates raw AI text against a Pydantic schema."""
        extracted = cls.extract_json_str(raw_text)
        repaired = cls.repair_json_str(extracted)

        try:
            parsed_dict = json.loads(repaired)
            if isinstance(parsed_dict, list) and issubclass(schema_cls, ImagePromptsModel):
                parsed_dict = {"prompts": parsed_dict}

            validated = schema_cls.model_validate(parsed_dict)
            logger.info(f"Successfully validated AI response against schema '{schema_cls.__name__}'")
            return validated
        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(f"AI response validation failed for schema '{schema_cls.__name__}': {e}")
            logger.debug(f"Raw response was:\n{raw_text}")
            raise ValueError(f"AI Output failed schema validation [{schema_cls.__name__}]: {str(e)}") from e

ai_parser = AIResponseParser()
