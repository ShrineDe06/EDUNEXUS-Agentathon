import re
from typing import Any, Dict, List


def is_explicit_document_request(query: str) -> bool:
    patterns = [
        r"\b(?:this|the|my|our|uploaded|attached)\s+(?:document|file|pdf|attachment|notes?|text)\b",
        r"\b(?:document|file|pdf|attachment|notes?)\s+(?:i|we)\s+(?:uploaded|attached)\b",
        r"\baccording to\s+(?:this|the|my|our)\s+(?:document|file|pdf|notes?)\b",
        r"\b(?:page|section)\s+\d+\b",
    ]
    return any(re.search(pattern, query.lower()) for pattern in patterns)


def select_relevant_document_chunks(
    metadata: List[Dict[str, Any]],
    scores,
    indices,
    allowed_documents: List[str],
    query: str,
    explicit_document_request: bool = False,
    threshold: float = 0.42,
    limit: int = 5,
) -> List[str]:
    """Select relevant chunks without allowing content from another chat."""
    allowed = set(allowed_documents)
    generic_terms = {
        "about", "answer", "could", "define", "describe", "does", "explain",
        "give", "help", "how", "learn", "mean", "please", "show", "tell",
        "that", "this", "what", "when", "where", "which", "with", "work",
        "works", "would", "you", "your",
    }
    query_terms = {
        token for token in re.findall(r"[a-z0-9]+", query.lower())
        if len(token) >= 3 and token not in generic_terms
    }

    def has_topic_overlap(text: str) -> bool:
        if explicit_document_request:
            return True
        text_terms = set(re.findall(r"[a-z0-9]+", text.lower()))
        for query_term in query_terms:
            if query_term in text_terms:
                return True
            if len(query_term) >= 5 and any(
                text_term.startswith(query_term[:5]) or query_term.startswith(text_term[:5])
                for text_term in text_terms if len(text_term) >= 5
            ):
                return True
        return False

    relevant = []
    for score, index in zip(scores, indices):
        index = int(index)
        if index < 0 or index >= len(metadata) or float(score) < threshold:
            continue
        item = metadata[index]
        if item.get("document") not in allowed or not has_topic_overlap(item.get("text", "")):
            continue
        relevant.append(item["text"])
        if len(relevant) == limit:
            break
    return relevant
