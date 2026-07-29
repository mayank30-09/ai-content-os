from modules.ai.parser import ReelsScriptModel, ai_parser


def test_extract_json_str_markdown():
    raw_markdown = """
    Here is the requested output:
    ```json
    {
      "hook": "Stop wasting time writing copy!",
      "body": [
        {"timestamp": "0-10s", "spoken_text": "Use AI Content OS", "visual_cue": "Screen recording"}
      ],
      "call_to_action": "Follow for more!"
    }
    ```
    Enjoy!
    """
    extracted = ai_parser.extract_json_str(raw_markdown)
    assert extracted.startswith("{") and extracted.endswith("}")

def test_repair_json_trailing_commas():
    malformed_json = """
    {
      "hook": "Test Hook",
      "body": [
        {"timestamp": "0-5s", "spoken_text": "Text", "visual_cue": "Visual",}
      ],
      "call_to_action": "CTA",
    }
    """
    validated = ai_parser.parse_and_validate(malformed_json, ReelsScriptModel)
    assert validated.hook == "Test Hook"
    assert len(validated.body) == 1
    assert validated.call_to_action == "CTA"
