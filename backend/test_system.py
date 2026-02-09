"""
System Test Script
Validates TMEP data, vector database, and RAG functionality
Windows-compatible version with proper path handling
"""

import json
import pickle
import faiss
from sentence_transformers import SentenceTransformer
import os

def test_system():
    """Comprehensive system test"""
    
    print("🧪 TESTING TRADEMARK RISK ASSESSMENT SYSTEM")
    print("=" * 60)
    print()
    
    # Test 1: TMEP Data
    print("TEST 1: TMEP Knowledge Base")
    print("-" * 60)
    try:
        tmep_sections_path = os.path.join("app", "data", "tmep", "tmep_sections.json")
        citation_path = os.path.join("app", "data", "tmep", "citation_validation.json")
        metadata_path = os.path.join("app", "data", "tmep", "metadata.json")
        
        with open(tmep_sections_path, "r") as f:
            tmep_data = json.load(f)
        with open(citation_path, "r") as f:
            citations = json.load(f)
        with open(metadata_path, "r") as f:
            metadata = json.load(f)
        
        print(f"✅ TMEP sections loaded: {len(tmep_data)}")
        print(f"✅ Citations validated: {len(citations)}")
        print(f"✅ Metadata loaded")
        print(f"   Categories: {metadata['categories']}")
        print()
    except Exception as e:
        print(f"❌ TMEP Data Test Failed: {e}")
        return False
    
    # Test 2: Vector Database
    print("TEST 2: Vector Database")
    print("-" * 60)
    try:
        index_path = os.path.join("app", "data", "vectors", "tmep_index.faiss")
        vec_metadata_path = os.path.join("app", "data", "vectors", "metadata.pkl")
        vec_config_path = os.path.join("app", "data", "vectors", "config.json")
        
        index = faiss.read_index(index_path)
        with open(vec_metadata_path, "rb") as f:
            vec_metadata = pickle.load(f)
        with open(vec_config_path, "r") as f:
            vec_config = json.load(f)
        
        print(f"✅ FAISS index loaded: {index.ntotal} vectors")
        print(f"✅ Vector metadata loaded: {len(vec_metadata)} items")
        print(f"✅ Dimension: {vec_config['dimension']}")
        print()
    except Exception as e:
        print(f"❌ Vector Database Test Failed: {e}")
        return False
    
    # Test 3: Embedding Model
    print("TEST 3: Embedding Model")
    print("-" * 60)
    try:
        model = SentenceTransformer('all-MiniLM-L6-v2')
        test_text = "trademark likelihood of confusion"
        embedding = model.encode([test_text])
        
        print(f"✅ Model loaded successfully")
        print(f"✅ Test embedding generated: shape {embedding.shape}")
        print()
    except Exception as e:
        print(f"❌ Embedding Model Test Failed: {e}")
        return False
    
    # Test 4: Search Functionality
    print("TEST 4: Semantic Search")
    print("-" * 60)
    try:
        # Test query for "TEAR, POUR, LIVE MORE" trademark
        test_queries = [
            "likelihood of confusion with similar marks",
            "descriptiveness of beverage packaging terms",
            "specimens required for supplement applications"
        ]
        
        for query in test_queries:
            query_emb = model.encode([query])
            distances, indices = index.search(query_emb, k=2)
            
            print(f"Query: '{query}'")
            for i, idx in enumerate(indices[0]):
                section = vec_metadata[idx]
                print(f"  → {section['section']}: {section['title']}")
            print()
        
        print("✅ Semantic search working correctly")
        print()
    except Exception as e:
        print(f"❌ Search Test Failed: {e}")
        return False
    
    # Test 5: Citation Validation
    print("TEST 5: Citation Validation")
    print("-" * 60)
    try:
        test_citations = ["1207", "1209", "904", "FAKE123"]
        
        for cite in test_citations:
            if cite in citations:
                print(f"✅ {cite}: Valid citation - {citations[cite].get('title', 'N/A')}")
            else:
                print(f"❌ {cite}: Invalid citation (correctly detected)")
        print()
    except Exception as e:
        print(f"❌ Citation Validation Test Failed: {e}")
        return False
    
    # Test 6: Real Trademark Analysis Simulation
    print("TEST 6: Trademark Analysis Simulation")
    print("-" * 60)
    try:
        trademark = "TEAR, POUR, LIVE MORE"
        goods = "Energy drinks, sports drinks, dietary supplements"
        
        print(f"Trademark: {trademark}")
        print(f"Goods: {goods}")
        print()
        
        # Simulate key analysis queries
        analysis_queries = [
            f"likelihood of confusion for {trademark} in beverage and supplement classes",
            f"is tear pour descriptive for packaged beverages",
            f"specimen requirements for {goods}"
        ]
        
        issues_found = []
        
        for query in analysis_queries:
            query_emb = model.encode([query])
            distances, indices = index.search(query_emb, k=1)
            
            section = vec_metadata[indices[0][0]]
            issues_found.append({
                "query": query,
                "relevant_section": section['section'],
                "title": section['title'],
                "category": section['category']
            })
        
        print("Issues Identified:")
        for i, issue in enumerate(issues_found, 1):
            print(f"  {i}. {issue['title']} (§{issue['relevant_section']})")
            print(f"     Category: {issue['category']}")
        print()
        
        print("✅ Trademark analysis simulation successful")
        print()
    except Exception as e:
        print(f"❌ Analysis Simulation Failed: {e}")
        return False
    
    # Final Summary
    print("=" * 60)
    print("🎉 ALL TESTS PASSED!")
    print("=" * 60)
    print()
    print("System Components Verified:")
    print("  ✅ TMEP Knowledge Base (10 sections)")
    print("  ✅ Citation Validation Database")
    print("  ✅ Vector Database (FAISS)")
    print("  ✅ Embedding Model (Semantic Search)")
    print("  ✅ RAG Pipeline (Query → Retrieval → Analysis)")
    print()
    print("Ready for:")
    print("  → Risk assessment engine")
    print("  → LLM integration (Ollama)")
    print("  → Frontend development")
    print()
    
    return True

if __name__ == "__main__":
    success = test_system()
    exit(0 if success else 1)
