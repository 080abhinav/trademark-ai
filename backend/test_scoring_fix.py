"""
Test script to verify risk scoring fix.
Ensures high-risk inputs produce HIGH/CRITICAL scores, not MODERATE.
"""
from risk_framework import RiskFramework, TrademarkIssue, IssueCategory, RiskLevel

fw = RiskFramework()

print("=" * 60)
print("TEST 1: RED BULL POWER with prior mark RED BULL (name contained)")
print("=" * 60)

issues = [
    TrademarkIssue(
        category=IssueCategory.LIKELIHOOD_CONFUSION, severity=RiskLevel.CRITICAL,
        title="Confusion", description="test", tmep_section="1207", citation_text="test",
        recommendation="test", confidence=0.9, estimated_cost="5000-10000", estimated_time="12-18 months"
    ),
    TrademarkIssue(
        category=IssueCategory.DESCRIPTIVENESS, severity=RiskLevel.MODERATE,
        title="Descriptiveness", description="test", tmep_section="1209", citation_text="test",
        recommendation="test", confidence=0.7, estimated_cost="1500-3000", estimated_time="6-9 months"
    ),
]

rejection = fw.assess_rejection_likelihood(
    issues=issues,
    similar_marks=[{"name": "RED BULL", "registration": "1234567", "name_contained": True}],
    tmep_evidence=[{"section": "1207"}, {"section": "1209"}]
)
print(f"  Rejection Likelihood score: {rejection.score}")
print(f"  Explanation: {rejection.explanation}")

overcoming = fw.assess_overcoming_difficulty(
    issues=issues,
    estimated_costs={"likelihood_of_confusion": 7500, "descriptiveness": 2250},
    estimated_times={"likelihood_of_confusion": 15, "descriptiveness": 7}
)
print(f"  Overcoming Difficulty score: {overcoming.score}")

precedent = fw.assess_legal_precedent(
    tmep_sections=[
        {"section": "1207", "category": "substantive"},
        {"section": "1209", "category": "substantive"},
        {"section": "1207.01", "category": "substantive"},
        {"section": "1209.01", "category": "substantive"},
    ],
    case_law=[],
    third_party_registrations=[]
)
print(f"  Legal Precedent score: {precedent.score}")

discretion = fw.assess_examiner_discretion(
    issues=issues,
    subjective_elements=["commercial impression", "suggestiveness"]
)
print(f"  Examiner Discretion score: {discretion.score}")

dims = {
    "rejection_likelihood": rejection,
    "overcoming_difficulty": overcoming,
    "legal_precedent": precedent,
    "examiner_discretion": discretion,
}
score, conf = fw.calculate_overall_score(dims)
level = fw.determine_risk_level(score)
print(f"\n  OVERALL SCORE: {score:.1f}/100")
print(f"  RISK LEVEL: {level.value.upper()}")
print(f"  Confidence: {conf*100:.1f}%")
assert level in (RiskLevel.HIGH, RiskLevel.CRITICAL), f"FAIL: Expected HIGH/CRITICAL, got {level.value}"
print("  PASSED")

print()
print("=" * 60)
print("TEST 2: FRESH JUICE (no prior marks, clean mark)")
print("=" * 60)

issues2 = [
    TrademarkIssue(
        category=IssueCategory.DESCRIPTIVENESS, severity=RiskLevel.MODERATE,
        title="Descriptiveness", description="test", tmep_section="1209", citation_text="test",
        recommendation="test", confidence=0.6, estimated_cost="1500-3000", estimated_time="6-9 months"
    ),
    TrademarkIssue(
        category=IssueCategory.SPECIMEN_DEFICIENCY, severity=RiskLevel.LOW,
        title="Specimen", description="test", tmep_section="904", citation_text="test",
        recommendation="test", confidence=0.5, estimated_cost="500-1500", estimated_time="3-6 months"
    ),
]

rejection2 = fw.assess_rejection_likelihood(issues=issues2, similar_marks=[], tmep_evidence=[{"section": "1209"}])
overcoming2 = fw.assess_overcoming_difficulty(issues=issues2, estimated_costs={"descriptiveness": 2250}, estimated_times={"descriptiveness": 7})
precedent2 = fw.assess_legal_precedent(tmep_sections=[{"section": "1209", "category": "substantive"}], case_law=[], third_party_registrations=[])
discretion2 = fw.assess_examiner_discretion(issues=issues2, subjective_elements=["suggestiveness"])

dims2 = {
    "rejection_likelihood": rejection2,
    "overcoming_difficulty": overcoming2,
    "legal_precedent": precedent2,
    "examiner_discretion": discretion2,
}
score2, conf2 = fw.calculate_overall_score(dims2)
level2 = fw.determine_risk_level(score2)
print(f"  Rejection: {rejection2.score}, Overcoming: {overcoming2.score}, Precedent: {precedent2.score}, Discretion: {discretion2.score}")
print(f"  OVERALL SCORE: {score2:.1f}/100")
print(f"  RISK LEVEL: {level2.value.upper()}")
assert level2 in (RiskLevel.LOW, RiskLevel.MODERATE), f"FAIL: Expected LOW/MODERATE, got {level2.value}"
print("  PASSED")

print()
print("=" * 60)
print("TEST 3: NIKE AIR MAX with prior mark NIKE (name contained)")
print("=" * 60)

issues3 = [
    TrademarkIssue(
        category=IssueCategory.LIKELIHOOD_CONFUSION, severity=RiskLevel.CRITICAL,
        title="Confusion", description="test", tmep_section="1207", citation_text="test",
        recommendation="test", confidence=0.95, estimated_cost="5000-10000", estimated_time="12-18 months"
    ),
]

rejection3 = fw.assess_rejection_likelihood(
    issues=issues3,
    similar_marks=[{"name": "NIKE", "registration": "9876543", "name_contained": True}],
    tmep_evidence=[{"section": "1207"}]
)
dims3 = {
    "rejection_likelihood": rejection3,
    "overcoming_difficulty": fw.assess_overcoming_difficulty(issues3, {"likelihood_of_confusion": 7500}, {"likelihood_of_confusion": 15}),
    "legal_precedent": fw.assess_legal_precedent([{"section": "1207", "category": "substantive"}], [], []),
    "examiner_discretion": fw.assess_examiner_discretion(issues3, ["commercial impression"]),
}
score3, _ = fw.calculate_overall_score(dims3)
level3 = fw.determine_risk_level(score3)
print(f"  OVERALL SCORE: {score3:.1f}/100")
print(f"  RISK LEVEL: {level3.value.upper()}")
assert level3 in (RiskLevel.HIGH, RiskLevel.CRITICAL), f"FAIL: Expected HIGH/CRITICAL, got {level3.value}"
print("  PASSED")

print()
print("=" * 60)
print("TEST 4: Prior marks supplied but no name containment")
print("=" * 60)

issues4 = [
    TrademarkIssue(
        category=IssueCategory.LIKELIHOOD_CONFUSION, severity=RiskLevel.HIGH,
        title="Confusion", description="test", tmep_section="1207", citation_text="test",
        recommendation="test", confidence=0.8, estimated_cost="3000-6000", estimated_time="9-12 months"
    ),
]

rejection4 = fw.assess_rejection_likelihood(
    issues=issues4,
    similar_marks=[{"name": "BLUE OX", "registration": "5555555", "name_contained": False}],
    tmep_evidence=[{"section": "1207"}]
)
dims4 = {
    "rejection_likelihood": rejection4,
    "overcoming_difficulty": fw.assess_overcoming_difficulty(issues4, {"likelihood_of_confusion": 4500}, {"likelihood_of_confusion": 10}),
    "legal_precedent": fw.assess_legal_precedent([{"section": "1207", "category": "substantive"}], [], []),
    "examiner_discretion": fw.assess_examiner_discretion(issues4, ["commercial impression"]),
}
score4, _ = fw.calculate_overall_score(dims4)
level4 = fw.determine_risk_level(score4)
print(f"  Rejection: {rejection4.score}")
print(f"  OVERALL SCORE: {score4:.1f}/100")
print(f"  RISK LEVEL: {level4.value.upper()}")
# Should be HIGH or MODERATE (not CRITICAL, since no name containment)
assert level4 in (RiskLevel.HIGH, RiskLevel.MODERATE), f"FAIL: Expected HIGH/MODERATE, got {level4.value}"
print("  PASSED")

print()
print("ALL 4 TESTS PASSED!")
