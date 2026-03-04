"""
Trademark Risk Assessment API
FastAPI backend — 3-Tier Architecture (ML Similarity → Deterministic → LLM)

Endpoints:
- POST /api/analyze      - Analyze trademark (manual input)
- POST /api/analyze-pdf  - Upload PDF + full analysis
- POST /api/upload       - Upload and parse PDF only
- GET  /api/health       - Health check
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import tempfile
import os

# Import our modules
from risk_framework import (
    RiskFramework,
    TrademarkIssue,
    IssueCategory,
    RiskLevel,
)
from focused_analyzer import FocusedAnalyzer, FullAnalysisResult, MarkComparisonResult, IssueResult
from document_parser import DocumentParser
from tmep_knowledge import TMEP_SECTIONS, get_section

app = FastAPI(
    title="Trademark Risk Assessment API",
    description="AI-powered trademark risk analysis — 3-Tier Architecture with per-mark analysis and DuPont 13 factor coverage",
    version="3.0.0",
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components (Tier 1: sentence-transformers, Tier 2: deterministic, Tier 3: Gemini LLM)
risk_framework = RiskFramework()
analyzer = FocusedAnalyzer()
document_parser = DocumentParser()


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    """Request to analyze a trademark"""
    mark: str
    goods_services: str
    classes: List[int]
    prior_marks: Optional[List[Dict]] = []


class MarkComparisonResponse(BaseModel):
    """Per-mark confusion result"""
    prior_mark_name: str
    prior_mark_goods: str
    prior_mark_classes: List[int]
    prior_mark_reg_number: str
    is_similar: bool
    is_related_goods: bool
    confusion_risk: str
    reasoning: str
    key_factor: str
    tmep_section: str
    citation_text: str
    confidence: float
    name_contained: bool
    # 3-Tier Architecture metadata
    tier_resolved: str = ""         # "tier1_2" or "tier3"
    similarity_scores: Optional[Dict] = None  # Raw ML scores from Tier 1


class IssueResponse(BaseModel):
    """Non-confusion issue response"""
    category: str
    severity: str
    title: str
    description: str
    tmep_section: str
    citation_text: str
    recommendation: str
    confidence: float
    estimated_cost: str
    estimated_time: str


class RiskDimensionResponse(BaseModel):
    """Risk dimension response"""
    name: str
    weight: float
    score: float
    confidence: float
    explanation: str
    citations: List[str]


class AnalysisResponse(BaseModel):
    """Complete analysis response"""
    overall_risk_score: float
    overall_risk_level: str
    overall_confidence: float
    requires_human_review: bool

    rejection_likelihood: RiskDimensionResponse
    overcoming_difficulty: RiskDimensionResponse
    legal_precedent_strength: RiskDimensionResponse
    examiner_discretion: RiskDimensionResponse

    issues: List[IssueResponse]
    total_issues: int
    critical_issues: int

    primary_recommendation: str
    alternative_strategies: List[str]
    estimated_total_cost: str
    estimated_timeline: str

    trademark: str
    goods_services: str

    # NEW: per-mark breakdown (3-tier pipeline output)
    per_mark_results: List[MarkComparisonResponse]
    overall_confusion_risk: str
    highest_risk_mark: Optional[str]
    total_prior_marks_analyzed: int
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int


class PdfAnalysisResponse(AnalysisResponse):
    """Analysis response from PDF upload"""
    input_mode: str = "pdf"
    parsed_mark: str
    parsed_goods_services: str
    parsed_classes: List[int]
    parsed_prior_marks_count: int
    parsed_prior_marks_uspto: List[Dict]
    total_pdf_conflicts: int
    report_date: Optional[str] = None


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _risk_str_to_level(risk: str) -> RiskLevel:
    """Convert string risk level to RiskLevel enum."""
    mapping = {
        "HIGH": RiskLevel.HIGH,
        "MEDIUM": RiskLevel.MODERATE,
        "LOW": RiskLevel.LOW,
        "CRITICAL": RiskLevel.CRITICAL,
    }
    return mapping.get(risk.upper(), RiskLevel.MODERATE)


def _issue_category_from_type(issue_type: str) -> IssueCategory:
    """Map issue type string to IssueCategory."""
    mapping = {
        "descriptiveness": IssueCategory.DESCRIPTIVENESS,
        "specimen_deficiency": IssueCategory.SPECIMEN_DEFICIENCY,
        "filing_basis_issue": IssueCategory.BASIS_ISSUE,
        "identification_issue": IssueCategory.IDENTIFICATION_ISSUE,
        "likelihood_of_confusion": IssueCategory.LIKELIHOOD_CONFUSION,
        "genericness": IssueCategory.GENERICNESS,
        "deceptiveness": IssueCategory.PROCEDURAL,  # No dedicated enum — closest match
        "ownership_issue": IssueCategory.OWNERSHIP_ISSUE,
        "dilution": IssueCategory.LIKELIHOOD_CONFUSION,  # Dilution is related to confusion
    }
    return mapping.get(issue_type, IssueCategory.PROCEDURAL)


def _estimate_cost(severity: RiskLevel) -> str:
    cost_map = {
        RiskLevel.CRITICAL: "$5,000-10,000",
        RiskLevel.HIGH: "$3,000-6,000",
        RiskLevel.MODERATE: "$1,500-3,000",
        RiskLevel.LOW: "$500-1,500",
        RiskLevel.MINIMAL: "$0-500",
    }
    return cost_map.get(severity, "$1,000-2,000")


def _estimate_time(severity: RiskLevel) -> str:
    time_map = {
        RiskLevel.CRITICAL: "12-18 months",
        RiskLevel.HIGH: "9-12 months",
        RiskLevel.MODERATE: "6-9 months",
        RiskLevel.LOW: "3-6 months",
        RiskLevel.MINIMAL: "1-3 months",
    }
    return time_map.get(severity, "6-9 months")


def _parse_cost(cost_str: str) -> int:
    try:
        costs = [int(c.replace("$", "").replace(",", "")) for c in cost_str.split("-")]
        return sum(costs) // len(costs)
    except Exception:
        return 2000


def _parse_time(time_str: str) -> int:
    try:
        times = [int(t) for t in time_str.replace("months", "").split("-")]
        return sum(times) // len(times)
    except Exception:
        return 6


def _calculate_total_cost(issues: List[TrademarkIssue]) -> str:
    total = sum(_parse_cost(i.estimated_cost) for i in issues)
    return f"${total:,}-${int(total * 1.5):,}"


def _calculate_total_timeline(issues: List[TrademarkIssue]) -> str:
    max_time = max([_parse_time(i.estimated_time) for i in issues]) if issues else 6
    return f"{max_time}-{max_time + 3} months"


def _dim_to_response(dim) -> RiskDimensionResponse:
    return RiskDimensionResponse(
        name=dim.name,
        weight=dim.weight,
        score=dim.score,
        confidence=dim.confidence,
        explanation=dim.explanation,
        citations=dim.citations,
    )


def _mark_result_to_response(r: MarkComparisonResult) -> MarkComparisonResponse:
    return MarkComparisonResponse(
        prior_mark_name=r.prior_mark_name,
        prior_mark_goods=r.prior_mark_goods,
        prior_mark_classes=r.prior_mark_classes,
        prior_mark_reg_number=r.prior_mark_reg_number,
        is_similar=r.is_similar,
        is_related_goods=r.is_related_goods,
        confusion_risk=r.confusion_risk,
        reasoning=r.reasoning,
        key_factor=r.key_factor,
        tmep_section=r.tmep_section,
        citation_text=r.citation_text,
        confidence=r.confidence,
        name_contained=r.name_contained,
        tier_resolved=r.tier_resolved,
        similarity_scores=r.similarity_scores,
    )


# ---------------------------------------------------------------------------
# Core analysis pipeline (shared by /api/analyze and /api/analyze-pdf)
# ---------------------------------------------------------------------------

async def _run_analysis_pipeline(
    mark: str,
    goods_services: str,
    classes: List[int],
    prior_marks: List[Dict],
) -> dict:
    """
    Run the full analysis pipeline and return a dict ready for AnalysisResponse.

    Pipeline:
    1. FocusedAnalyzer.run_full_analysis() — per-mark + other issues
    2. Convert to TrademarkIssues for the risk framework
    3. Calculate risk dimensions
    4. Generate recommendations
    """

    # Step 1: Focused analysis (3-tier pipeline: ML → Deterministic → LLM)
    print(f"📋 Running focused analysis for: {mark}")
    full_result: FullAnalysisResult = await analyzer.run_full_analysis(
        mark=mark,
        goods_services=goods_services,
        classes=classes,
        prior_marks=prior_marks,
    )

    # Step 2: Convert to TrademarkIssues for risk framework
    trademark_issues: List[TrademarkIssue] = []

    # Add confusion issue (aggregated from per-mark results)
    if full_result.per_mark_results:
        confusion_severity = _risk_str_to_level(full_result.overall_confusion_risk)
        # If any HIGH marks with name containment → CRITICAL
        critical_marks = [r for r in full_result.per_mark_results
                         if r.confusion_risk == "HIGH" and r.name_contained]
        if critical_marks:
            confusion_severity = RiskLevel.CRITICAL

        # Build description from top risk marks (deduplicated by name)
        high_marks = [r for r in full_result.per_mark_results if r.confusion_risk == "HIGH"]
        desc_parts = []
        seen_names = set()
        for r in high_marks:
            if r.prior_mark_name in seen_names:
                continue
            seen_names.add(r.prior_mark_name)
            # Truncate reasoning at word boundary — 350 chars gives full thoughts
            reasoning = r.reasoning[:350]
            if len(r.reasoning) > 350:
                reasoning = reasoning[:reasoning.rfind(' ')] + '...'
            desc_parts.append(f"{r.prior_mark_name} (§{r.tmep_section}): {reasoning}")
            if len(desc_parts) >= 3:  # Top 3 marks — rest visible in per-mark dropdown
                break
        confusion_desc = (
            f"Analyzed {full_result.total_prior_marks_analyzed} prior marks individually. "
            f"Found {full_result.high_risk_count} HIGH risk, "
            f"{full_result.medium_risk_count} MEDIUM risk, "
            f"{full_result.low_risk_count} LOW risk. "
        )
        if desc_parts:
            confusion_desc += "Top risks: " + "; ".join(desc_parts)

        section_data = get_section("1207.01")
        trademark_issues.append(TrademarkIssue(
            category=IssueCategory.LIKELIHOOD_CONFUSION,
            severity=confusion_severity,
            title="Likelihood of Confusion Analysis",
            description=confusion_desc,
            tmep_section="1207.01",
            citation_text=section_data["citation_text"] if section_data else "",
            recommendation=(
                "HIGH RISK: Multiple confusingly similar prior marks found. "
                "Consider modifying the mark or conducting a comprehensive clearance search."
                if confusion_severity in (RiskLevel.CRITICAL, RiskLevel.HIGH)
                else "Monitor identified prior marks during prosecution."
            ),
            confidence=max(r.confidence for r in full_result.per_mark_results) if full_result.per_mark_results else 0.5,
            estimated_cost=_estimate_cost(confusion_severity),
            estimated_time=_estimate_time(confusion_severity),
        ))

    # Add non-confusion issues
    for issue_result in full_result.other_issues:
        severity = _risk_str_to_level(issue_result.risk_level)
        category = _issue_category_from_type(issue_result.issue_type)
        trademark_issues.append(TrademarkIssue(
            category=category,
            severity=severity,
            title=issue_result.title,
            description=issue_result.description,
            tmep_section=issue_result.tmep_section,
            citation_text=issue_result.citation_text,
            recommendation=issue_result.recommendation,
            confidence=issue_result.confidence,
            estimated_cost=_estimate_cost(severity),
            estimated_time=_estimate_time(severity),
        ))

    # Step 3: Calculate risk dimensions
    enriched_prior_marks = []
    for pm in (prior_marks or []):
        pm_copy = dict(pm)
        pm_name = (pm_copy.get("name") or pm_copy.get("mark") or "").lower().strip()
        pm_name_norm = pm_name.replace(" ", "")
        mark_norm = mark.lower().strip().replace(" ", "")
        pm_copy["name_contained"] = bool(pm_name_norm and (pm_name_norm in mark_norm or mark_norm in pm_name_norm))
        enriched_prior_marks.append(pm_copy)

    rejection = risk_framework.assess_rejection_likelihood(
        issues=trademark_issues,
        similar_marks=enriched_prior_marks,
        tmep_evidence=[{"section": i.tmep_section} for i in trademark_issues],
    )
    overcoming = risk_framework.assess_overcoming_difficulty(
        issues=trademark_issues,
        estimated_costs={i.category.value: _parse_cost(i.estimated_cost) for i in trademark_issues},
        estimated_times={i.category.value: _parse_time(i.estimated_time) for i in trademark_issues},
    )
    precedent = risk_framework.assess_legal_precedent(
        tmep_sections=[{"section": i.tmep_section, "category": "substantive"} for i in trademark_issues],
        case_law=[],
        third_party_registrations=[],
    )
    discretion = risk_framework.assess_examiner_discretion(
        issues=trademark_issues,
        subjective_elements=["commercial impression", "suggestiveness"],
    )

    # Step 4: Overall risk
    dimensions = {
        "rejection_likelihood": rejection,
        "overcoming_difficulty": overcoming,
        "legal_precedent": precedent,
        "examiner_discretion": discretion,
    }
    overall_score, overall_confidence = risk_framework.calculate_overall_score(dimensions)
    overall_level = risk_framework.determine_risk_level(overall_score)
    needs_review = risk_framework.requires_human_review(overall_confidence)

    # Step 5: Recommendations
    primary_rec, alt_strategies = risk_framework.generate_recommendations(
        overall_level, trademark_issues, dimensions
    )

    # Build response dict
    return {
        "overall_risk_score": overall_score,
        "overall_risk_level": overall_level.value,
        "overall_confidence": overall_confidence,
        "requires_human_review": needs_review,
        "rejection_likelihood": _dim_to_response(rejection),
        "overcoming_difficulty": _dim_to_response(overcoming),
        "legal_precedent_strength": _dim_to_response(precedent),
        "examiner_discretion": _dim_to_response(discretion),
        "issues": [
            IssueResponse(
                category=i.category.value,
                severity=i.severity.value,
                title=i.title,
                description=i.description,
                tmep_section=i.tmep_section,
                citation_text=i.citation_text,
                recommendation=i.recommendation,
                confidence=i.confidence,
                estimated_cost=i.estimated_cost,
                estimated_time=i.estimated_time,
            )
            for i in trademark_issues
        ],
        "total_issues": len(trademark_issues),
        "critical_issues": sum(1 for i in trademark_issues if i.severity == RiskLevel.CRITICAL),
        "primary_recommendation": primary_rec,
        "alternative_strategies": alt_strategies,
        "estimated_total_cost": _calculate_total_cost(trademark_issues),
        "estimated_timeline": _calculate_total_timeline(trademark_issues),
        "trademark": mark,
        "goods_services": goods_services,
        # Per-mark breakdown
        "per_mark_results": [_mark_result_to_response(r) for r in full_result.per_mark_results],
        "overall_confusion_risk": full_result.overall_confusion_risk,
        "highest_risk_mark": full_result.highest_risk_mark,
        "total_prior_marks_analyzed": full_result.total_prior_marks_analyzed,
        "high_risk_count": full_result.high_risk_count,
        "medium_risk_count": full_result.medium_risk_count,
        "low_risk_count": full_result.low_risk_count,
    }


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    return {
        "service": "Trademark Risk Assessment API",
        "version": "3.0.0",
        "architecture": "3-Tier (ML Similarity → Deterministic → LLM)",
        "status": "operational",
    }


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "3.0.0",
        "architecture": "3-tier",
        "tiers": {
            "tier1": "ML Probabilistic (phonetic/semantic/visual via sentence-transformers)",
            "tier2": "Deterministic Screening (rule-based pass/fail)",
            "tier3": "LLM Analysis (Gemini — nuanced judgment)",
        },
        "components": {
            "similarity_engine": "operational (Tier 1 + 2)",
            "focused_analyzer": "operational (Tier 3 + orchestration)",
            "risk_framework": "operational",
            "document_parser": "operational",
            "tmep_knowledge": f"{len(TMEP_SECTIONS)} sections loaded",
        },
        "anti_hallucination": {
            "method": "per-mark analysis with hardcoded TMEP knowledge",
            "max_context_per_call": "~500 tokens",
            "citation_validation": True,
        },
    }


@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze_trademark(request: AnalyzeRequest):
    """
    Analyze trademark application for registration risks.

    3-Tier Architecture:
    1. Tier 1: ML similarity (phonetic/semantic/visual) screens all prior marks
    2. Tier 2: Deterministic rules filter clear-cut cases (no LLM needed)
    3. Tier 3: Gemini LLM for ambiguous marks (~200-500 tokens context)
    4. Citations validated against 26 known TMEP sections (all 13 DuPont factors)
    """
    result = await _run_analysis_pipeline(
        mark=request.mark,
        goods_services=request.goods_services,
        classes=request.classes,
        prior_marks=request.prior_marks or [],
    )
    return AnalysisResponse(**result)


@app.post("/api/upload")
async def upload_report(file: UploadFile = File(...)):
    """Upload and parse trademark search report PDF (parse only, no analysis)."""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        content = await file.read()
        temp_file.write(content)
        temp_path = temp_file.name

    try:
        parsed_report = document_parser.parse_pdf_report(temp_path)
        return {
            "mark": parsed_report.application.mark,
            "classes": parsed_report.application.classes,
            "goods_services": (
                parsed_report.application.goods_services[0]
                if parsed_report.application.goods_services
                else ""
            ),
            "prior_marks": {
                "uspto": [
                    {
                        "mark": m.mark,
                        "registration": m.registration_number,
                        "status": m.status,
                        "similarity": m.similarity_score,
                    }
                    for m in parsed_report.prior_marks_uspto
                ],
                "state": len(parsed_report.prior_marks_state),
                "common_law": len(parsed_report.prior_marks_common_law),
                "domains": len(parsed_report.prior_marks_domains),
            },
            "total_conflicts": parsed_report.total_conflicts,
            "report_date": parsed_report.report_date,
        }
    finally:
        os.unlink(temp_path)


@app.post("/api/analyze-pdf", response_model=PdfAnalysisResponse)
async def analyze_pdf(file: UploadFile = File(...)):
    """
    Upload a PDF trademark report and run FULL focused analysis on it.

    This endpoint:
    1. Parses the PDF to extract mark, goods/services, classes, prior marks
    2. Runs 3-tier analysis (ML similarity → deterministic screening → Gemini LLM)
    3. Returns analysis results + parsed PDF metadata
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        content = await file.read()
        temp_file.write(content)
        temp_path = temp_file.name

    try:
        # Step 1: Parse PDF
        print(f"📄 Parsing uploaded PDF: {file.filename}")
        parsed_report = document_parser.parse_pdf_report(temp_path)

        mark = parsed_report.application.mark
        # Combine ALL goods/services descriptions
        goods_services = "; ".join(parsed_report.application.goods_services) if parsed_report.application.goods_services else "General goods and services"
        classes = parsed_report.application.classes or [0]

        # Build prior marks list — prioritize USPTO (the numbered list in the report)
        # Only use common law / domain as fallback if no USPTO marks found
        if parsed_report.prior_marks_uspto:
            all_prior_marks = parsed_report.prior_marks_uspto
        else:
            all_prior_marks = (
                parsed_report.prior_marks_state +
                parsed_report.prior_marks_common_law +
                parsed_report.prior_marks_domains
            )
        prior_marks = [
            {
                "name": m.mark,
                "goods_services": m.goods_services or "",
                "classes": m.classes or [],
                "registration": m.registration_number or "",
                "source": m.source or "Unknown",
            }
            for m in all_prior_marks
        ]

        print(f"   Mark: {mark}")
        print(f"   Goods: {goods_services}")
        print(f"   Classes: {classes}")
        print(f"   Prior marks: {len(prior_marks)} (USPTO: {len(parsed_report.prior_marks_uspto)})")

        # Step 2: Run focused analysis
        result = await _run_analysis_pipeline(
            mark=mark,
            goods_services=goods_services,
            classes=classes,
            prior_marks=prior_marks,
        )

        # Step 3: Build PDF-specific response
        prior_marks_response = [
            {
                "mark": m.mark,
                "registration": m.registration_number,
                "status": m.status,
                "similarity": m.similarity_score,
                "source": m.source,
            }
            for m in all_prior_marks
        ]

        return PdfAnalysisResponse(
            **result,
            input_mode="pdf",
            parsed_mark=mark,
            parsed_goods_services=goods_services,
            parsed_classes=classes,
            parsed_prior_marks_count=parsed_report.total_conflicts,
            parsed_prior_marks_uspto=prior_marks_response,
            total_pdf_conflicts=parsed_report.total_conflicts,
            report_date=parsed_report.report_date,
        )

    finally:
        os.unlink(temp_path)


if __name__ == "__main__":
    import uvicorn

    print("🚀 Starting Trademark Risk Assessment API v3.0...")
    print("📍 Server: http://localhost:8000")
    print("📚 Docs: http://localhost:8000/docs")
    print("🛡️  Architecture: 3-Tier (ML → Deterministic → LLM)")
    print(f"📚 TMEP Knowledge: 26 sections covering all 13 DuPont factors")
    uvicorn.run(app, host="0.0.0.0", port=8000)
