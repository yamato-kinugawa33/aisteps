import pytest

from services.gemini import _extract_json


class TestExtractJson:
    def test_plain(self):
        raw = '{"goal": "エンジニア", "steps": []}'
        result = _extract_json(raw)
        assert result == {"goal": "エンジニア", "steps": []}

    def test_with_fence(self):
        raw = '```json\n{"goal": "エンジニア", "steps": []}\n```'
        result = _extract_json(raw)
        assert result == {"goal": "エンジニア", "steps": []}

    def test_with_fence_no_lang(self):
        raw = '```\n{"goal": "エンジニア", "steps": []}\n```'
        result = _extract_json(raw)
        assert result == {"goal": "エンジニア", "steps": []}

    def test_with_whitespace(self):
        raw = '  \n{"goal": "エンジニア", "steps": []}\n  '
        result = _extract_json(raw)
        assert result == {"goal": "エンジニア", "steps": []}

    def test_invalid_json(self):
        with pytest.raises(Exception):
            _extract_json("これはJSONではない")

    def test_empty_string(self):
        with pytest.raises(Exception):
            _extract_json("")
