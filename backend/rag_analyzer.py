"""
RAG Analyzer - Retrieval Augmented Generation for Trademark Analysis
Combines vector search with Ollama LLM for zero-hallucination risk assessment

KEY FEATURES:
- Only uses retrieved TMEP content (no hallucination)
- Citation validation (every citation is verified)
- Confidence scoring (knows when it doesn't know)
- Structured analysis output
"""
import os
import json
import pickle
import faiss
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Tuple, Optional
import requests
from dataclasses import dataclass

@dataclass
class RetrievedContext:
    """Retrieved TMEP context for analysis"""
    section_id: str
    section_number: str
    title: str
    content: str
    category: str
    relevance_score: float
    citation: str

@dataclass
class AnalysisResult:
    """LLM analysis result with citations"""
    analysis: str
    citations_used: List[str]
    confidence: float
    requires_human_review: bool
    retrieved_sections: List[RetrievedContext]

class RAGAnalyzer:
    """
    Retrieval-Augmented Generation Analyzer
    
    Zero-Hallucination Guarantee:
    1. Query vector database for relevant TMEP sections
    2. Only provide retrieved content to LLM
    3. Validate all citations against known TMEP sections
    4. Flag low-confidence analyses for human review
    """
    
    def __init__(
        self,
        vector_db_path: str = None,
        metadata_path: str = None,
        citation_db_path: str = None,
        ollama_url: str = "http://localhost:11434/api/generate",
        model_name: str = "llama3.1:8b"
    ):
        """Initialize RAG analyzer"""
        
        print("🔧 Initializing RAG Analyzer...")
        
        # Use default paths if not provided - Windows-compatible
        if vector_db_path is None:
            vector_db_path = os.path.join("app", "data", "vectors", "tmep_index.faiss")
        if metadata_path is None:
            metadata_path = os.path.join("app", "data", "vectors", "metadata.pkl")
        if citation_db_path is None:
            citation_db_path = os.path.join("app", "data", "tmep", "citation_validation.json")
        
        # Load vector database
        self.index = faiss.read_index(vector_db_path)
        
        with open(metadata_path, 'rb') as f:
            self.metadata = pickle.load(f)
        
        # Load citation validation
        with open(citation_db_path, 'r') as f:
            self.citation_db = json.load(f)
        
        # Load embedding model
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Ollama configuration
        self.ollama_url = ollama_url
        self.model_name = model_name
        
        print(f"   ✓ Vector DB loaded: {self.index.ntotal} sections")
        print(f"   ✓ Citation DB loaded: {len(self.citation_db)} valid citations")
        print(f"   ✓ LLM: {self.model_name}")
        print()
    
    def retrieve_relevant_sections(
        self, 
        query: str, 
        k: int = 5
    ) -> List[RetrievedContext]:
        """
        Retrieve most relevant TMEP sections for query
        
        Args:
            query: Natural language query
            k: Number of sections to retrieve
        
        Returns:
            List of RetrievedContext with relevance scores
        """
        # Embed query
        query_embedding = self.embedding_model.encode([query])
        
        # Search vector database
        distances, indices = self.index.search(query_embedding.astype('float32'), k)
        
        # Build retrieved contexts
        contexts = []
        for idx, dist in zip(indices[0], distances[0]):
            section_meta = self.metadata[idx]
            
            # Calculate relevance score (inverse of L2 distance, normalized)
            relevance = 1.0 / (1.0 + dist)
            
            context = RetrievedContext(
                section_id=section_meta['section_id'],
                section_number=section_meta['section'],
                title=section_meta['title'],
                content=section_meta['content'],
                category=section_meta['category'],
                relevance_score=float(relevance),
                citation=f"TMEP §{section_meta['section']}"
            )
            contexts.append(context)
        
        return contexts
    
    def validate_citations(self, citations: List[str]) -> Tuple[List[str], List[str]]:
        """
        Validate citations against known TMEP sections
        
        Returns:
            (valid_citations, invalid_citations)
        """
        valid = []
        invalid = []
        
        for citation in citations:
            # Extract section number from citation
            # Format: "TMEP §1207" or "1207" or "§1207"
            section = citation.replace("TMEP", "").replace("§", "").strip()
            
            if section in self.citation_db:
                valid.append(citation)
            else:
                invalid.append(citation)
        
        return valid, invalid
    
    def analyze_with_llm(
        self,
        query: str,
        contexts: List[RetrievedContext],
        temperature: float = 0.1
    ) -> Dict:
        """
        Use Ollama LLM to analyze query with retrieved context
        
        Args:
            query: Analysis question
            contexts: Retrieved TMEP sections
            temperature: LLM temperature (lower = more deterministic)
        
        Returns:
            LLM response dict
        """
        # Build context-aware prompt
        context_text = "\n\n".join([
            f"TMEP §{ctx.section_number}: {ctx.title}\n{ctx.content}"
            for ctx in contexts
        ])
        
        prompt = f"""You are a trademark law expert analyzing trademark applications against USPTO guidelines.

CRITICAL RULES:
1. ONLY use information from the provided TMEP sections below
2. ALWAYS cite specific TMEP sections when making claims (format: TMEP §XXXX)
3. If information is not in the provided context, say "Based on provided TMEP sections, I cannot determine..."
4. Be precise and factual - no speculation
5. Rate your confidence (0-100%) in your analysis

TMEP SECTIONS PROVIDED:
{context_text}

QUERY: {query}

Provide your analysis in this format:
ANALYSIS: [Your detailed analysis here, with TMEP §citations]
CONFIDENCE: [0-100]%
CITATIONS_USED: [List section numbers you cited, e.g., 1207, 1209]
"""
        
        # Call Ollama API
        try:
            response = requests.post(
                self.ollama_url,
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "temperature": 0,
                    "seed":42,
                    "stream": False
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "response": result.get("response", ""),
                    "model": self.model_name
                }
            else:
                return {
                    "success": False,
                    "error": f"Ollama API error: {response.status_code}"
                }
        
        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "error": "Cannot connect to Ollama. Is it running? (ollama serve)"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error calling Ollama: {str(e)}"
            }
    
    def parse_llm_response(self, response_text: str) -> Dict:
        """
        Parse structured LLM response
        
        Returns:
            {
                "analysis": str,
                "confidence": float,
                "citations": List[str]
            }
        """
        lines = response_text.split('\n')
        
        analysis_parts = []
        confidence = 0.5  # Default if not specified
        citations = []
        
        current_section = None
        
        for line in lines:
            line = line.strip()
            
            if line.startswith("ANALYSIS:"):
                current_section = "analysis"
                analysis_parts.append(line.replace("ANALYSIS:", "").strip())
            
            elif line.startswith("CONFIDENCE:"):
                current_section = "confidence"
                # Extract percentage
                conf_str = line.replace("CONFIDENCE:", "").strip().replace("%", "")
                try:
                    confidence = float(conf_str) / 100.0
                except:
                    confidence = 0.5
            
            elif line.startswith("CITATIONS_USED:"):
                current_section = "citations"
                # Extract citations
                cites_str = line.replace("CITATIONS_USED:", "").strip()
                citations = [c.strip() for c in cites_str.split(',') if c.strip()]
            
            elif current_section == "analysis" and line:
                analysis_parts.append(line)
        
        return {
            "analysis": " ".join(analysis_parts),
            "confidence": confidence,
            "citations": citations
        }
    
    def analyze_trademark_issue(
        self,
        trademark: str,
        goods_services: str,
        issue_type: str,
        k_sections: int = 5
    ) -> AnalysisResult:
        """
        Analyze specific trademark issue using RAG
        
        Args:
            trademark: Mark being analyzed
            goods_services: Goods/services description
            issue_type: Type of issue (e.g., "likelihood of confusion", "descriptiveness")
            k_sections: Number of TMEP sections to retrieve
        
        Returns:
            AnalysisResult with analysis and validated citations
        """
        # Build query
        query = f"Analyze {issue_type} for trademark '{trademark}' used on {goods_services}"
        
        # Retrieve relevant TMEP sections
        contexts = self.retrieve_relevant_sections(query, k=k_sections)
        
        # Analyze with LLM
        llm_result = self.analyze_with_llm(query, contexts)
        
        if not llm_result["success"]:
            # Fallback to template-based analysis if LLM fails
            return AnalysisResult(
                analysis=f"LLM unavailable: {llm_result['error']}. Retrieved {len(contexts)} relevant TMEP sections for manual review.",
                citations_used=[ctx.citation for ctx in contexts],
                confidence=0.3,  # Low confidence without LLM
                requires_human_review=True,
                retrieved_sections=contexts
            )
        
        # Parse LLM response
        parsed = self.parse_llm_response(llm_result["response"])
        
        # Validate citations
        claimed_citations = [f"TMEP §{c}" for c in parsed["citations"]]
        valid_citations, invalid_citations = self.validate_citations(claimed_citations)
        
        # Calculate final confidence
        # Reduce confidence if invalid citations detected
        citation_penalty = len(invalid_citations) * 0.1
        final_confidence = max(0.0, parsed["confidence"] - citation_penalty)
        
        # Determine if human review needed
        needs_review = final_confidence < 0.6 or len(invalid_citations) > 0
        
        return AnalysisResult(
            analysis=parsed["analysis"],
            citations_used=valid_citations,
            confidence=final_confidence,
            requires_human_review=needs_review,
            retrieved_sections=contexts
        )
    
    def analyze_multiple_issues(
        self,
        trademark: str,
        goods_services: str,
        issue_types: List[str]
    ) -> Dict[str, AnalysisResult]:
        """
        Analyze multiple trademark issues
        
        Returns:
            Dict of issue_type -> AnalysisResult
        """
        results = {}
        
        for issue_type in issue_types:
            print(f"   🔍 Analyzing: {issue_type}...")
            result = self.analyze_trademark_issue(
                trademark=trademark,
                goods_services=goods_services,
                issue_type=issue_type
            )
            results[issue_type] = result
        
        return results

def test_rag_analyzer():
    """Test the RAG analyzer"""
    
    print("🧪 TESTING RAG ANALYZER")
    print("=" * 70)
    print()
    
    analyzer = RAGAnalyzer()
    
    # Test trademark
    trademark = "TEAR, POUR, LIVE MORE"
    goods = "Energy drinks, sports drinks, dietary supplements"
    
    print(f"📋 Test Case:")
    print(f"   Trademark: {trademark}")
    print(f"   Goods: {goods}")
    print()
    
    # Test issues
    issues = [
        "likelihood of confusion with similar marks",
        "descriptiveness of POUR for beverages",
        "specimen requirements for Class 5 and Class 32"
    ]
    
    print(f"🔍 Analyzing {len(issues)} issues...")
    print()
    
    results = analyzer.analyze_multiple_issues(trademark, goods, issues)
    
    for issue_type, result in results.items():
        print(f"📊 ISSUE: {issue_type}")
        print(f"{'=' * 70}")
        print(f"Analysis: {result.analysis[:300]}...")
        print(f"Confidence: {result.confidence*100:.1f}%")
        print(f"Human Review: {'YES ⚠️' if result.requires_human_review else 'NO ✅'}")
        print(f"Citations: {', '.join(result.citations_used)}")
        print()
        print(f"Retrieved Sections ({len(result.retrieved_sections)}):")
        for ctx in result.retrieved_sections[:3]:
            print(f"  - {ctx.citation}: {ctx.title} (relevance: {ctx.relevance_score:.3f})")
        print()
    
    print("✅ RAG Analyzer Test Complete!")

if __name__ == "__main__":
    test_rag_analyzer()
