"""
Trademark Risk Assessment API
FastAPI backend integrating RAG analyzer, risk framework, and document parser

Endpoints:
- POST /api/analyze - Analyze trademark application
- POST /api/upload - Upload and parse trademark report
- GET /api/health - Health check
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import tempfile
import os
from pathlib import Path

# Import our modules
from risk_framework import (
    RiskFramework, 
    RiskAssessment, 
    TrademarkIssue,
    IssueCategory,
    RiskLevel
)
from rag_analyzer import RAGAnalyzer, AnalysisResult
from document_parser import DocumentParser, TrademarkApplication, ParsedReport

app = FastAPI(
    title="Trademark Risk Assessment API",
    description="AI-powered trademark risk analysis using RAG and zero-hallucination methodology",
    version="1.0.0"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
risk_framework = RiskFramework()
rag_analyzer = RAGAnalyzer()
document_parser = DocumentParser()

# Request/Response Models
class AnalyzeRequest(BaseModel):
    """Request to analyze a trademark"""
    mark: str
    goods_services: str
    classes: List[int]
    prior_marks: Optional[List[Dict]] = []
    
class IssueResponse(BaseModel):
    """Trademark issue response"""
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

class PdfAnalysisResponse(AnalysisResponse):
    """Analysis response from PDF upload — includes parsed PDF metadata"""
    input_mode: str = "pdf"
    parsed_mark: str
    parsed_goods_services: str
    parsed_classes: List[int]
    parsed_prior_marks_count: int
    parsed_prior_marks_uspto: List[Dict]
    total_pdf_conflicts: int
    report_date: Optional[str] = None

# API Endpoints

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Trademark Risk Assessment API",
        "status": "operational",
        "version": "1.0.0"
    }

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    
    # Check if RAG analyzer is working
    try:
        # Quick test query
        test_contexts = rag_analyzer.retrieve_relevant_sections("test", k=1)
        rag_status = "operational" if test_contexts else "degraded"
    except Exception as e:
        rag_status = f"error: {str(e)}"
    
    return {
        "status": "healthy",
        "components": {
            "risk_framework": "operational",
            "rag_analyzer": rag_status,
            "document_parser": "operational",
            "vector_db": "operational" if rag_analyzer.index.ntotal > 0 else "error"
        },
        "vector_db_size": rag_analyzer.index.ntotal,
        "citation_db_size": len(rag_analyzer.citation_db)
    }

@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze_trademark(request: AnalyzeRequest):
    """
    Analyze trademark application for registration risks
    
    This is the CORE endpoint that:
    1. Uses RAG to analyze trademark against TMEP guidelines
    2. Identifies specific issues with citations
    3. Calculates multi-dimensional risk scores
    4. Provides actionable recommendations
    """
    
    print(f"📋 Analyzing trademark: {request.mark}")
    
    # Step 1: Identify issues using RAG
    print("   🔍 Step 1: Issue identification with RAG...")
    
    issues_to_check = [
        "likelihood of confusion with similar marks",
        "descriptiveness or genericness",
        "specimen and identification requirements",
        "filing basis and ownership issues"
    ]
    
    rag_results = await rag_analyzer.analyze_multiple_issues_parallel(
        trademark=request.mark,
        goods_services=request.goods_services,
        issue_types=issues_to_check
    )
    
    # Step 2: Convert RAG results to TrademarkIssues
    print("   📊 Step 2: Converting to structured issues...")
    
    trademark_issues = []
    
    for issue_type, rag_result in rag_results.items():
        # Determine category and severity based on analysis
        category = IssueCategory.LIKELIHOOD_CONFUSION  # Default
        severity = RiskLevel.MODERATE
        
        if "confusion" in issue_type.lower():
            category = IssueCategory.LIKELIHOOD_CONFUSION
            severity = RiskLevel.HIGH if rag_result.confidence > 0.7 else RiskLevel.MODERATE
        elif "descriptive" in issue_type.lower():
            category = IssueCategory.DESCRIPTIVENESS
            severity = RiskLevel.MODERATE if rag_result.confidence > 0.6 else RiskLevel.LOW
        elif "specimen" in issue_type.lower():
            category = IssueCategory.SPECIMEN_DEFICIENCY
            severity = RiskLevel.LOW
        elif "ownership" in issue_type.lower():
            category = IssueCategory.OWNERSHIP_ISSUE
            severity = RiskLevel.MODERATE
        
        # Extract primary citation
        primary_citation = rag_result.citations_used[0] if rag_result.citations_used else "TMEP §1207"
        
        # Get citation text from retrieved contexts
        citation_text = ""
        if rag_result.retrieved_sections:
            citation_text = rag_result.retrieved_sections[0].content[:200] + "..."
        
        issue = TrademarkIssue(
            category=category,
            severity=severity,
            title=issue_type.title(),
            description=rag_result.analysis[:300],
            tmep_section=primary_citation.replace("TMEP §", ""),
            citation_text=citation_text,
            recommendation="Review analysis and consider attorney consultation" if rag_result.requires_human_review else "Standard prosecution recommended",
            confidence=rag_result.confidence,
            estimated_cost=_estimate_cost(severity),
            estimated_time=_estimate_time(severity)
        )
        
        trademark_issues.append(issue)
    
    # Step 3: Calculate risk dimensions
    print("   🎯 Step 3: Calculating risk dimensions...")
    
    rejection = risk_framework.assess_rejection_likelihood(
        issues=trademark_issues,
        similar_marks=request.prior_marks,
        tmep_evidence=[{"section": i.tmep_section} for i in trademark_issues]
    )
    
    overcoming = risk_framework.assess_overcoming_difficulty(
        issues=trademark_issues,
        estimated_costs={i.category.value: _parse_cost(i.estimated_cost) for i in trademark_issues},
        estimated_times={i.category.value: _parse_time(i.estimated_time) for i in trademark_issues}
    )
    
    precedent = risk_framework.assess_legal_precedent(
        tmep_sections=[{"section": i.tmep_section, "category": "substantive"} for i in trademark_issues],
        case_law=[],
        third_party_registrations=[]
    )
    
    discretion = risk_framework.assess_examiner_discretion(
        issues=trademark_issues,
        subjective_elements=["commercial impression", "suggestiveness"]
    )
    
    # Step 4: Calculate overall risk
    print("   📈 Step 4: Calculating overall risk...")
    
    dimensions = {
        "rejection_likelihood": rejection,
        "overcoming_difficulty": overcoming,
        "legal_precedent": precedent,
        "examiner_discretion": discretion
    }
    
    overall_score, overall_confidence = risk_framework.calculate_overall_score(dimensions)
    overall_level = risk_framework.determine_risk_level(overall_score)
    needs_review = risk_framework.requires_human_review(overall_confidence)
    
    # Step 5: Generate recommendations
    print("   💡 Step 5: Generating recommendations...")
    
    primary_rec, alt_strategies = risk_framework.generate_recommendations(
        overall_level, trademark_issues, dimensions
    )
    
    # Step 6: Build response
    print("   ✅ Step 6: Building response...")
    
    response = AnalysisResponse(
        overall_risk_score=overall_score,
        overall_risk_level=overall_level.value,
        overall_confidence=overall_confidence,
        requires_human_review=needs_review,
        
        rejection_likelihood=_dim_to_response(rejection),
        overcoming_difficulty=_dim_to_response(overcoming),
        legal_precedent_strength=_dim_to_response(precedent),
        examiner_discretion=_dim_to_response(discretion),
        
        issues=[_issue_to_response(i) for i in trademark_issues],
        total_issues=len(trademark_issues),
        critical_issues=sum(1 for i in trademark_issues if i.severity == RiskLevel.CRITICAL),
        
        primary_recommendation=primary_rec,
        alternative_strategies=alt_strategies,
        estimated_total_cost=_calculate_total_cost(trademark_issues),
        estimated_timeline=_calculate_total_timeline(trademark_issues),
        
        trademark=request.mark,
        goods_services=request.goods_services
    )
    
    print(f"   🎉 Analysis complete! Risk: {overall_level.value}")
    
    return response

@app.post("/api/upload")
async def upload_report(file: UploadFile = File(...)):
    """
    Upload and parse trademark search report PDF
    
    Returns parsed application data and prior marks
    """
    
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
        content = await file.read()
        temp_file.write(content)
        temp_path = temp_file.name
    
    try:
        # Parse the PDF
        parsed_report = document_parser.parse_pdf_report(temp_path)
        
        # Convert to response format
        response = {
            "mark": parsed_report.application.mark,
            "classes": parsed_report.application.classes,
            "goods_services": parsed_report.application.goods_services[0] if parsed_report.application.goods_services else "",
            "prior_marks": {
                "uspto": [
                    {
                        "mark": m.mark,
                        "registration": m.registration_number,
                        "status": m.status,
                        "similarity": m.similarity_score
                    }
                    for m in parsed_report.prior_marks_uspto
                ],
                "state": len(parsed_report.prior_marks_state),
                "common_law": len(parsed_report.prior_marks_common_law),
                "domains": len(parsed_report.prior_marks_domains)
            },
            "total_conflicts": parsed_report.total_conflicts,
            "report_date": parsed_report.report_date
        }
        
        return response
    
    finally:
        # Clean up temp file
        os.unlink(temp_path)

@app.post("/api/analyze-pdf", response_model=PdfAnalysisResponse)
async def analyze_pdf(file: UploadFile = File(...)):
    """
    Upload a PDF trademark report and run FULL analysis on it.
    
    This endpoint:
    1. Parses the PDF with DocumentParser to extract mark, goods/services, classes, prior marks
    2. Runs the same RAG + risk analysis pipeline as /api/analyze
    3. Returns analysis results PLUS the parsed PDF metadata
    """
    
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
        content = await file.read()
        temp_file.write(content)
        temp_path = temp_file.name
    
    try:
        # Step 1: Parse the PDF
        print(f"📄 Parsing uploaded PDF: {file.filename}")
        parsed_report = document_parser.parse_pdf_report(temp_path)
        
        # Extract data from parsed report
        mark = parsed_report.application.mark
        goods_services = (
            parsed_report.application.goods_services[0] 
            if parsed_report.application.goods_services 
            else "General goods and services"
        )
        classes = parsed_report.application.classes or [0]
        
        # Build prior marks list from parsed USPTO marks
        prior_marks = [
            {
                "name": m.mark,
                "registration": m.registration_number or "",
                "similarity": m.similarity_score
            }
            for m in parsed_report.prior_marks_uspto
        ]
        
        print(f"   📋 Extracted mark: {mark}")
        print(f"   📋 Goods/Services: {goods_services}")
        print(f"   📋 Classes: {classes}")
        print(f"   📋 Prior marks found: {len(prior_marks)}")
        
        # Step 2: Run RAG analysis (same as /api/analyze)
        print(f"   🔍 Running RAG analysis on parsed data...")
        
        issues_to_check = [
            "likelihood of confusion with similar marks",
            "descriptiveness or genericness",
            "specimen and identification requirements",
            "filing basis and ownership issues"
        ]
        
        rag_results = await rag_analyzer.analyze_multiple_issues_parallel(
            trademark=mark,
            goods_services=goods_services,
            issue_types=issues_to_check
        )
        
        # Step 3: Convert RAG results to TrademarkIssues
        print("   📊 Converting to structured issues...")
        
        trademark_issues = []
        
        for issue_type, rag_result in rag_results.items():
            category = IssueCategory.LIKELIHOOD_CONFUSION
            severity = RiskLevel.MODERATE
            
            if "confusion" in issue_type.lower():
                category = IssueCategory.LIKELIHOOD_CONFUSION
                severity = RiskLevel.HIGH if rag_result.confidence > 0.7 else RiskLevel.MODERATE
            elif "descriptive" in issue_type.lower():
                category = IssueCategory.DESCRIPTIVENESS
                severity = RiskLevel.MODERATE if rag_result.confidence > 0.6 else RiskLevel.LOW
            elif "specimen" in issue_type.lower():
                category = IssueCategory.SPECIMEN_DEFICIENCY
                severity = RiskLevel.LOW
            elif "ownership" in issue_type.lower():
                category = IssueCategory.OWNERSHIP_ISSUE
                severity = RiskLevel.MODERATE
            
            primary_citation = rag_result.citations_used[0] if rag_result.citations_used else "TMEP §1207"
            
            citation_text = ""
            if rag_result.retrieved_sections:
                citation_text = rag_result.retrieved_sections[0].content[:200] + "..."
            
            issue = TrademarkIssue(
                category=category,
                severity=severity,
                title=issue_type.title(),
                description=rag_result.analysis[:300],
                tmep_section=primary_citation.replace("TMEP §", ""),
                citation_text=citation_text,
                recommendation="Review analysis and consider attorney consultation" if rag_result.requires_human_review else "Standard prosecution recommended",
                confidence=rag_result.confidence,
                estimated_cost=_estimate_cost(severity),
                estimated_time=_estimate_time(severity)
            )
            
            trademark_issues.append(issue)
        
        # Step 4: Calculate risk dimensions
        print("   🎯 Calculating risk dimensions...")
        
        rejection = risk_framework.assess_rejection_likelihood(
            issues=trademark_issues,
            similar_marks=prior_marks,
            tmep_evidence=[{"section": i.tmep_section} for i in trademark_issues]
        )
        
        overcoming = risk_framework.assess_overcoming_difficulty(
            issues=trademark_issues,
            estimated_costs={i.category.value: _parse_cost(i.estimated_cost) for i in trademark_issues},
            estimated_times={i.category.value: _parse_time(i.estimated_time) for i in trademark_issues}
        )
        
        precedent = risk_framework.assess_legal_precedent(
            tmep_sections=[{"section": i.tmep_section, "category": "substantive"} for i in trademark_issues],
            case_law=[],
            third_party_registrations=[]
        )
        
        discretion = risk_framework.assess_examiner_discretion(
            issues=trademark_issues,
            subjective_elements=["commercial impression", "suggestiveness"]
        )
        
        # Step 5: Calculate overall risk
        print("   📈 Calculating overall risk...")
        
        dimensions = {
            "rejection_likelihood": rejection,
            "overcoming_difficulty": overcoming,
            "legal_precedent": precedent,
            "examiner_discretion": discretion
        }
        
        overall_score, overall_confidence = risk_framework.calculate_overall_score(dimensions)
        overall_level = risk_framework.determine_risk_level(overall_score)
        needs_review = risk_framework.requires_human_review(overall_confidence)
        
        # Step 6: Generate recommendations
        print("   💡 Generating recommendations...")
        
        primary_rec, alt_strategies = risk_framework.generate_recommendations(
            overall_level, trademark_issues, dimensions
        )
        
        # Step 7: Build response with PDF metadata
        print("   ✅ Building response...")
        
        # Prepare prior marks for response
        prior_marks_response = [
            {
                "mark": m.mark,
                "registration": m.registration_number,
                "status": m.status,
                "similarity": m.similarity_score
            }
            for m in parsed_report.prior_marks_uspto
        ]
        
        response = PdfAnalysisResponse(
            overall_risk_score=overall_score,
            overall_risk_level=overall_level.value,
            overall_confidence=overall_confidence,
            requires_human_review=needs_review,
            
            rejection_likelihood=_dim_to_response(rejection),
            overcoming_difficulty=_dim_to_response(overcoming),
            legal_precedent_strength=_dim_to_response(precedent),
            examiner_discretion=_dim_to_response(discretion),
            
            issues=[_issue_to_response(i) for i in trademark_issues],
            total_issues=len(trademark_issues),
            critical_issues=sum(1 for i in trademark_issues if i.severity == RiskLevel.CRITICAL),
            
            primary_recommendation=primary_rec,
            alternative_strategies=alt_strategies,
            estimated_total_cost=_calculate_total_cost(trademark_issues),
            estimated_timeline=_calculate_total_timeline(trademark_issues),
            
            trademark=mark,
            goods_services=goods_services,
            
            # PDF-specific fields
            input_mode="pdf",
            parsed_mark=mark,
            parsed_goods_services=goods_services,
            parsed_classes=classes,
            parsed_prior_marks_count=parsed_report.total_conflicts,
            parsed_prior_marks_uspto=prior_marks_response,
            total_pdf_conflicts=parsed_report.total_conflicts,
            report_date=parsed_report.report_date
        )
        
        print(f"   🎉 PDF analysis complete! Risk: {overall_level.value}")
        
        return response
    
    finally:
        # Clean up temp file
        os.unlink(temp_path)

# Helper Functions

def _dim_to_response(dim) -> RiskDimensionResponse:
    """Convert RiskDimension to response model"""
    return RiskDimensionResponse(
        name=dim.name,
        weight=dim.weight,
        score=dim.score,
        confidence=dim.confidence,
        explanation=dim.explanation,
        citations=dim.citations
    )

def _issue_to_response(issue: TrademarkIssue) -> IssueResponse:
    """Convert TrademarkIssue to response model"""
    return IssueResponse(
        category=issue.category.value,
        severity=issue.severity.value,
        title=issue.title,
        description=issue.description,
        tmep_section=issue.tmep_section,
        citation_text=issue.citation_text,
        recommendation=issue.recommendation,
        confidence=issue.confidence,
        estimated_cost=issue.estimated_cost,
        estimated_time=issue.estimated_time
    )

def _estimate_cost(severity: RiskLevel) -> str:
    """Estimate legal costs based on severity"""
    cost_map = {
        RiskLevel.CRITICAL: "$5,000-10,000",
        RiskLevel.HIGH: "$3,000-6,000",
        RiskLevel.MODERATE: "$1,500-3,000",
        RiskLevel.LOW: "$500-1,500",
        RiskLevel.MINIMAL: "$0-500"
    }
    return cost_map.get(severity, "$1,000-2,000")

def _estimate_time(severity: RiskLevel) -> str:
    """Estimate timeline based on severity"""
    time_map = {
        RiskLevel.CRITICAL: "12-18 months",
        RiskLevel.HIGH: "9-12 months",
        RiskLevel.MODERATE: "6-9 months",
        RiskLevel.LOW: "3-6 months",
        RiskLevel.MINIMAL: "1-3 months"
    }
    return time_map.get(severity, "6-9 months")

def _parse_cost(cost_str: str) -> int:
    """Parse cost string to integer (middle estimate)"""
    try:
        costs = [int(c.replace('$', '').replace(',', '')) for c in cost_str.split('-')]
        return sum(costs) // len(costs)
    except:
        return 2000

def _parse_time(time_str: str) -> int:
    """Parse time string to months (middle estimate)"""
    try:
        times = [int(t) for t in time_str.replace('months', '').split('-')]
        return sum(times) // len(times)
    except:
        return 6

def _calculate_total_cost(issues: List[TrademarkIssue]) -> str:
    """Calculate total estimated cost"""
    total = sum(_parse_cost(i.estimated_cost) for i in issues)
    return f"${total:,}-${int(total * 1.5):,}"

def _calculate_total_timeline(issues: List[TrademarkIssue]) -> str:
    """Calculate total estimated timeline"""
    max_time = max([_parse_time(i.estimated_time) for i in issues]) if issues else 6
    return f"{max_time}-{max_time + 3} months"

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Trademark Risk Assessment API...")
    print("📍 Server will run on: http://localhost:8000")
    print("📚 API docs: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)
