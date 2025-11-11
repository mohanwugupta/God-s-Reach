"""
Text chunking module for RAG-based retrieval.
Chunks text blocks by token budget while preserving page and box coordinates.
"""
from typing import List, Dict, Any, Tuple

# Lazy import with fallback for offline environments
def get_tiktoken_encoding():
    """Get tiktoken encoding with offline fallback."""
    try:
        import tiktoken
        return tiktoken.get_encoding("cl100k_base")
    except Exception as e:
        # Fallback: use simple token approximation (words * 1.3)
        import logging
        logging.warning(f"tiktoken encoding unavailable ({e}), using word-based approximation")
        return None


def chunk_blocks(blocks: List[Tuple], model_ctx: int = 6000) -> List[Dict[str, Any]]:
    """
    Chunk text blocks into smaller pieces with token limits.

    Args:
        blocks: List of block tuples from PyMuPDF: [(x0, y0, x1, y1, text, block_no, ...)]
        model_ctx: Maximum tokens per chunk

    Returns:
        List of chunks: [{"text": str, "box": (x0, y0, x1, y1), "page": int, "block_no": int}]
    """
    enc = get_tiktoken_encoding()
    chunks = []

    for block in blocks:
        if len(block) < 5:
            continue
        x0, y0, x1, y1, text, block_no = block[:6]
        page = getattr(block, 'page', 1)  # Assume page is set elsewhere

        if not text or not text.strip():
            continue

        # Tokenize the text
        if enc is not None:
            try:
                toks = enc.encode(text)
            except Exception:
                # Fallback to word-based approximation
                toks = text.split()
        else:
            # Word-based approximation
            toks = text.split()

        # Split into chunks if too long
        for i in range(0, len(toks), model_ctx):
            sub_toks = toks[i:i + model_ctx]
            if enc is not None:
                try:
                    sub_text = enc.decode(sub_toks)
                except Exception:
                    sub_text = ' '.join(sub_toks) if isinstance(sub_toks[0], str) else text[i:i+model_ctx]
            else:
                sub_text = ' '.join(sub_toks)
            
            chunks.append({
                "text": sub_text,
                "box": (x0, y0, x1, y1),
                "page": page,
                "block_no": block_no
            })

    return chunks


def chunk_text_by_tokens(text: str, max_tokens: int = 1000, overlap: int = 100) -> List[str]:
    """
    Simple text chunking by tokens with overlap.

    Args:
        text: Input text
        max_tokens: Maximum tokens per chunk
        overlap: Token overlap between chunks

    Returns:
        List of text chunks
    """
    enc = get_tiktoken_encoding()
    
    if enc is not None:
        try:
            toks = enc.encode(text)
        except Exception:
            # Fallback to word-based
            toks = text.split()
    else:
        toks = text.split()
    
    chunks = []

    start = 0
    while start < len(toks):
        end = min(start + max_tokens, len(toks))
        chunk_toks = toks[start:end]
        
        if enc is not None:
            try:
                chunk_text = enc.decode(chunk_toks)
            except Exception:
                chunk_text = ' '.join(chunk_toks) if isinstance(chunk_toks[0], str) else text[start:end]
        else:
            chunk_text = ' '.join(chunk_toks)
        
        chunks.append(chunk_text)
        start = end - overlap if end < len(toks) else end

    return chunks
