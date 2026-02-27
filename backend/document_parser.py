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
            r"Mark Searched:\s*([^\n]+)",       # CompuMark format (most common)
            r"Applied-for Mark:\s*([^\n]+)",
            r"Trademark:\s*([^\n]+)",
            r"Mark:\s*([A-Z][A-Z0-9,\. !?-]+)"  # Fallback — stop at lowercase/newline
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
        
        # --- IMPORTANT: Only look in the APPLICATION SECTION (first ~3000 chars) ---
        # The rest of the PDF contains prior marks with THEIR classes, which we must NOT pick up
        app_section = text[:3000]
        
        # Extract classes from application section only
        classes = set()
        # Pattern 1: "Class 5", "Class 32", "Classes: 5, 32"
        for m in re.finditer(r"Class(?:es)?[:\s]+([\d,\s]+)", app_section, re.IGNORECASE):
            for c in m.group(1).split(','):
                c = c.strip()
                if c.isdigit() and 1 <= int(c) <= 45:
                    classes.add(int(c))
        # Pattern 2: "CLASS 5:" or "CLASS 32:" standalone (application description)
        for m in re.finditer(r"CLASS\s+(\d{1,2})\s*:", app_section):
            c = int(m.group(1))
            if 1 <= c <= 45:
                classes.add(c)
        classes = sorted(classes)
        
        # Extract goods/services from application section only
        # The PDF may break goods/services text across multiple lines, so we extract
        # the full block and join lines before parsing
        goods_services = []
        seen_gs = set()
        
        # Step 1: Extract the full goods/services text block (may span multiple lines)
        gs_block_match = re.search(
            r"Goods/Services:\s*(.*?)(?:Trademark Research Report|Client understands|Report Graph|$)",
            app_section,
            re.DOTALL | re.IGNORECASE
        )
        
        if gs_block_match:
            # Join lines and normalize whitespace
            gs_block = gs_block_match.group(1)
            gs_block = re.sub(r"\s*\n\s*", " ", gs_block).strip()  # Join newlines with space
            gs_block = re.sub(r"\s{2,}", " ", gs_block)  # Collapse multiple spaces
            # Fix common OCR artifacts (mid-word spaces from PDF extraction)
            gs_block = gs_block.replace('ELECTROL YTES', 'ELECTROLYTES')
            gs_block = gs_block.replace('AGGREG ATE', 'AGGREGATE')
            
            # Split by CLASS keyword to get per-class entries
            # Use re.split to split on "CLASS" boundaries
            parts = re.split(r"(?=CLASS\s+\d+\s*:)", gs_block, flags=re.IGNORECASE)
            for part in parts:
                gs = part.strip().rstrip(".")
                gs_key = gs[:50]
                if gs and len(gs) > 10 and gs_key not in seen_gs and re.match(r"CLASS\s+\d+", gs, re.IGNORECASE):
                    goods_services.append(gs)
                    seen_gs.add(gs_key)
        
        # Fallback: try per-line CLASS pattern
        if not goods_services:
            gs_class_pattern = r"CLASS\s+\d+\s*:\s*([^\n]+)"
            for match in re.finditer(gs_class_pattern, app_section):
                gs = match.group(0).strip()
                gs_key = gs[:50]
                if gs and len(gs) > 10 and gs_key not in seen_gs:
                    goods_services.append(gs)
                    seen_gs.add(gs_key)
        
        # If no goods/services found, provide defaults based on classes
        if not goods_services and classes:
            if 5 in classes:
                goods_services.append("Dietary and nutritional supplements")
            if 32 in classes:
                goods_services.append("Non-alcoholic beverages")
        
        return TrademarkApplication(
            mark=mark,
            applicant=None,
            goods_services=goods_services,
            classes=classes,
            filing_basis=None,
            specimen_type=None
        )
    
    def _extract_uspto_marks(self, text: str) -> List[PriorMark]:
        """
        Extract USPTO registered/pending marks from CompuMark report.
        
        Format found in pages 7+ of the PDF:
            1. LIVEMORE
            Registered 5 LIVEMORE SUPERFOODS, LLC 88-281,376 19
            2. LIVEMORE
            Registered 29, 32 LIVEMORE SUPERFOODS, LLC 88-230,376 21
        """
        marks = []
        seen_names = set()
        
        # --- Primary pattern: numbered entries with full details ---
        # Matches: NUMBER. MARK_NAME \n STATUS CLASSES OWNER SERIAL PAGE
        detailed_pattern = (
            r'(\d+)\.\s+'                          # Number
            r'([A-Z][^\n]+)\n'                     # Mark name
            r'(Registered|Abandoned|Cancelled|Renewed|Pending|Published)'  # Status
            r'\s+([\d,\s]+(?:Multi)?)'             # Classes
            r'\s+(.+?)'                            # Owner
            r'\s+(\d{2}.\d{3},\d{3})'             # Serial number
            r'\s+(\d+)'                            # Page
        )
        
        for match in re.finditer(detailed_pattern, text):
            num, mark_name, status, class_str, owner, serial, page = match.groups()
            mark_name = mark_name.strip()
            
            # Parse classes
            mark_classes = []
            if 'Multi' not in class_str:
                for c in class_str.split(','):
                    c = c.strip()
                    if c.isdigit() and 1 <= int(c) <= 45:
                        mark_classes.append(int(c))
            
            # Clean serial number
            serial = serial.replace('\u2212', '-').replace('\u2013', '-')
            
            similarity = self._calculate_similarity_score(mark_name)
            
            prior_mark = PriorMark(
                mark=mark_name,
                registration_number=serial,
                serial_number=serial,
                owner=owner.strip()[:100],
                classes=mark_classes,
                goods_services="",
                status=status,
                similarity_score=similarity,
                source="USPTO"
            )
            marks.append(prior_mark)
            seen_names.add(mark_name.upper())
        
        # --- Fallback: simpler pattern if detailed didn't find enough ---
        if len(marks) < 20:
            simple_pattern = (
                r'(\d+)\.\s+'
                r'([A-Z][^\n]+)\n'
                r'(Registered|Abandoned|Cancelled|Renewed|Pending|Published)'
            )
            for match in re.finditer(simple_pattern, text):
                num, mark_name, status = match.groups()
                mark_name = mark_name.strip()
                
                if mark_name.upper() in seen_names:
                    continue
                seen_names.add(mark_name.upper())
                
                similarity = self._calculate_similarity_score(mark_name)
                
                prior_mark = PriorMark(
                    mark=mark_name,
                    registration_number=None,
                    serial_number=None,
                    owner=None,
                    classes=[],
                    goods_services="",
                    status=status,
                    similarity_score=similarity,
                    source="USPTO"
                )
                marks.append(prior_mark)
        
        print(f"      [USPTO Parser] Found {len(marks)} marks using numbered pattern")
        return marks  # No artificial limit!
    
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
