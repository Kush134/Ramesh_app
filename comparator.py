from __future__ import annotations
import re
import html
import json
import difflib
from dataclasses import dataclass, asdict
from typing import Optional, List, Tuple
import numpy as np

# ============================================================
# Data Classes
# ============================================================

@dataclass
class Chunk:
    chunk_id: int
    heading: str
    text: str
    embed_text: str

@dataclass
class ComparisonRow:
    index: int
    new_chunk_id: int
    old_chunk_id: Optional[int]
    new_heading: str
    old_heading: str
    new_text: str
    old_text: str
    score: float
    status: str

# ============================================================
# Text Cleaning
# ============================================================

def clean_text(value: str) -> str:
    value = value.replace("\u2013", "-").replace("\u2014", "-")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()

# ============================================================
# Embedding Cache and Model Loader
# ============================================================

_model = None
_embeddings_cache = {}  # Cache key: (doc_id, chunks_length), Value: np.ndarray (embeddings)

def load_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        # Load the sentence transformer model
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model

def get_embeddings_for_document(doc_id: int, chunks_data: List[dict], chunks_json_str: str) -> np.ndarray:
    """Caching helper to load or calculate document embeddings."""
    cache_key = (doc_id, len(chunks_json_str))
    if cache_key in _embeddings_cache:
        return _embeddings_cache[cache_key]

    if not chunks_data:
        return np.zeros((0, 384), dtype=np.float32)

    chunks = [
        Chunk(
            chunk_id=c["chunk_id"],
            heading=c["clause"],
            text=c["content"],
            embed_text=f"{c['clause']}\n\n{c['content']}"
        ) for c in chunks_data
    ]

    model = load_model()
    embeddings = model.encode(
        [c.embed_text for c in chunks],
        batch_size=64,
        show_progress_bar=False,
        normalize_embeddings=True
    )

    _embeddings_cache[cache_key] = embeddings
    return embeddings

# ============================================================
# Matching Engine Key Normalizer
# ============================================================

def extract_clause_id(heading: str) -> str:
    h = re.sub(r'\s+', ' ', heading).strip().lower()
    
    # Clause pattern matching e.g., 145.A.30, AMC1 145.A.30(e)
    clause_pat = r'(?:(amc|gm|car|rule|appendix|table|section|part)\s*([0-9a-z]*)\s*(?:to|no\s*\.?\s*[0-9]+(?:\s*to)?)?\s*)?(car\s*-?\s*)?([0-9]{3}(?:\s*\.\s*[0-9a-z]+)*(?:\s*\([a-z0-9]+\))*)'
    
    match = re.search(clause_pat, h)
    if match:
        cl_type = match.group(1) or 'car'
        cl_num = match.group(2) or ''
        cl_id = match.group(4)
        
        # Clean ID
        cl_id_norm = re.sub(r'\s+', '', cl_id)
        
        # Clean type
        if cl_type in ['car', 'rule', 'section', 'part']:
            cl_type = 'car'
            
        # Treat amc1 / amc as same, and gm1 / gm as same by clearing '1'
        if cl_num == '1':
            cl_num = ''
            
        key = f"{cl_type}:{cl_num}:{cl_id_norm}"
        key = re.sub(r':+', ':', key).strip(':')
        return key
        
    text_key = re.sub(r'[^a-z0-9]', '', h)
    return text_key

# ============================================================
# 4-Phase Matching Algorithm
# ============================================================

def compute_top_1_matches(
    new_chunks: List[Chunk], 
    new_embeds: np.ndarray, 
    old_chunks: List[Chunk], 
    old_embeds: np.ndarray
) -> List[dict]:
    if len(new_chunks) == 0 or len(old_chunks) == 0:
        return []
        
    old_by_idx = {i: c for i, c in enumerate(old_chunks)}
    
    matched_old_indices = set()
    matched_new_indices = set()
    
    matches_list = []
    
    # --- PHASE 1: Exact Normalized Key Matching ---
    old_keys_map = {}
    for i, c in enumerate(old_chunks):
        key = extract_clause_id(c.heading)
        old_keys_map.setdefault(key, []).append(i)
        
    for j, nc in enumerate(new_chunks):
        key = extract_clause_id(nc.heading)
        if key in old_keys_map:
            for o_idx in old_keys_map[key]:
                if o_idx not in matched_old_indices:
                    sim = float(new_embeds[j] @ old_embeds[o_idx].T)
                    matches_list.append({
                        "new_idx": j,
                        "old_idx": o_idx,
                        "score": sim,
                        "method": "exact_key"
                    })
                    matched_old_indices.add(o_idx)
                    matched_new_indices.add(j)
                    break

    # --- PHASE 2: Fuzzy Heading Match ---
    for j, nc in enumerate(new_chunks):
        if j in matched_new_indices:
            continue
        best_old_idx = -1
        best_ratio = 0.0
        for i, oc in enumerate(old_chunks):
            if i in matched_old_indices:
                continue
            ratio = difflib.SequenceMatcher(None, nc.heading.lower(), oc.heading.lower()).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_old_idx = i
                
        if best_ratio > 0.85:
            sim = float(new_embeds[j] @ old_embeds[best_old_idx].T)
            matches_list.append({
                "new_idx": j,
                "old_idx": best_old_idx,
                "score": sim,
                "method": f"fuzzy_heading_{best_ratio:.2f}"
            })
            matched_old_indices.add(best_old_idx)
            matched_new_indices.add(j)

    # --- PHASE 3: Semantic Embedding Similarity Matching ---
    sim_matrix = new_embeds @ old_embeds.T
    for j, nc in enumerate(new_chunks):
        if j in matched_new_indices:
            continue
        
        best_old_idx = -1
        best_sim = -1.0
        for i, oc in enumerate(old_chunks):
            if i in matched_old_indices:
                continue
            sim = float(sim_matrix[j, i])
            if sim > best_sim:
                best_sim = sim
                best_old_idx = i
                
        if best_old_idx != -1 and best_sim >= 0.70:
            matches_list.append({
                "new_idx": j,
                "old_idx": best_old_idx,
                "score": best_sim,
                "method": "semantic"
            })
            matched_old_indices.add(best_old_idx)
            matched_new_indices.add(j)

    # --- PHASE 4: Alignment Output (Interleaving) ---
    results = []
    used_old_for_rows = set()
    old_cursor = 0
    
    new_to_match = {m["new_idx"]: m for m in matches_list}
    
    for j, nc in enumerate(new_chunks):
        if j in new_to_match:
            m = new_to_match[j]
            o_idx = m["old_idx"]
            
            if o_idx > old_cursor:
                for i in range(old_cursor, o_idx):
                    if i not in matched_old_indices and i not in used_old_for_rows:
                        oc = old_by_idx[i]
                        results.append({
                            "match_idx": len(results),
                            "new_chunk_id": -1,
                            "new_heading": "",
                            "new_text": "",
                            "old_chunk_id": oc.chunk_id,
                            "old_heading": oc.heading,
                            "old_text": oc.text,
                            "similarity_score": 0.0
                        })
                        used_old_for_rows.add(i)
            oc = old_by_idx[o_idx]
            results.append({
                "match_idx": len(results),
                "new_chunk_id": nc.chunk_id,
                "new_heading": nc.heading,
                "new_text": nc.text,
                "old_chunk_id": oc.chunk_id,
                "old_heading": oc.heading,
                "old_text": oc.text,
                "similarity_score": round(m["score"], 4)
            })
            used_old_for_rows.add(o_idx)
            old_cursor = max(old_cursor, o_idx + 1)
        else:
            results.append({
                "match_idx": len(results),
                "new_chunk_id": nc.chunk_id,
                "new_heading": nc.heading,
                "new_text": nc.text,
                "old_chunk_id": None,
                "old_heading": "",
                "old_text": "",
                "similarity_score": 0.0
            })
            
    for i in range(old_cursor, len(old_chunks)):
        if i not in matched_old_indices and i not in used_old_for_rows:
            oc = old_by_idx[i]
            results.append({
                "match_idx": len(results),
                "new_chunk_id": -1,
                "new_heading": "",
                "new_text": "",
                "old_chunk_id": oc.chunk_id,
                "old_heading": oc.heading,
                "old_text": oc.text,
                "similarity_score": 0.0
            })
            used_old_for_rows.add(i)
            
    return results

# ============================================================
# DB Document Comparator API Wrapper
# ============================================================

def compare_db_documents_by_id(old_id: int, new_id: int) -> dict:
    from db_utils import get_document_by_id
    
    old_doc = get_document_by_id(old_id)
    new_doc = get_document_by_id(new_id)
    
    if not old_doc:
        return {"error": f"Old document ID {old_id} not found"}
    if not new_doc:
        return {"error": f"New document ID {new_id} not found"}
        
    old_chunks_str = old_doc.get("chunks")
    new_chunks_str = new_doc.get("chunks")
    
    # Friendly labels
    old_label = old_doc.get("car_series_part") or f"Doc {old_id}"
    old_ver = old_doc.get("issue_no_date") or ""
    new_label = new_doc.get("car_series_part") or f"Doc {new_id}"
    new_ver = new_doc.get("issue_no_date") or ""
    
    if not old_chunks_str:
        return {"error": f"Markdown chunks are not generated for document: {old_label} ({old_ver})"}
    if not new_chunks_str:
        return {"error": f"Markdown chunks are not generated for document: {new_label} ({new_ver})"}
        
    try:
        old_chunks_data = json.loads(old_chunks_str)
        new_chunks_data = json.loads(new_chunks_str)
    except Exception as e:
        return {"error": f"Failed to parse stored JSON chunks: {str(e)}"}
        
    # Get embeddings with in-memory caching
    old_embeds = get_embeddings_for_document(old_id, old_chunks_data, old_chunks_str)
    new_embeds = get_embeddings_for_document(new_id, new_chunks_data, new_chunks_str)
    
    # Map to Chunk instances for the matcher
    old_chunks = [
        Chunk(
            chunk_id=c["chunk_id"],
            heading=c["clause"],
            text=c["content"],
            embed_text=f"{c['clause']}\n\n{c['content']}"
        ) for c in old_chunks_data
    ]
    new_chunks = [
        Chunk(
            chunk_id=c["chunk_id"],
            heading=c["clause"],
            text=c["content"],
            embed_text=f"{c['clause']}\n\n{c['content']}"
        ) for c in new_chunks_data
    ]
    
    # Compute matches using the 4-phase algorithm
    matches = compute_top_1_matches(new_chunks, new_embeds, old_chunks, old_embeds)
    
    EXACT_THRESH = 0.98
    SIMILAR_THRESH = 0.75
    
    rows = []
    for idx, match in enumerate(matches, start=1):
        if match["new_chunk_id"] == -1:
            status = "REMOVED"
        elif match["old_chunk_id"] is None:
            status = "ADDED"
        elif match["similarity_score"] >= EXACT_THRESH:
            status = "UNCHANGED"
        elif match["similarity_score"] >= SIMILAR_THRESH:
            status = "CHANGED"
        else:
            status = "CHANGED"
            
        rows.append({
            "index": idx,
            "new_chunk_id": match["new_chunk_id"],
            "old_chunk_id": match["old_chunk_id"],
            "new_heading": match["new_heading"],
            "old_heading": match["old_heading"],
            "new_text": match["new_text"],
            "old_text": match["old_text"],
            "score": match["similarity_score"],
            "status": status,
        })
        
    return {"comparison": rows}