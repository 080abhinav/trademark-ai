"""
Rebuild Vector Database
Rebuilds the vector database including official TMEP sections

Run this AFTER parse_official_tmep.py to include all official sections
"""

import json
import pickle
import os
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

def rebuild_vector_database():
    """Rebuild vector database with both original and official TMEP sections"""
    
    print("🔨 REBUILDING VECTOR DATABASE WITH OFFICIAL TMEP")
    print("=" * 70)
    print()
    
    # Load original sections
    print("📖 Loading original TMEP sections...")
    original_path = os.path.join("app", "data", "tmep", "tmep_sections.json")
    
    with open(original_path, "r", encoding="utf-8") as f:
        original_sections = json.load(f)
    
    # Convert to dict if list
    if isinstance(original_sections, list):
        orig_dict = {}
        for section in original_sections:
            section_id = section.get('section', section.get('section_id', 'unknown'))
            orig_dict[section_id] = section
        original_sections = orig_dict
    
    print(f"   ✓ Loaded {len(original_sections)} original sections")
    
    # Load official sections (if they exist)
    official_path = os.path.join("app", "data", "tmep_official", "tmep_official_sections.json")
    
    if os.path.exists(official_path):
        print("📚 Loading official TMEP sections...")
        with open(official_path, "r", encoding="utf-8") as f:
            official_sections = json.load(f)
        print(f"   ✓ Loaded {len(official_sections)} official sections")
    else:
        print("⚠️  No official sections found (run parse_official_tmep.py first)")
        official_sections = {}
    
    # Merge sections (official sections override original if same section number)
    print()
    print("🔄 Merging sections...")
    all_sections = {**original_sections, **official_sections}
    print(f"   ✓ Total sections: {len(all_sections)}")
    
    # Load citation maps
    original_citations_path = os.path.join("app", "data", "tmep", "citation_validation.json")
    with open(original_citations_path, "r") as f:
        original_citations = json.load(f)
    
    if os.path.exists(official_path):
        official_citations_path = os.path.join("app", "data", "tmep_official", "tmep_official_citations.json")
        with open(official_citations_path, "r") as f:
            official_citations = json.load(f)
        all_citations = {**original_citations, **official_citations}
    else:
        all_citations = original_citations
    
    print(f"   ✓ Total citations: {len(all_citations)}")
    print()
    
    # Initialize embedding model
    print("🤖 Loading embedding model...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    print("   ✓ Model loaded")
    print()
    
    # Prepare documents
    print("📝 Preparing documents...")
    documents = []
    metadata = []
    
    for section_id, section_data in all_sections.items():
        # Handle both data formats
        if isinstance(section_data, dict):
            section_num = section_data.get('section', section_id)
            title = section_data.get('title', 'Unknown')
            category = section_data.get('category', 'general')
            content = section_data.get('content', '')
        else:
            section_num = section_id
            title = 'Unknown'
            category = 'general'
            content = str(section_data)
        
        # Create searchable document
        doc_text = f"""
        Section {section_num}: {title}
        Category: {category}
        
        {content}
        """
        
        documents.append(doc_text.strip())
        metadata.append({
            "section_id": section_id,
            "section": section_num,
            "title": title,
            "category": category,
            "content": content[:2000],  # Limit for storage
            "related_sections": section_data.get("related_sections", []) if isinstance(section_data, dict) else []
        })
    
    print(f"   ✓ Prepared {len(documents)} documents")
    print()
    
    # Generate embeddings
    print("🧠 Generating embeddings...")
    print("   (This may take 2-5 minutes for 500+ sections)")
    embeddings = model.encode(documents, show_progress_bar=True, convert_to_numpy=True)
    print(f"   ✓ Generated {len(embeddings)} embeddings")
    print(f"   ✓ Dimension: {embeddings.shape[1]}")
    print()
    
    # Create FAISS index
    print("🔍 Building FAISS index...")
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings.astype('float32'))
    print(f"   ✓ Index built with {index.ntotal} vectors")
    print()
    
    # Save everything
    print("💾 Saving enhanced vector database...")
    vectors_dir = os.path.join("app", "data", "vectors")
    
    # Save FAISS index
    index_path = os.path.join(vectors_dir, "tmep_index.faiss")
    faiss.write_index(index, index_path)
    
    # Save metadata
    metadata_path = os.path.join(vectors_dir, "metadata.pkl")
    with open(metadata_path, "wb") as f:
        pickle.dump(metadata, f)
    
    # Save config
    config = {
        "model_name": "all-MiniLM-L6-v2",
        "dimension": int(dimension),
        "total_vectors": int(index.ntotal),
        "original_sections": len(original_sections),
        "official_sections": len(official_sections),
        "created": "2024"
    }
    config_path = os.path.join(vectors_dir, "config.json")
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    
    # Update citation database
    citations_path = os.path.join("app", "data", "tmep", "citation_validation.json")
    with open(citations_path, "w") as f:
        json.dump(all_citations, f, indent=2)
    
    print("   ✓ FAISS index saved")
    print("   ✓ Metadata saved")
    print("   ✓ Config saved")
    print("   ✓ Citations updated")
    print()
    
    print("=" * 70)
    print("🎉 VECTOR DATABASE REBUILT!")
    print("=" * 70)
    print(f"   📊 Total Sections: {index.ntotal}")
    print(f"   📚 Original: {len(original_sections)}")
    print(f"   📕 Official: {len(official_sections)}")
    print(f"   🎯 Dimension: {dimension}")
    print()
    
    # Test search
    print("🧪 Testing enhanced search...")
    test_query = "What are the DuPont factors for likelihood of confusion?"
    query_embedding = model.encode([test_query], convert_to_numpy=True)
    
    distances, indices = index.search(query_embedding.astype('float32'), k=3)
    
    print(f"   Query: '{test_query}'")
    print(f"   Top 3 results:")
    for i, (idx, dist) in enumerate(zip(indices[0], distances[0])):
        section = metadata[idx]
        print(f"      {i+1}. Section {section['section']}: {section['title']}")
        print(f"         Relevance: {1.0/(1.0+dist):.3f}")
    
    print()
    print("✅ Enhanced vector database ready!")
    print()
    print("Your RAG system now has access to:")
    print("   • Original curated sections (focused on risk assessment)")
    print("   • Official USPTO TMEP sections (comprehensive coverage)")
    print("   • 500+ total searchable sections")
    print()

if __name__ == "__main__":
    rebuild_vector_database()
