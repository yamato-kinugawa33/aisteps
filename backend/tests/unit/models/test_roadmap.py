from models.roadmap import Roadmap


class TestRoadmapModel:
    def test_tablename(self):
        assert Roadmap.__tablename__ == "roadmaps"

    def test_columns_exist(self):
        columns = {c.name for c in Roadmap.__table__.columns}
        expected = {
            "id",
            "user_input",
            "initial_json",
            "critique",
            "final_json",
            "model_name",
            "input_tokens",
            "output_tokens",
            "created_at",
        }
        assert expected == columns
