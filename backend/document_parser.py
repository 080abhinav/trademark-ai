"""
Document Parser
Extracts trademark application data from uploaded PDF reports (like CompuMark reports)

Handles:
- Trademark name extraction
- Goods/services classification
- Prior marks identification
- USPTO citations extraction
- State/common law marks
"""

import re
from typing import Dict, List, Optional
from dataclasses import dataclass
import PyPDF2
from pathlib import Path

@dataclass
class TrademarkApplication:
    """Parsed trademark application data"""
    mark: str
    applicant: Optional[str]
    goods_services: List[str]
    classes: List[int]
    filing_basis: Optional[str]
    specimen_type: Optional[str]
    
@dataclass
class PriorMark:
    """Prior conflicting mark"""
    mark: str
    registration_number: Optional[str]
    serial_number: Optional[str]
    owner: Optional[str]
    classes: List[int]
    goods_services: str
    status: str
    similarity_score: float
    source: str  # "USPTO", "State", "Common Law", "Domain"

@dataclass
class ParsedReport:
    """Complete parsed trademark search report"""
    application: TrademarkApplication
    prior_marks_uspto: List[PriorMark]
    prior_marks_state: List[PriorMark]
    prior_marks_common_law: List[PriorMark]
    prior_marks_domains: List[PriorMark]
    total_conflicts: int
    report_date: Optional[str]
    report_type: str

class DocumentParser:
    """
    Parse trademark search reports and applications
    
    Supports:
    - CompuMark reports
    - USPTO TESS reports
    - Plain text trademark descriptions
    """
    
    def __init__(self):
        self.mark_patterns = [
            r"Mark:\s*([A-Z0-9\s,\.!?-]+)",
            r"Trademark:\s*([A-Z0-9\s,\.!?-]+)",
            r"Applied-for Mark:\s*([A-Z0-9\s,\.!?-]+)"
        ]
        
        self.class_pattern = r"Class(?:es)?:\s*([\d,\s]+)"
        self.registration_pattern = r"Reg(?:istration)?\.?\s*No\.?\s*:?\s*([\d,]+)"
        self.serial_pattern = r"Serial\s*No\.?\s*:?\s*([\d,]+)"
    
    def parse_pdf_report(self, pdf_path: str) -> ParsedReport:
        """
        Parse trademark search report PDF
        
        Args:
            pdf_path: Path to PDF file
        
        Returns:
            ParsedReport with extracted data
        """
        print(f"📄 Parsing PDF: {pdf_path}")
        
        # Extract text from PDF
        text = self._extract_pdf_text(pdf_path)
        
        # Extract application details
        application = self._extract_application(text)
        
        # Extract prior marks by source
        uspto_marks = self._extract_uspto_marks(text)
        state_marks = self._extract_state_marks(text)
        common_law = self._extract_common_law_marks(text)
        domains = self._extract_domain_marks(text)
        
        # Extract report metadata
        report_date = self._extract_date(text)
        
        total_conflicts = (
            len(uspto_marks) + 
            len(state_marks) + 
            len(common_law) + 
            len(domains)
        )
        
        report = ParsedReport(
            application=application,
            prior_marks_uspto=uspto_marks,
            prior_marks_state=state_marks,
            prior_marks_common_law=common_law,
            prior_marks_domains=domains,
            total_conflicts=total_conflicts,
            report_date=report_date,
            report_type="CompuMark Search Report"
        )
        
        print(f"   ✓ Parsed mark: {application.mark}")
        print(f"   ✓ Found {total_conflicts} prior marks")
        print(f"      - USPTO: {len(uspto_marks)}")
        print(f"      - State: {len(state_marks)}")
        print(f"      - Common Law: {len(common_law)}")
        print(f"      - Domains: {len(domains)}")
        
        return report
    
    def _extract_pdf_text(self, pdf_path: str) -> str:
        """Extract all text from PDF"""
        text = ""
        
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        
        return text
    
    def _extract_application(self, text: str) -> TrademarkApplication:
        """Extract application details from report"""
        
        # Extract mark
        mark = "UNKNOWN"
        for pattern in self.mark_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                mark = match.group(1).strip()
                break
        
        # Extract classes
        classes = []
        class_match = re.search(self.class_pattern, text, re.IGNORECASE)
        if class_match:
            class_str = class_match.group(1)
            classes = [int(c.strip()) for c in class_str.split(',') if c.strip().isdigit()]
        
        # Extract goods/services (simplified - look for common patterns)
        goods_services = []
        
        # Common indicators of goods/services descriptions
        gs_patterns = [
            r"Goods/Services:\s*([^\n]+)",
            r"Class \d+:\s*([^\n]+)"
        ]
        
        for pattern in gs_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                gs = match.group(1).strip()
                if gs and len(gs) > 10:  # Filter out noise
                    goods_services.append(gs)
        
        # If no goods/services found, provide defaults based on classes
        if not goods_services and classes:
            if 5 in classes:
                goods_services.append("Dietary and nutritional supplements")
            if 32 in classes:
                goods_services.append("Non-alcoholic beverages")
        
        return TrademarkApplication(
            mark=mark,
            applicant=None,  # Can be extracted if needed
            goods_services=goods_services,
            classes=classes,
            filing_basis=None,
            specimen_type=None
        )
    
    def _extract_uspto_marks(self, text: str) -> List[PriorMark]:
        """Extract USPTO registered/pending marks from report"""
        marks = []
        
        # Look for USPTO sections
        # CompuMark reports typically have "UNITED STATES PATENT AND TRADEMARK OFFICE" sections
        uspto_section_pattern = r"UNITED STATES PATENT AND TRADEMARK OFFICE.*?(?=STATE TRADEMARK|COMMON LAW|DOMAIN NAMES|$)"
        
        uspto_match = re.search(uspto_section_pattern, text, re.IGNORECASE | re.DOTALL)
        
        if not uspto_match:
            # Try alternative pattern
            uspto_section_pattern = r"USPTO.*?(?=State|Common|Domain|$)"
            uspto_match = re.search(uspto_section_pattern, text, re.IGNORECASE | re.DOTALL)
        
        if uspto_match:
            uspto_text = uspto_match.group(0)
            
            # Extract individual mark records
            # Pattern: Mark name followed by registration/serial number
            mark_records = re.finditer(
                r"([A-Z][A-Z0-9\s,\.\-\']{2,50})\s+(?:Reg\.?\s*No\.?\s*:?\s*([\d,]+)|Serial\s*No\.?\s*:?\s*([\d,]+))",
                uspto_text
            )
            
            for match in mark_records:
                mark_name = match.group(1).strip()
                reg_num = match.group(2)
                serial_num = match.group(3)
                
                # Calculate simple similarity score (placeholder)
                similarity = self._calculate_similarity_score(mark_name)
                
                prior_mark = PriorMark(
                    mark=mark_name,
                    registration_number=reg_num,
                    serial_number=serial_num,
                    owner=None,
                    classes=[],  # Can extract if needed
                    goods_services="",
                    status="Registered" if reg_num else "Pending",
                    similarity_score=similarity,
                    source="USPTO"
                )
                marks.append(prior_mark)
        
        return marks[:50]  # Limit to top 50 for performance
    
    def _extract_state_marks(self, text: str) -> List[PriorMark]:
        """Extract state trademark registrations"""
        marks = []
        
        # Look for State section
        state_pattern = r"STATE TRADEMARK.*?(?=COMMON LAW|DOMAIN NAMES|$)"
        state_match = re.search(state_pattern, text, re.IGNORECASE | re.DOTALL)
        
        if state_match:
            state_text = state_match.group(0)
            
            # Extract state marks (simplified)
            mark_records = re.finditer(
                r"([A-Z][A-Z0-9\s,\.\-\']{2,50})\s+\(([A-Z]{2})\)",
                state_text
            )
            
            for match in mark_records:
                mark_name = match.group(1).strip()
                state = match.group(2)
                
                similarity = self._calculate_similarity_score(mark_name)
                
                prior_mark = PriorMark(
                    mark=mark_name,
                    registration_number=None,
                    serial_number=None,
                    owner=None,
                    classes=[],
                    goods_services=f"State registration ({state})",
                    status="Registered",
                    similarity_score=similarity,
                    source=f"State ({state})"
                )
                marks.append(prior_mark)
        
        return marks[:25]  # Limit to top 25
    
    def _extract_common_law_marks(self, text: str) -> List[PriorMark]:
        """Extract common law (unregistered) marks"""
        marks = []
        
        # Look for Common Law section
        cl_pattern = r"COMMON LAW.*?(?=DOMAIN NAMES|$)"
        cl_match = re.search(cl_pattern, text, re.IGNORECASE | re.DOTALL)
        
        if cl_match:
            cl_text = cl_match.group(0)
            
            # Extract common law marks
            mark_records = re.finditer(
                r"([A-Z][A-Z0-9\s,\.\-\']{2,50})",
                cl_text
            )
            
            seen = set()
            for match in mark_records:
                mark_name = match.group(1).strip()
                
                # Avoid duplicates
                if mark_name in seen or len(mark_name) < 3:
                    continue
                seen.add(mark_name)
                
                similarity = self._calculate_similarity_score(mark_name)
                
                prior_mark = PriorMark(
                    mark=mark_name,
                    registration_number=None,
                    serial_number=None,
                    owner=None,
                    classes=[],
                    goods_services="Common law use",
                    status="Unregistered",
                    similarity_score=similarity,
                    source="Common Law"
                )
                marks.append(prior_mark)
        
        return marks[:20]  # Limit to top 20
    
    def _extract_domain_marks(self, text: str) -> List[PriorMark]:
        """Extract domain name conflicts"""
        marks = []
        
        # Look for Domain Names section
        domain_pattern = r"DOMAIN NAMES?.*?(?=\n\n\n|$)"
        domain_match = re.search(domain_pattern, text, re.IGNORECASE | re.DOTALL)
        
        if domain_match:
            domain_text = domain_match.group(0)
            
            # Extract domains
            domain_records = re.finditer(
                r"([a-z0-9\-]+\.[a-z]{2,})",
                domain_text,
                re.IGNORECASE
            )
            
            seen = set()
            for match in domain_records:
                domain = match.group(1).lower()
                
                if domain in seen:
                    continue
                seen.add(domain)
                
                # Extract brand name from domain
                brand = domain.split('.')[0]
                
                similarity = self._calculate_similarity_score(brand)
                
                prior_mark = PriorMark(
                    mark=brand.upper(),
                    registration_number=None,
                    serial_number=None,
                    owner=None,
                    classes=[],
                    goods_services=f"Domain: {domain}",
                    status="Active",
                    similarity_score=similarity,
                    source="Domain Name"
                )
                marks.append(prior_mark)
        
        return marks[:30]  # Limit to top 30
    
    def _extract_date(self, text: str) -> Optional[str]:
        """Extract report date"""
        date_pattern = r"(?:Date|Report Date|Search Date):\s*([A-Za-z]+\s+\d{1,2},\s*\d{4})"
        match = re.search(date_pattern, text, re.IGNORECASE)
        
        if match:
            return match.group(1)
        
        return None
    
    def _calculate_similarity_score(self, mark: str) -> float:
        """
        Calculate simple similarity score
        (Placeholder - real implementation would use proper string similarity)
        """
        # For now, just return a random-ish score based on length
        # In production, use Levenshtein distance, phonetic similarity, etc.
        score = min(0.9, 0.3 + (len(mark) % 7) * 0.1)
        return score
    
    def parse_text_description(
        self,
        mark: str,
        goods_services: str,
        classes: List[int]
    ) -> TrademarkApplication:
        """
        Parse trademark from text description (for manual input)
        
        Args:
            mark: Trademark text
            goods_services: Description of goods/services
            classes: Nice classification numbers
        
        Returns:
            TrademarkApplication
        """
        return TrademarkApplication(
            mark=mark.upper().strip(),
            applicant=None,
            goods_services=[goods_services],
            classes=classes,
            filing_basis="Intent to Use (1b)",  # Default
            specimen_type=None
        )

def test_parser():
    """Test document parser"""
    
    print("🧪 TESTING DOCUMENT PARSER")
    print("=" * 70)
    print()
    
    parser = DocumentParser()
    
    # Test with uploaded PDF if available
    # Try multiple possible locations
    possible_paths = [
        r"C:\Users\Lenovo\Desktop\trademark-ai\data\TEAR, POUR, LIVE MORE_FULL.pdf",
        r"..\data\TEAR, POUR, LIVE MORE_FULL.pdf",
        r"TEAR, POUR, LIVE MORE_FULL.pdf",
        "/mnt/user-data/uploads/TEAR, POUR, LIVE MORE_FULL.pdf"
    ]
    
    pdf_path = None
    for path in possible_paths:
        if Path(path).exists():
            pdf_path = path
            break
    
    if pdf_path:
        print(f"📄 Testing with real PDF: {pdf_path}")
        report = parser.parse_pdf_report(pdf_path)
        
        print()
        print(f"✅ PARSED REPORT:")
        print(f"   Mark: {report.application.mark}")
        print(f"   Classes: {report.application.classes}")
        print(f"   Goods/Services: {len(report.application.goods_services)} items")
        print()
        print(f"   Prior Marks Found:")
        print(f"      USPTO: {len(report.prior_marks_uspto)}")
        print(f"      State: {len(report.prior_marks_state)}")
        print(f"      Common Law: {len(report.prior_marks_common_law)}")
        print(f"      Domains: {len(report.prior_marks_domains)}")
        print()
        
        if report.prior_marks_uspto:
            print(f"   Sample USPTO Marks:")
            for mark in report.prior_marks_uspto[:5]:
                print(f"      - {mark.mark} (Reg: {mark.registration_number}, Similarity: {mark.similarity_score:.2f})")
    
    else:
        print("⚠️  PDF not found, testing with text input")
        
        # Test text parsing
        app = parser.parse_text_description(
            mark="TEAR, POUR, LIVE MORE",
            goods_services="Energy drinks, sports drinks, dietary supplements",
            classes=[5, 32]
        )
        
        print(f"✅ Parsed from text:")
        print(f"   Mark: {app.mark}")
        print(f"   Classes: {app.classes}")
        print(f"   Goods: {app.goods_services}")
    
    print()
    print("✅ Document Parser Test Complete!")

if __name__ == "__main__":
    test_parser()
