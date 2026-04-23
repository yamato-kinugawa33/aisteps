import json
import os
import re
from pathlib import Path

import yaml
from google import genai

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set")
        _client = genai.Client(api_key=api_key)
    return _client

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
with open(PROMPTS_DIR / "config.yaml", encoding="utf-8") as f:
    _config = yaml.safe_load(f)

MODEL = _config["model"]


def _load(name: str) -> str:
    return (PROMPTS_DIR / _config["prompts"][name]["file"]).read_text(encoding="utf-8")


INITIAL_PROMPT = _load("initial")
CRITIQUE_PROMPT = _load("critique")
REFINE_PROMPT = _load("refine")


def _extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text.strip())


def _tokens(response) -> tuple[int, int]:
    usage = response.usage_metadata
    return (usage.prompt_token_count or 0), (usage.candidates_token_count or 0)


def run_pipeline(goal: str) -> tuple[dict, str, dict, str, int, int]:
    """
    Returns:
        (initial_json, critique_text, final_json, model_name,
         total_input_tokens, total_output_tokens)
    """
    client = _get_client()
    r1 = client.models.generate_content(
        model=MODEL, contents=INITIAL_PROMPT.format(goal=goal)
    )
    initial = _extract_json(r1.text)
    in1, out1 = _tokens(r1)

    r2 = client.models.generate_content(
        model=MODEL,
        contents=CRITIQUE_PROMPT.format(
            roadmap_json=json.dumps(initial, ensure_ascii=False, indent=2)
        ),
    )
    critique_text = r2.text.strip()
    in2, out2 = _tokens(r2)

    r3 = client.models.generate_content(
        model=MODEL,
        contents=REFINE_PROMPT.format(
            roadmap_json=json.dumps(initial, ensure_ascii=False, indent=2),
            critique=critique_text,
        ),
    )
    final = _extract_json(r3.text)
    in3, out3 = _tokens(r3)

    return initial, critique_text, final, MODEL, in1 + in2 + in3, out1 + out2 + out3
