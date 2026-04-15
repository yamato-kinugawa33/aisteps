from datetime import datetime

import pytest
from pydantic import ValidationError

from schemas.roadmap import RoadmapJson, RoadmapRequest, RoadmapResponse, RoadmapStep


class TestRoadmapRequest:
    def test_valid(self):
        req = RoadmapRequest(goal="エンジニアになる")
        assert req.goal == "エンジニアになる"

    def test_missing_goal(self):
        with pytest.raises(ValidationError):
            RoadmapRequest()


class TestRoadmapStep:
    def test_valid(self):
        step = RoadmapStep(
            order=1,
            title="基礎学習",
            description="Pythonを学ぶ",
            skills=["Python", "Git"],
            duration="1ヶ月",
        )
        assert step.order == 1
        assert len(step.skills) == 2


class TestRoadmapJson:
    def test_valid(self):
        data = RoadmapJson(
            goal="エンジニアになる",
            steps=[
                RoadmapStep(
                    order=1,
                    title="基礎",
                    description="学ぶ",
                    skills=["Python"],
                    duration="1ヶ月",
                )
            ],
        )
        assert data.goal == "エンジニアになる"
        assert len(data.steps) == 1

    def test_empty_steps(self):
        data = RoadmapJson(goal="エンジニアになる", steps=[])
        assert data.steps == []


class TestRoadmapResponse:
    def test_valid(self):
        resp = RoadmapResponse(
            id=1,
            user_input="エンジニアになる",
            initial_json={"goal": "test"},
            critique="改善点あり",
            final_json={"goal": "test"},
            model_name="gemini-2.5-flash",
            input_tokens=100,
            output_tokens=200,
            created_at=datetime(2026, 1, 1),
        )
        assert resp.id == 1

    def test_nullable_fields(self):
        resp = RoadmapResponse(
            id=1,
            user_input="エンジニアになる",
            initial_json=None,
            critique=None,
            final_json=None,
            model_name=None,
            input_tokens=None,
            output_tokens=None,
            created_at=datetime(2026, 1, 1),
        )
        assert resp.initial_json is None
