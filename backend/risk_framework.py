"""
Trademark Risk Assessment Framework
Multi-dimensional risk scoring with confidence-aware AI and human escalation triggers

This is the CORE differentiator of our system:
- Weighted risk dimensions (not arbitrary scores)
- Confidence-based decision making
- Explainable methodology
- Human escalation when AI is uncertain
"""

from typing import Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum
import json

class RiskLevel(Enum):
    """Risk severity levels"""
    CRITICAL = "critical"      # >75% - Almost certain rejection
    HIGH = "high"              # 60-75% - Likely rejection
    MODERATE = "moderate"      # 40-60% - Possible rejection
    LOW = "low"                # 20-40% - Minor concerns
    MINIMAL = "minimal"        # <20% - Clear path to registration

class IssueCategory(Enum):
    """Types of trademark issues"""
    LIKELIHOOD_CONFUSION = "likelihood_of_confusion"
    DESCRIPTIVENESS = "descriptiveness"
    GENERICNESS = "genericness"
    SPECIMEN_DEFICIENCY = "specimen_deficiency"
    IDENTIFICATION_ISSUE = "identification_issue"
    OWNERSHIP_ISSUE = "ownership_issue"
    BASIS_ISSUE = "filing_basis_issue"
    PROCEDURAL = "procedural_issue"

@dataclass
class RiskDimension:
    """Individual risk dimension with weight and score"""
    name: str
    weight: float  # Percentage weight in overall score
    score: float   # 0-100 score
    confidence: float  # 0-1 confidence in this assessment
    explanation: str
    citations: List[str]  # TMEP citations supporting this assessment

@dataclass
class TrademarkIssue:
    """Individual identified issue"""
    category: IssueCategory
    severity: RiskLevel
    title: str
    description: str
    tmep_section: str
    citation_text: str
    recommendation: str
    confidence: float
    estimated_cost: str  # Cost to overcome
    estimated_time: str  # Time to overcome

@dataclass
class RiskAssessment:
    """Complete risk assessment result"""
    overall_risk_score: float  # 0-100 weighted score
    overall_risk_level: RiskLevel
    overall_confidence: float  # 0-1 confidence
    requires_human_review: bool  # True if confidence < threshold
    
    # Risk dimensions
    rejection_likelihood: RiskDimension  # 40% weight
    overcoming_difficulty: RiskDimension  # 30% weight
    legal_precedent_strength: RiskDimension  # 20% weight
    examiner_discretion: RiskDimension  # 10% weight
    
    # Issues
    issues: List[TrademarkIssue]
    total_issues: int
    critical_issues: int
    
    # Recommendations
    primary_recommendation: str
    alternative_strategies: List[str]
    estimated_total_cost: str
    estimated_timeline: str
    
    # Metadata
    trademark: str
    goods_services: str
    analysis_timestamp: str

class RiskFramework:
    """
    Risk Assessment Framework
    
    Implements the weighted multi-dimensional risk scoring methodology:
    - Rejection Likelihood (40%): Probability examiner will refuse registration
    - Overcoming Difficulty (30%): Effort/cost to overcome refusals
    - Legal Precedent Strength (20%): Strength of legal arguments available
    - Examiner Discretion (10%): Subjective elements in examination
    
    Confidence-Aware AI:
    - Scores each dimension with confidence level
    - Auto-escalates to human review if overall confidence < 60%
    - Transparent about uncertainty
    """
    
    # Dimension weights (must sum to 1.0)
    WEIGHTS = {
        "rejection_likelihood": 0.40,
        "overcoming_difficulty": 0.30,
        "legal_precedent": 0.20,
        "examiner_discretion": 0.10
    }
    
    # Confidence threshold for human escalation
    HUMAN_REVIEW_THRESHOLD = 0.60
    
    def __init__(self):
        self.weights = self.WEIGHTS
        self.threshold = self.HUMAN_REVIEW_THRESHOLD
    
    def calculate_overall_score(self, dimensions: Dict[str, RiskDimension]) -> Tuple[float, float]:
        """
        Calculate weighted overall risk score and confidence
        
        Args:
            dimensions: Dict of dimension_name -> RiskDimension
        
        Returns:
            (overall_score, overall_confidence)
        """
        weighted_score = 0.0
        weighted_confidence = 0.0
        
        for dim_name, weight in self.weights.items():
            dimension = dimensions.get(dim_name)
            if dimension:
                weighted_score += dimension.score * weight
                weighted_confidence += dimension.confidence * weight
        
        return weighted_score, weighted_confidence
    
    def determine_risk_level(self, score: float) -> RiskLevel:
        """Convert numeric score to risk level"""
        if score >= 75:
            return RiskLevel.CRITICAL
        elif score >= 60:
            return RiskLevel.HIGH
        elif score >= 40:
            return RiskLevel.MODERATE
        elif score >= 20:
            return RiskLevel.LOW
        else:
            return RiskLevel.MINIMAL
    
    def requires_human_review(self, confidence: float) -> bool:
        """Determine if assessment needs human expert review"""
        return confidence < self.threshold
    
    def assess_rejection_likelihood(
        self, 
        issues: List[TrademarkIssue],
        similar_marks: List[Dict],
        tmep_evidence: List[Dict]
    ) -> RiskDimension:
        """
        Assess likelihood of USPTO examiner rejecting the application
        
        Factors:
        - Number and severity of identified issues
        - Existence of confusingly similar prior marks
        - Strength of TMEP citations supporting refusal
        """
        score = 0.0
        confidence = 1.0
        explanations = []
        citations = []
        
        # Critical issues contribute heavily
        critical_count = sum(1 for i in issues if i.severity == RiskLevel.CRITICAL)
        high_count = sum(1 for i in issues if i.severity == RiskLevel.HIGH)
        
        if critical_count > 0:
            score += min(critical_count * 30, 60)  # Cap at 60 for critical issues
            explanations.append(f"{critical_count} critical issue(s) identified")
            confidence *= 0.9  # High confidence in critical issues
        
        if high_count > 0:
            score += min(high_count * 15, 30)  # Cap at 30 for high issues
            explanations.append(f"{high_count} high-severity issue(s) identified")
            confidence *= 0.85
        
        # Similar marks increase rejection likelihood
        if similar_marks:
            confusion_risk = len(similar_marks) * 10
            score += min(confusion_risk, 25)
            explanations.append(f"{len(similar_marks)} potentially confusing prior mark(s)")
            citations.extend([m.get('registration', 'Prior mark') for m in similar_marks[:3]])
        
        # Strong TMEP precedent
        if tmep_evidence:
            score += min(len(tmep_evidence) * 5, 15)
            citations.extend([e.get('section', 'TMEP') for e in tmep_evidence[:3]])
        
        # Cap at 100
        score = min(score, 100)
        
        explanation = "Rejection Likelihood: " + "; ".join(explanations) if explanations else "No significant rejection risks identified"
        
        return RiskDimension(
            name="Rejection Likelihood",
            weight=self.weights["rejection_likelihood"],
            score=score,
            confidence=confidence,
            explanation=explanation,
            citations=citations[:5]  # Top 5 citations
        )
    
    def assess_overcoming_difficulty(
        self,
        issues: List[TrademarkIssue],
        estimated_costs: Dict[str, int],
        estimated_times: Dict[str, int]
    ) -> RiskDimension:
        """
        Assess difficulty/cost of overcoming identified issues
        
        Factors:
        - Type of refusals (some easier to overcome than others)
        - Estimated legal costs
        - Time to resolution
        - Availability of evidence/arguments
        """
        score = 0.0
        confidence = 0.85  # Moderate confidence in cost/time estimates
        explanations = []
        citations = []
        
        # Different issue types have different difficulty levels
        difficulty_map = {
            IssueCategory.LIKELIHOOD_CONFUSION: 70,  # Very hard to overcome
            IssueCategory.DESCRIPTIVENESS: 50,        # Moderate - can claim acquired distinctiveness
            IssueCategory.GENERICNESS: 90,            # Nearly impossible
            IssueCategory.SPECIMEN_DEFICIENCY: 20,    # Easy - just submit new specimen
            IssueCategory.IDENTIFICATION_ISSUE: 15,   # Easy - amend description
            IssueCategory.OWNERSHIP_ISSUE: 40,        # Moderate - requires documentation
            IssueCategory.BASIS_ISSUE: 25,            # Relatively easy - may amend basis
            IssueCategory.PROCEDURAL: 10              # Easy - administrative fix
        }
        
        max_difficulty = 0
        total_difficulty = 0
        
        for issue in issues:
            difficulty = difficulty_map.get(issue.category, 30)
            total_difficulty += difficulty
            max_difficulty = max(max_difficulty, difficulty)
            
            if difficulty >= 60:
                explanations.append(f"{issue.category.value} is difficult to overcome")
                citations.append(issue.tmep_section)
        
        # Average difficulty, weighted toward max
        if issues:
            score = (total_difficulty / len(issues)) * 0.6 + max_difficulty * 0.4
            score = min(score, 100)
        
        # Factor in costs if high
        total_cost = sum(estimated_costs.values())
        if total_cost > 5000:
            score += 10
            explanations.append(f"Estimated legal costs: ${total_cost:,}")
        
        # Factor in time if lengthy
        total_time = sum(estimated_times.values())
        if total_time > 12:  # months
            score += 10
            explanations.append(f"Estimated timeline: {total_time} months")
        
        score = min(score, 100)
        
        explanation = "Overcoming Difficulty: " + "; ".join(explanations) if explanations else "Issues can be overcome with standard responses"
        
        return RiskDimension(
            name="Overcoming Difficulty",
            weight=self.weights["overcoming_difficulty"],
            score=score,
            confidence=confidence,
            explanation=explanation,
            citations=citations[:5]
        )
    
    def assess_legal_precedent(
        self,
        tmep_sections: List[Dict],
        case_law: List[Dict],
        third_party_registrations: List[Dict]
    ) -> RiskDimension:
        """
        Assess strength of legal precedent for/against registration
        
        Factors:
        - Relevant TMEP guidance
        - Applicable case law
        - Third-party registrations (showing USPTO accepted similar marks)
        """
        score = 50  # Start neutral
        confidence = 0.75  # Moderate confidence in legal analysis
        explanations = []
        citations = []
        
        # Strong TMEP guidance against registration
        substantive_sections = [s for s in tmep_sections if s.get('category') == 'substantive']
        if len(substantive_sections) >= 3:
            score += 20
            explanations.append(f"Multiple TMEP sections support refusal ({len(substantive_sections)} sections)")
            citations.extend([s.get('section', '') for s in substantive_sections[:2]])
        elif len(substantive_sections) == 0:
            score -= 20
            explanations.append("Limited TMEP precedent for refusal")
        
        # Case law supporting or opposing
        if case_law:
            favorable = sum(1 for c in case_law if c.get('favorable', False))
            unfavorable = len(case_law) - favorable
            
            if unfavorable > favorable:
                score += 15
                explanations.append(f"{unfavorable} case(s) support refusal")
            elif favorable > unfavorable:
                score -= 15
                explanations.append(f"{favorable} case(s) support registration")
        
        # Third-party registrations (evidence USPTO accepts similar marks)
        if third_party_registrations:
            score -= min(len(third_party_registrations) * 5, 20)
            explanations.append(f"{len(third_party_registrations)} similar mark(s) registered by USPTO")
            confidence *= 0.9  # These are strong evidence
        
        score = max(0, min(score, 100))
        
        explanation = "Legal Precedent: " + "; ".join(explanations) if explanations else "Neutral legal precedent"
        
        return RiskDimension(
            name="Legal Precedent Strength",
            weight=self.weights["legal_precedent"],
            score=score,
            confidence=confidence,
            explanation=explanation,
            citations=citations[:5]
        )
    
    def assess_examiner_discretion(
        self,
        issues: List[TrademarkIssue],
        subjective_elements: List[str]
    ) -> RiskDimension:
        """
        Assess role of examiner subjective judgment
        
        Factors:
        - Presence of subjective elements (commercial impression, suggestiveness, etc.)
        - Gray areas in trademark law
        - Likelihood examiner could reasonably decide either way
        """
        score = 30  # Default moderate discretion
        confidence = 0.70  # Lower confidence - predicting human judgment is hard
        explanations = []
        citations = []
        
        # Issues with high examiner discretion
        high_discretion_categories = [
            IssueCategory.LIKELIHOOD_CONFUSION,  # Subjective "commercial impression"
            IssueCategory.DESCRIPTIVENESS,       # Descriptive vs suggestive is gray area
        ]
        
        discretionary_issues = [i for i in issues if i.category in high_discretion_categories]
        
        if discretionary_issues:
            score = 50 + len(discretionary_issues) * 10
            explanations.append(f"{len(discretionary_issues)} issue(s) involve examiner discretion")
            citations.extend([i.tmep_section for i in discretionary_issues[:2]])
        
        # Subjective elements increase discretion
        if subjective_elements:
            score += min(len(subjective_elements) * 5, 20)
            explanations.append(f"{len(subjective_elements)} subjective element(s) in analysis")
        
        score = min(score, 100)
        
        explanation = "Examiner Discretion: " + "; ".join(explanations) if explanations else "Limited examiner discretion"
        
        return RiskDimension(
            name="Examiner Discretion",
            weight=self.weights["examiner_discretion"],
            score=score,
            confidence=confidence,
            explanation=explanation,
            citations=citations[:3]
        )
    
    def generate_recommendations(
        self,
        risk_level: RiskLevel,
        issues: List[TrademarkIssue],
        dimensions: Dict[str, RiskDimension]
    ) -> Tuple[str, List[str]]:
        """
        Generate primary recommendation and alternative strategies
        
        Returns:
            (primary_recommendation, alternative_strategies)
        """
        primary = ""
        alternatives = []
        
        if risk_level == RiskLevel.CRITICAL:
            primary = "DO NOT FILE - Likelihood of rejection is very high. Consider substantial mark modification or alternative mark entirely."
            alternatives = [
                "Conduct comprehensive knockout search to identify less risky mark",
                "If brand is essential, budget for extensive legal costs and likelihood of failure",
                "Consider foreign filing first to establish some rights",
                "Explore common law rights instead of federal registration"
            ]
        
        elif risk_level == RiskLevel.HIGH:
            primary = "PROCEED WITH CAUTION - Significant rejection risk exists. Recommend addressing issues before filing or budgeting for extensive Office Action responses."
            alternatives = [
                "Amend goods/services to avoid conflicting classes",
                "Develop secondary meaning evidence before filing",
                "File intent-to-use to delay specimen submission while addressing issues",
                "Consult trademark attorney for pre-filing risk mitigation",
                "Consider consent agreement if single prior mark is primary issue"
            ]
        
        elif risk_level == RiskLevel.MODERATE:
            primary = "PROCEED WITH PREPARATION - Issues exist but can likely be overcome. Budget for 1-2 Office Action responses."
            alternatives = [
                "Prepare response arguments in advance",
                "Gather evidence of non-descriptiveness or acquired distinctiveness",
                "Ensure specimens meet all USPTO requirements",
                "Consider trademark attorney for Office Action response",
                "Monitor similar applications during prosecution"
            ]
        
        elif risk_level == RiskLevel.LOW:
            primary = "PROCEED - Minor issues may arise but registration is likely. Standard prosecution expected."
            alternatives = [
                "Ensure all filing requirements are met",
                "Monitor application status regularly",
                "Prepare for possible minor amendments",
                "Consider DIY filing or limited attorney assistance"
            ]
        
        else:  # MINIMAL
            primary = "PROCEED CONFIDENTLY - Clear path to registration. Minimal risk identified."
            alternatives = [
                "File application as soon as ready",
                "DIY filing is reasonable given low risk",
                "Maintain specimens and usage evidence",
                "Plan for straightforward prosecution timeline (8-12 months)"
            ]
        
        # Add issue-specific recommendations
        for issue in issues:
            if issue.recommendation and issue.recommendation not in alternatives:
                alternatives.append(issue.recommendation)
        
        return primary, alternatives[:5]  # Top 5 alternatives

def create_sample_assessment():
    """Create a sample assessment for testing"""
    
    framework = RiskFramework()
    
    # Sample issues
    issues = [
        TrademarkIssue(
            category=IssueCategory.LIKELIHOOD_CONFUSION,
            severity=RiskLevel.HIGH,
            title="Likelihood of Confusion with LIVEMORE",
            description="Prior registered mark LIVEMORE exists in Class 5 for supplements, creating confusion risk with LIVE MORE element",
            tmep_section="1207.01",
            citation_text="Marks are compared in their entireties for similarities in appearance, sound, connotation...",
            recommendation="Consider disclaimer of LIVE MORE element or amend to different goods",
            confidence=0.85,
            estimated_cost="$2,000-4,000",
            estimated_time="6-9 months"
        ),
        TrademarkIssue(
            category=IssueCategory.DESCRIPTIVENESS,
            severity=RiskLevel.MODERATE,
            title="Descriptiveness of POUR for Beverages",
            description="POUR directly describes the method of consuming beverages, potentially merely descriptive under 2(e)(1)",
            tmep_section="1209.01",
            citation_text="A mark is merely descriptive if it immediately conveys knowledge of a quality, feature, function...",
            recommendation="Argue phrase as a whole is suggestive; prepare acquired distinctiveness evidence",
            confidence=0.75,
            estimated_cost="$1,500-3,000",
            estimated_time="4-6 months"
        )
    ]
    
    # Calculate dimensions
    rejection = framework.assess_rejection_likelihood(
        issues=issues,
        similar_marks=[{"name": "LIVEMORE", "registration": "5234567"}],
        tmep_evidence=[{"section": "1207.01"}]
    )
    
    overcoming = framework.assess_overcoming_difficulty(
        issues=issues,
        estimated_costs={"confusion": 3000, "descriptiveness": 2000},
        estimated_times={"confusion": 9, "descriptiveness": 6}
    )
    
    precedent = framework.assess_legal_precedent(
        tmep_sections=[{"section": "1207.01", "category": "substantive"}],
        case_law=[],
        third_party_registrations=[]
    )
    
    discretion = framework.assess_examiner_discretion(
        issues=issues,
        subjective_elements=["commercial impression", "suggestiveness"]
    )
    
    dimensions = {
        "rejection_likelihood": rejection,
        "overcoming_difficulty": overcoming,
        "legal_precedent": precedent,
        "examiner_discretion": discretion
    }
    
    # Calculate overall
    overall_score, overall_confidence = framework.calculate_overall_score(dimensions)
    overall_level = framework.determine_risk_level(overall_score)
    needs_review = framework.requires_human_review(overall_confidence)
    
    primary_rec, alt_strategies = framework.generate_recommendations(
        overall_level, issues, dimensions
    )
    
    assessment = RiskAssessment(
        overall_risk_score=overall_score,
        overall_risk_level=overall_level,
        overall_confidence=overall_confidence,
        requires_human_review=needs_review,
        rejection_likelihood=rejection,
        overcoming_difficulty=overcoming,
        legal_precedent_strength=precedent,
        examiner_discretion=discretion,
        issues=issues,
        total_issues=len(issues),
        critical_issues=sum(1 for i in issues if i.severity == RiskLevel.CRITICAL),
        primary_recommendation=primary_rec,
        alternative_strategies=alt_strategies,
        estimated_total_cost="$3,500-7,000",
        estimated_timeline="6-9 months",
        trademark="TEAR, POUR, LIVE MORE",
        goods_services="Energy drinks, sports drinks, dietary supplements",
        analysis_timestamp="2024-02-07T10:00:00Z"
    )
    
    return assessment

if __name__ == "__main__":
    print("🧪 Testing Risk Assessment Framework...")
    print("=" * 70)
    
    assessment = create_sample_assessment()
    
    print(f"\n📊 RISK ASSESSMENT: {assessment.trademark}")
    print(f"Goods/Services: {assessment.goods_services}")
    print("=" * 70)
    
    print(f"\n🎯 OVERALL RISK: {assessment.overall_risk_level.value.upper()}")
    print(f"   Score: {assessment.overall_risk_score:.1f}/100")
    print(f"   Confidence: {assessment.overall_confidence*100:.1f}%")
    print(f"   Human Review Required: {'YES ⚠️' if assessment.requires_human_review else 'NO ✅'}")
    
    print(f"\n📏 RISK DIMENSIONS:")
    for dim in [assessment.rejection_likelihood, assessment.overcoming_difficulty, 
                assessment.legal_precedent_strength, assessment.examiner_discretion]:
        print(f"\n   {dim.name} (Weight: {dim.weight*100:.0f}%)")
        print(f"   Score: {dim.score:.1f}/100 | Confidence: {dim.confidence*100:.1f}%")
        print(f"   {dim.explanation}")
    
    print(f"\n⚠️  ISSUES IDENTIFIED: {assessment.total_issues}")
    for i, issue in enumerate(assessment.issues, 1):
        print(f"\n   {i}. {issue.title} [{issue.severity.value.upper()}]")
        print(f"      {issue.description}")
        print(f"      TMEP §{issue.tmep_section}")
        print(f"      Cost: {issue.estimated_cost} | Time: {issue.estimated_time}")
    
    print(f"\n💡 PRIMARY RECOMMENDATION:")
    print(f"   {assessment.primary_recommendation}")
    
    print(f"\n🔄 ALTERNATIVE STRATEGIES:")
    for i, alt in enumerate(assessment.alternative_strategies, 1):
        print(f"   {i}. {alt}")
    
    print(f"\n💰 ESTIMATED COSTS: {assessment.estimated_total_cost}")
    print(f"⏱️  ESTIMATED TIMELINE: {assessment.estimated_timeline}")
    
    print("\n" + "=" * 70)
    print("✅ Risk Framework Test Complete!")
