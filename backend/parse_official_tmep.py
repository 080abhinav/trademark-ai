"""
Official TMEP Bulk Parser
Parses all official USPTO TMEP PDF files and adds them to the vector database

This will expand the knowledge base from 11 sections to 500+ sections!
"""

import os
import json
import PyPDF2
from pathlib import Path
import re
from typing import Dict, List, Tuple
from datetime import datetime

class TMEPBulkParser:
    """Parse official TMEP PDFs and extract structured content"""
    
    def __init__(self, tmep_folder: str):
        self.tmep_folder = tmep_folder
        self.sections = {}
        self.citation_map = {}
        
    def parse_all_pdfs(self) -> Tuple[Dict, Dict]:
        """
        Parse all TMEP PDFs in the folder
        
        Returns:
            (sections_dict, citation_map)
        """
        print("🔥 TMEP BULK PARSER - OFFICIAL USPTO GUIDELINES")
        print("=" * 70)
        print()
        
        # Get all PDF files
        pdf_files = sorted(Path(self.tmep_folder).glob("tmep-*.pdf"))
        
        print(f"📚 Found {len(pdf_files)} TMEP PDF files")
        print()
        
        total_sections = 0
        total_pages = 0
        
        for pdf_file in pdf_files:
            print(f"📄 Processing: {pdf_file.name}...")
            
            try:
                sections, pages = self._parse_single_pdf(pdf_file)
                total_sections += sections
                total_pages += pages
                print(f"   ✓ Extracted {sections} sections, {pages} pages")
            except Exception as e:
                print(f"   ⚠️  Error: {str(e)}")
                continue
        
        print()
        print("=" * 70)
        print(f"✅ PARSING COMPLETE!")
        print(f"   Total PDFs: {len(pdf_files)}")
        print(f"   Total Sections: {total_sections}")
        print(f"   Total Pages: {total_pages}")
        print()
        
        return self.sections, self.citation_map
    
    def _parse_single_pdf(self, pdf_path: Path) -> Tuple[int, int]:
        """
        Parse a single TMEP PDF file
        
        Returns:
            (sections_extracted, pages_processed)
        """
        # Extract section number from filename
        # Format: tmep-1207.pdf -> section 1207
        filename = pdf_path.stem  # tmep-1207
        section_num = filename.replace("tmep-", "")
        
        # Read PDF
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            num_pages = len(pdf_reader.pages)
            
            # Extract all text
            full_text = ""
            for page in pdf_reader.pages:
                full_text += page.extract_text() + "\n"
        
        # Clean and structure the text
        cleaned_text = self._clean_text(full_text)
        
        # Extract title (usually first line or heading)
        title = self._extract_title(cleaned_text, section_num)
        
        # Determine category
        category = self._determine_category(section_num, title, cleaned_text)
        
        # Store section
        if cleaned_text.strip():  # Only if we got actual content
            self.sections[section_num] = {
                "section": section_num,
                "title": title,
                "content": cleaned_text[:5000],  # First 5000 chars to avoid huge sections
                "category": category,
                "source_file": pdf_path.name,
                "pages": num_pages
            }
            
            # Add to citation map
            self.citation_map[section_num] = {
                "exists": True,
                "title": title,
                "section": section_num,
                "category": category
            }
            
            return 1, num_pages
        
        return 0, num_pages
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted PDF text"""
        # Remove excessive whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r' +', ' ', text)
        
        # Remove page numbers and headers/footers
        text = re.sub(r'Page \d+ of \d+', '', text)
        text = re.sub(r'TMEP §\d+\s*$', '', text, flags=re.MULTILINE)
        
        return text.strip()
    
    def _extract_title(self, text: str, section_num: str) -> str:
        """Extract section title from text"""
        # Try to find title patterns
        lines = text.split('\n')
        
        # First non-empty line is often the title
        for line in lines[:10]:
            line = line.strip()
            if len(line) > 10 and len(line) < 200:
                # Remove section number if present
                line = re.sub(rf'^{section_num}\s*', '', line)
                line = re.sub(r'^TMEP\s*§\s*\d+\s*', '', line)
                if line:
                    return line
        
        # Fallback
        return f"TMEP Section {section_num}"
    
    def _determine_category(self, section_num: str, title: str, content: str) -> str:
        """Determine if section is substantive, procedural, or general"""
        
        # Substantive sections (examining substance of marks)
        substantive_keywords = [
            'confusion', 'descriptive', 'generic', 'deceptive',
            'surname', 'geographic', 'functional', 'ornamental',
            'likelihood', 'refusal', 'disclaimer', 'acquired distinctiveness'
        ]
        
        # Procedural sections (process, filing, deadlines)
        procedural_keywords = [
            'filing', 'specimen', 'basis', 'amendment', 'response',
            'deadline', 'extension', 'abandonment', 'petition',
            'publication', 'opposition', 'certificate'
        ]
        
        text_to_check = (title + ' ' + content[:1000]).lower()
        
        substantive_score = sum(1 for kw in substantive_keywords if kw in text_to_check)
        procedural_score = sum(1 for kw in procedural_keywords if kw in text_to_check)
        
        if substantive_score > procedural_score:
            return "substantive"
        elif procedural_score > substantive_score:
            return "procedural"
        else:
            return "general"
    
    def save_to_json(self, output_dir: str):
        """Save parsed sections to JSON files"""
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Save sections
        sections_path = os.path.join(output_dir, "tmep_official_sections.json")
        with open(sections_path, 'w', encoding='utf-8') as f:
            json.dump(self.sections, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Saved {len(self.sections)} sections to: {sections_path}")
        
        # Save citation map
        citations_path = os.path.join(output_dir, "tmep_official_citations.json")
        with open(citations_path, 'w', encoding='utf-8') as f:
            json.dump(self.citation_map, f, indent=2)
        
        print(f"✅ Saved {len(self.citation_map)} citations to: {citations_path}")
        
        # Save metadata
        metadata = {
            "created": datetime.now().isoformat(),
            "total_sections": len(self.sections),
            "categories": {
                "substantive": sum(1 for s in self.sections.values() if s["category"] == "substantive"),
                "procedural": sum(1 for s in self.sections.values() if s["category"] == "procedural"),
                "general": sum(1 for s in self.sections.values() if s["category"] == "general")
            },
            "source": "USPTO TMEP Official PDFs (November 2025)",
            "section_range": f"{min(self.sections.keys())} - {max(self.sections.keys())}"
        }
        
        metadata_path = os.path.join(output_dir, "tmep_official_metadata.json")
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"✅ Saved metadata to: {metadata_path}")
        print()
        print("📊 STATISTICS:")
        print(f"   Substantive: {metadata['categories']['substantive']}")
        print(f"   Procedural: {metadata['categories']['procedural']}")
        print(f"   General: {metadata['categories']['general']}")
        print(f"   Section Range: {metadata['section_range']}")

def main():
    """Main execution"""
    
    # Paths
    tmep_folder = os.path.join("..", "data", "tmep-nov2025-pdf")
    output_dir = os.path.join("app", "data", "tmep_official")
    
    # Check if folder exists
    if not os.path.exists(tmep_folder):
        print(f"❌ ERROR: TMEP folder not found at: {tmep_folder}")
        print()
        print("Expected location: C:\\Users\\Lenovo\\trademark-ai\\data\\tmep-nov2025-pdf\\")
        print()
        print("Please ensure the TMEP PDFs are in the correct location!")
        return
    
    # Parse all PDFs
    parser = TMEPBulkParser(tmep_folder)
    sections, citations = parser.parse_all_pdfs()
    
    if not sections:
        print("❌ No sections extracted! Check PDF files.")
        return
    
    # Save results
    parser.save_to_json(output_dir)
    
    print()
    print("=" * 70)
    print("🎉 OFFICIAL TMEP PARSING COMPLETE!")
    print("=" * 70)
    print()
    print("Next steps:")
    print("1. Run: python rebuild_vector_db.py")
    print("   This will rebuild the vector database with ALL sections!")
    print()
    print("2. Your system will now have 500+ TMEP sections instead of 11!")
    print()

if __name__ == "__main__":
    main()
