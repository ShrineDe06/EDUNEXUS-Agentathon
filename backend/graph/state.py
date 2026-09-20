from typing import TypedDict, List, Dict, Any, Optional

# Constants for Workflow States
TOPIC_SELECTED = "TOPIC_SELECTED"
DIAGNOSTIC_GENERATION = "DIAGNOSTIC_GENERATION"
AWAITING_ANSWERS = "AWAITING_ANSWERS"
SCORING_DIAGNOSTIC = "SCORING_DIAGNOSTIC"
DIAGNOSIS = "DIAGNOSIS"
REMEDIATE = "REMEDIATE"
AWAITING_LEARNER_DECISION = "AWAITING_LEARNER_DECISION"
VERIFY = "VERIFY"
SCORING_VERIFICATION = "SCORING_VERIFICATION"
ADAPTIVE_STRATEGY = "ADAPTIVE_STRATEGY"
MASTERED = "MASTERED"
DEFERRED = "DEFERRED"
UNRESOLVED_AFTER_LIMIT = "UNRESOLVED_AFTER_LIMIT"
NO_SUPPORTED_MISCONCEPTION = "NO_SUPPORTED_MISCONCEPTION"

class EduNexusState(TypedDict, total=False):
    # Session identity
    student_id: str
    topic: str
    attempt_id: str

    # Current workflow state
    current_state: str

    # Context
    syllabus_context: str
    learner_context: str

    # Diagnostic
    diagnostic_questions: List[Dict[str, Any]]
    student_answers: List[str]  # Or Dict, depending on frontend submission
    diagnostic_results: List[Dict[str, Any]]
    diagnostic_score: float

    # Diagnosis
    diagnosis: Dict[str, Any]
    misconception_found: bool

    # Remediation
    remediation: Dict[str, Any]
    learner_decision: str
    previous_strategy: str

    # Verification
    verification_questions: List[Dict[str, Any]]
    verification_answers: List[str]
    verification_results: List[Dict[str, Any]]
    verification_score: float
    verification_passed: bool

    # Adaptive loop
    remediation_cycle: int
    max_remediation_cycles: int

    # Model budget
    model_calls: int
    max_model_calls: int

    # Dynamic Agent Thinking Traces
    diagnostic_thinking: str
    diagnosis_thinking: str
    remediation_thinking: str
    verification_thinking: str
    adaptive_thinking: str
    final_status: str

    retry_count: int

    # Final state
    final_status: str
