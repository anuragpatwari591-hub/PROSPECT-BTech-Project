import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Analysis
from ..pdf_report import generate_pdf_report

router = APIRouter(prefix="/api", tags=["report"])


@router.get("/report/{analysis_id}")
def download_report(analysis_id: int, db: Session = Depends(get_db)):
    record = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Analysis not found.")

    analysis = {
        "repo_full_name": record.repo_full_name,
        "repo_url": record.repo_url,
        "risk_score": record.risk_score,
        "health_score": record.health_score,
        "classification": record.classification,
        "factors": json.loads(record.factors_json),
        "recommendations": json.loads(record.recommendations_json),
        "metrics": json.loads(record.metrics_json),
        "stars": record.stars,
        "forks": record.forks,
    }

    pdf_bytes = generate_pdf_report(analysis)
    filename = f"prospect-report-{record.repo_full_name.replace('/', '-')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
