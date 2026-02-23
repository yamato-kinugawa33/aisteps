from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Roadmap
from schemas import RoadmapRequest, RoadmapResponse, RoadmapSummary
from services import gemini

router = APIRouter(prefix="/api/roadmaps", tags=["roadmaps"])


@router.post("", response_model=RoadmapResponse)
def create_roadmap(req: RoadmapRequest, db: Session = Depends(get_db)):
    try:
        initial_json, critique_text, final_json, model_name, input_tokens, output_tokens = gemini.run_pipeline(req.goal)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI生成エラー: {str(e)}")

    record = Roadmap(
        user_input=req.goal,
        initial_json=initial_json,
        critique=critique_text,
        final_text=None,
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
def list_roadmaps(db: Session = Depends(get_db)):
    return db.query(Roadmap).order_by(Roadmap.created_at.desc()).all()


@router.get("/{roadmap_id}", response_model=RoadmapResponse)
def get_roadmap(roadmap_id: int, db: Session = Depends(get_db)):
    record = db.get(Roadmap, roadmap_id)
    if not record:
        raise HTTPException(status_code=404, detail="Not found")
    return record
