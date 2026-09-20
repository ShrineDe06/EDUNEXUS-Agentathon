import json
from typing import Dict, Any, Optional

def search_syllabus_rag(query: str, syllabus_memory=None) -> Dict[str, Any]:
    """
    Tool: Search Syllabus RAG Vector Memory.
    Checks whether the query is relevant to the ingested PDF syllabus.
    Returns syllabus_context and boolean indicating if RAG document was relevant.
    """
    if not syllabus_memory or not hasattr(syllabus_memory, "retrieve"):
        return {"relevant": False, "context": "No syllabus vector index loaded. Using general knowledge."}
        
    context = syllabus_memory.retrieve(query=query, top_k=2)
    
    # Check if retrieved context is empty, trivial, or completely unrelated
    if not context or "no syllabus context" in context.lower() or len(context.strip()) < 20:
        return {
            "relevant": False,
            "context": "NO_RELEVANT_RAG_CONTEXT: Topic does not match uploaded syllabus document. Relying on core knowledge."
        }
        
    return {
        "relevant": True,
        "context": context
    }


def get_student_progress(student_id: str, topic: str, learner_memory=None) -> Dict[str, Any]:
    """
    Tool: Get Student Progress & Historical Misconceptions from SQLAlchemy Database.
    Fetches past accuracy, weak sub-concepts, active misconceptions, and previous intervention cycles.
    """
    if not learner_memory or not hasattr(learner_memory, "get_learner_context"):
        return {
            "has_history": False,
            "learner_context": "No historical database connected."
        }
        
    context_str = learner_memory.get_learner_context(student_id, topic)
    perf_data = learner_memory.get_topic_performance(student_id, topic)
    
    weak_subconcepts = [sc for sc, data in perf_data.items() if data.get("status") == "weak"]
    
    return {
        "has_history": bool(perf_data),
        "weak_subconcepts": weak_subconcepts,
        "topic_performance": perf_data,
        "learner_context": context_str
    }
