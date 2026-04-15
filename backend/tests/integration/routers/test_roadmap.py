"""
【Integrationテスト】ロードマップAPIエンドポイントのテスト
FastAPI TestClient + テスト用DB使用

認証が必要なエンドポイントのテストです。
auth_headers フィクスチャ（conftest.py 定義）を使って認証状態を再現します。
"""

import pytest


class TestRoadmapRequiresAuth:
    def test_create_roadmap_without_token(self, client):
        """認証なしでロードマップ生成を試みると401になること"""
        # 期待: 認証なしでは 401 または 403 が返る
        response = client.post(
            "/api/roadmaps",
            json={"goal": "AIエンジニアになりたい"},
        )
        assert response.status_code in (401, 403)

    def test_list_roadmaps_without_token(self, client):
        """認証なしでロードマップ一覧を取得しようとすると401になること"""
        # 期待: 認証なしでは 401 または 403 が返る
        response = client.get("/api/roadmaps")
        assert response.status_code in (401, 403)

    def test_get_roadmap_without_token(self, client):
        """認証なしで特定のロードマップを取得しようとすると401になること"""
        # 期待: 認証なしでは 401 または 403 が返る
        response = client.get("/api/roadmaps/1")
        assert response.status_code in (401, 403)

    def test_list_roadmaps_with_valid_token(self, client, auth_headers):
        """有効なトークンでロードマップ一覧を取得できること"""
        # 期待: 認証済みなら 200 が返る（空配列でも OK）
        response = client.get("/api/roadmaps", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)
