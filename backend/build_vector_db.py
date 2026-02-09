"""
Vector Database Builder
Creates FAISS index for semantic search with citation validation
Windows-compatible version with proper path handling
"""

import json
import pickle
import os
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

def build_vector_database():
    """Build FAISS vector database from TMEP sections"""
    
    print("🔨 Building Vector Database...")
    print()
    
    # Load TMEP data - Windows-compatible paths
    print("📖 Loading TMEP sections...")
    tmep_path = os.path.join("app", "data", "tmep", "tmep_sections.json")
    citation_path = os.path.join("app", "data", "tmep", "citation_validation.json")
    
    with open(tmep_path, "r", encoding="utf-8") as f:
        tmep_sections = json.load(f)
    
    # Handle both list and dict formats
    if isinstance(tmep_sections, list):
        # Convert list to dict format
        tmep_dict = {}
        for section in tmep_sections:
            section_id = section.get('section', section.get('section_id', 'unknown'))
            tmep_dict[section_id] = section
        tmep_sections = tmep_dict
    
    # Load citation validation
    with open(citation_path, "r", encoding="utf-8") as f:
        citation_map = json.load(f)
    
    print(f"   ✓ Loaded {len(tmep_sections)} sections")
    print()
    
    # Initialize embedding model
    print("🤖 Loading embedding model...")
    model = SentenceTransformer('all-MiniLM-L6-v2')  # Fast, good quality
    print("   ✓ Model loaded")
    print()
    
    # Prepare documents for embedding
    print("📝 Preparing documents...")
    documents = []
    metadata = []
    
    for section_id, section_data in tmep_sections.items():
        # Handle both old and new data formats
        if isinstance(section_data, dict):
            section_num = section_data.get('section', section_data.get('section_number', section_id))
            title = section_data.get('title', 'Unknown')
            category = section_data.get('category', 'general')
            content = section_data.get('content', '')
        else:
            # Fallback if data format is unexpected
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
            "content": content,
            "related_sections": section_data.get("related_sections", []) if isinstance(section_data, dict) else []
        })
    
    print(f"   ✓ Prepared {len(documents)} documents")
    print()
    
    # Generate embeddings
    print("🧠 Generating embeddings (this takes ~30 seconds)...")
    embeddings = model.encode(documents, show_progress_bar=True, convert_to_numpy=True)
    print(f"   ✓ Generated {len(embeddings)} embeddings")
    print(f"   ✓ Dimension: {embeddings.shape[1]}")
    print()
    
    # Create FAISS index
    print("🔍 Building FAISS index...")
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)  # L2 distance for similarity
    index.add(embeddings.astype('float32'))
    print(f"   ✓ Index built with {index.ntotal} vectors")
    print()
    
    # Save everything - Windows-compatible paths
    print("💾 Saving vector database...")
    vectors_dir = os.path.join("app", "data", "vectors")
    os.makedirs(vectors_dir, exist_ok=True)
    
    # Save FAISS index
    index_path = os.path.join(vectors_dir, "tmep_index.faiss")
    faiss.write_index(index, index_path)
    
    # Save metadata
    metadata_path = os.path.join(vectors_dir, "metadata.pkl")
    with open(metadata_path, "wb") as f:
        pickle.dump(metadata, f)
    
    # Save model name for consistency
    config = {
        "model_name": "all-MiniLM-L6-v2",
        "dimension": int(dimension),
        "total_vectors": int(index.ntotal),
        "created": "2024"
    }
    config_path = os.path.join(vectors_dir, "config.json")
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    
    print("   ✓ FAISS index saved")
    print("   ✓ Metadata saved")
    print("   ✓ Config saved")
    print()
    
    print("✅ Vector Database Complete!")
    print(f"   📊 {index.ntotal} searchable sections")
    print(f"   🎯 {dimension}-dimensional embeddings")
    print(f"   📁 Saved to {vectors_dir}")
    print()
    
    # Test the index
    print("🧪 Testing search capability...")
    test_query = "What are the requirements for likelihood of confusion?"
    query_embedding = model.encode([test_query], convert_to_numpy=True)
    
    # Search top 3 results
    k = 3
    distances, indices = index.search(query_embedding.astype('float32'), k)
    
    print(f"   Query: '{test_query}'")
    print(f"   Top {k} results:")
    for i, (idx, dist) in enumerate(zip(indices[0], distances[0])):
        section = metadata[idx]
        print(f"      {i+1}. Section {section['section']}: {section['title']}")
        print(f"         Distance: {dist:.4f}")
    
    print()
    print("🎉 All systems ready for RAG!")

if __name__ == "__main__":
    build_vector_database()
