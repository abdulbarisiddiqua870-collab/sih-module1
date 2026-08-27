"""
Module 2 API — Compliance + AI Decision System
SIH26034 - AI Package/Label Compliance Checker

Run with:
    uvicorn app.main:app --reload
Then open http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI, HTTPException
from app.models.schemas import ProductData, ComplianceResult
from app.services.decision_engine import run_compliance_check

app = FastAPI(
    title="SIH26034 Module 2 - Compliance + AI Decision System",
    description=(
        "Rule-based, explainable compliance checker for packaged commodities "
        "under the Legal Metrology (Packaged Commodities) Rules, 2011. "
        "Prototype for evaluation purposes only."
    ),
    version="0.1.0",
)


@app.get("/")
def root():
    return {
        "service": "Module 2 - Compliance + AI Decision System",
        "status": "running",
        "docs": "/docs",
    }


@app.post("/analyze", response_model=ComplianceResult)
def analyze(product: ProductData):
    try:
        return run_compliance_check(product)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
