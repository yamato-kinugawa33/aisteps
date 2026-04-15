"""
【E2Eテスト】ブラウザ操作によるシナリオテスト（Playwright）
NOTE: このテストはPlaywrightが必要です。ローカル環境でのみ実行してください。
実行コマンド: uv run pytest tests/e2e/ --browser chromium
"""

import pytest


@pytest.mark.skip(reason="E2Eテストはplaywright環境が必要です")
class TestUserRegistration:
    def test_successful_registration(self, page):
        """新規登録フォームで正常に登録できること"""
        # 期待: /registerページでフォーム入力→送信→/にリダイレクト
        pass

    def test_registration_with_existing_email(self, page):
        """既存メールアドレスで登録するとエラーが表示されること"""
        # 期待: エラーメッセージが表示される
        pass


@pytest.mark.skip(reason="E2Eテストはplaywright環境が必要です")
class TestLoginLogout:
    def test_successful_login(self, page):
        """正しい認証情報でログインできること"""
        # 期待: /loginで入力→送信→/にリダイレクト
        pass

    def test_login_with_wrong_password(self, page):
        """間違ったパスワードでエラーが表示されること"""
        # 期待: エラーメッセージが表示される
        pass

    def test_logout(self, page):
        """ログアウトボタンでログアウトできること"""
        # 期待: /loginにリダイレクト
        pass


@pytest.mark.skip(reason="E2Eテストはplaywright環境が必要です")
class TestProtectedPageAccess:
    def test_unauthenticated_redirect_to_login(self, page):
        """未認証で/にアクセスすると/loginにリダイレクトされること"""
        # 期待: /loginにリダイレクト
        pass
