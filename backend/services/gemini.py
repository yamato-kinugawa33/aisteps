import json
import os
import re
from google import genai
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "gemini-2.5-flash"

INITIAL_PROMPT = """\
あなたはキャリアアドバイザーです。
ユーザーが「{goal}」を達成するためのキャリアロードマップを作成してください。

以下のJSON形式のみで回答してください。説明文や```json```などのマークダウンは不要です。

{{
  "goal": "やりたいこと（文字列）",
  "steps": [
    {{
      "order": 1,
      "title": "ステップ名",
      "description": "このステップで何をするかの説明",
      "skills": ["スキル1", "スキル2"],
      "duration": "目安期間（例: 1ヶ月）"
    }}
  ]
}}

ステップは4〜7個程度、現実的かつ具体的に作成してください。
"""

CRITIQUE_PROMPT = """\
以下のキャリアロードマップを批評してください。

{roadmap_json}

以下の観点で問題点・改善点を具体的に指摘してください:
- ステップの抜け漏れ
- 期間設定の妥当性
- スキルの具体性・過不足
- ステップ間のつながりや論理的な順序
- 全体的なバランス

批評は日本語で、箇条書きで記述してください。
"""

REFINE_PROMPT = """\
以下のキャリアロードマップと批評を踏まえて、改善版のロードマップを作成してください。

【元のロードマップ】
{roadmap_json}

【批評】
{critique}

改善版は以下のJSON形式のみで回答してください。説明文や```json```などのマークダウンは不要です。

{{
  "goal": "やりたいこと（文字列）",
  "steps": [
    {{
      "order": 1,
      "title": "ステップ名",
      "description": "このステップで何をするかの説明",
      "skills": ["スキル1", "スキル2"],
      "duration": "目安期間（例: 1ヶ月）"
    }}
  ]
}}
"""


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
    Returns: (initial_json, critique_text, final_json, model_name, total_input_tokens, total_output_tokens)
    """
    r1 = client.models.generate_content(model=MODEL, contents=INITIAL_PROMPT.format(goal=goal))
    initial = _extract_json(r1.text)
    in1, out1 = _tokens(r1)

    r2 = client.models.generate_content(
        model=MODEL,
        contents=CRITIQUE_PROMPT.format(roadmap_json=json.dumps(initial, ensure_ascii=False, indent=2))
    )
    critique_text = r2.text.strip()
    in2, out2 = _tokens(r2)

    r3 = client.models.generate_content(
        model=MODEL,
        contents=REFINE_PROMPT.format(
            roadmap_json=json.dumps(initial, ensure_ascii=False, indent=2),
            critique=critique_text,
        )
    )
    final = _extract_json(r3.text)
    in3, out3 = _tokens(r3)

    return initial, critique_text, final, MODEL, in1 + in2 + in3, out1 + out2 + out3
