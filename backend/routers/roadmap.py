"""
routers/roadmap.py

ロードマップ生成・取得のAPIエンドポイントを定義するファイルです。

【変更点】
- 全エンドポイントに認証ガード（get_current_user）を追加しました。
  未認証のリクエストには 401 が返るようになりました。
- エラーレスポンスを改善: 内部エラー情報をレスポンスに含めないようにしました。
  （セキュリティ仕様書 T11 対策: スタックトレースや内部情報の漏洩防止）
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.dependencies import get_current_user
from db.database import get_db
from models.roadmap import Roadmap
from models.user import User
from schemas.roadmap import RoadmapRequest, RoadmapResponse, RoadmapSummary
from services import gemini

# エラーログをサーバーログに記録するためのロガー
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/roadmaps", tags=["roadmaps"])


@router.post("", response_model=RoadmapResponse)
def create_roadmap(
    req: RoadmapRequest,
    db: Session = Depends(get_db),
    # current_user: 認証済みユーザー（Depends により自動取得）
    # 未認証の場合はここで 401 エラーが発生してエンドポイント処理に入らない
    current_user: User = Depends(get_current_user),
):
    """
    ロードマップを生成するエンドポイント。認証必須。

    リクエストボディ:
        goal: キャリア目標（テキスト）

    成功レスポンス (200):
        生成されたロードマップ情報

    エラーレスポンス:
        401/403: 認証トークンが無効または未提供
        500: AI生成中のエラー（詳細はサーバーログに記録）
    """
    try:
        (
            initial_json,
            critique_text,
            final_json,
            model_name,
            input_tokens,
            output_tokens,
        ) = gemini.run_pipeline(req.goal)
    except Exception as e:
        # エラーの詳細はサーバーログに記録するが、レスポンスには含めない（情報漏洩防止）
        logger.error(
            "AI pipeline error for user_id=%d: %s", current_user.id, e, exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="ロードマップ生成中にエラーが発生しました",
        )

    record = Roadmap(
        user_input=req.goal,
        initial_json=initial_json,
        critique=critique_text,
        final_json=final_json,
        model_name=model_name,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("", response_model=list[RoadmapSummary])
def list_roadmaps(
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),  # 認証必須（結果は使わない）
):
    """
    ロードマップ一覧を取得するエンドポイント。認証必須。

    成功レスポンス (200):
        ロードマップのサマリー一覧（作成日時降順）

    エラーレスポンス:
        401/403: 認証トークンが無効または未提供
    """
    return db.query(Roadmap).order_by(Roadmap.created_at.desc()).all()


@router.get("/{roadmap_id}", response_model=RoadmapResponse)
def get_roadmap(
    roadmap_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),  # 認証必須（結果は使わない）
):
    """
    指定IDのロードマップを取得するエンドポイント。認証必須。

    パスパラメータ:
        roadmap_id: 取得するロードマップのID

    成功レスポンス (200):
        ロードマップの詳細情報

    エラーレスポンス:
        401/403: 認証トークンが無効または未提供
        404: 指定IDのロードマップが存在しない
    """
    record = db.get(Roadmap, roadmap_id)
    if not record:
        raise HTTPException(status_code=404, detail="ロードマップが見つかりません")
    return record
