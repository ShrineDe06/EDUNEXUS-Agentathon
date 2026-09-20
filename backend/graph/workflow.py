import logging
from langgraph.graph import StateGraph, START, END
from backend.graph.state import (
    EduNexusState,
    TOPIC_SELECTED,
    DIAGNOSTIC_GENERATION,
    AWAITING_ANSWERS,
    SCORING_DIAGNOSTIC,
    DIAGNOSIS,
    REMEDIATE,
    AWAITING_LEARNER_DECISION,
    VERIFY,
    SCORING_VERIFICATION,
    ADAPTIVE_STRATEGY,
    MASTERED,
    DEFERRED,
    UNRESOLVED_AFTER_LIMIT,
    NO_SUPPORTED_MISCONCEPTION
)

from backend.agents.diagnostic import DiagnosticAgent, DiagnosisAgent, DiagnosticAndDiagnosisAgent
from backend.agents.remediation import RemediationAgent
from backend.agents.verification import VerificationAgent
from backend.agents.adaptive_strategy import AdaptiveStrategyAgent

from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3

# Initialize logger
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("EDUNEXUS")

def is_answer_correct(ans, correct_ans, options=None):
    if ans is None or correct_ans is None:
        return False
    ans_str = str(ans).strip()
    correct_str = str(correct_ans).strip()

    if ans_str.lower() == correct_str.lower():
        return True

    if options and isinstance(options, list) and len(options) > 0:
        if ans_str.isdigit():
            idx = int(ans_str) - 1
            if 0 <= idx < len(options):
                opt_text = options[idx].strip()
                if opt_text.lower() == correct_str.lower():
                    return True
                if (correct_str == ans_str or 
                    correct_str.startswith(f"{ans_str}.") or 
                    correct_str.startswith(f"{ans_str})") or 
                    correct_str.lower() == f"option {ans_str}"):
                    return True

        if correct_str.isdigit():
            c_idx = int(correct_str) - 1
            if 0 <= c_idx < len(options):
                c_opt_text = options[c_idx].strip()
                if ans_str.lower() == c_opt_text.lower():
                    return True
                if ans_str.isdigit() and int(ans_str) - 1 == c_idx:
                    return True

    return False


def resolve_student_answer(ans, options=None):
    ans_str = str(ans).strip()
    if options and isinstance(options, list) and ans_str.isdigit():
        idx = int(ans_str) - 1
        if 0 <= idx < len(options):
            return f"Option {ans_str}: {options[idx]}"
    return ans_str

def create_workflow(llm, learner_memory, checkpointer=None):
    
    diagnostic_agent = DiagnosticAgent(llm)
    diagnosis_agent = DiagnosisAgent(llm)
    remediation_agent = RemediationAgent(llm)
    verification_agent = VerificationAgent(llm)
    adaptive_strategy_agent = AdaptiveStrategyAgent(llm)

    def check_budget(state: EduNexusState):
        calls = state.get("model_calls", 0)
        max_calls = state.get("max_model_calls", 14)
        if calls >= max_calls:
            raise RuntimeError("Model call budget exhausted.")

    def load_context_node(state: EduNexusState):
        student_id = state.get("student_id")
        topic = state.get("topic")
        
        learner_context = learner_memory.get_learner_context(student_id, topic)
        return {"learner_context": learner_context, "current_state": TOPIC_SELECTED}

    def diagnostic_node(state: EduNexusState):
        logger.info("[EDUNEXUS] DIAGNOSTIC_GENERATION")
        check_budget(state)
        
        topic = state["topic"]
        syllabus_context = state["syllabus_context"]
        learner_context = state.get("learner_context")
        
        response = diagnostic_agent.generate_questions(
            topic=topic,
            syllabus_context=syllabus_context,
            learner_context=learner_context
        )
        
        model_calls = state.get("model_calls", 0) + 1
        
        diagnostic_questions = [q.model_dump() for q in response.questions]
        
        return {
            "diagnostic_questions": diagnostic_questions,
            "diagnostic_thinking": getattr(response, "thinking_process", ""),
            "model_calls": model_calls,
            "current_state": AWAITING_ANSWERS
        }

    def score_diagnostic_node(state: EduNexusState):
        logger.info("[EDUNEXUS] SCORING_DIAGNOSTIC")
        questions = state.get("diagnostic_questions", [])
        answers = state.get("student_answers", [])
        student_id = state["student_id"]
        attempt_id = state["attempt_id"]
        topic = state["topic"]
        
        if len(questions) != len(answers):
            raise ValueError(f"Mismatch between questions ({len(questions)}) and answers ({len(answers)})")
            
        results = []
        correct_count = 0
        total = len(questions)
        
        learner_memory.create_attempt(attempt_id, student_id, topic)
        
        for q, ans in zip(questions, answers):
            correct_ans = q.get("correct_answer")
            options = q.get("options")
            is_correct = is_answer_correct(ans, correct_ans, options)
            resolved_ans = resolve_student_answer(ans, options)
            
            if is_correct:
                correct_count += 1
                
            res = {
                "question": q.get("question"),
                "sub_concept": q.get("sub_concept"),
                "student_answer": resolved_ans,
                "correct_answer": correct_ans,
                "is_correct": is_correct
            }
            results.append(res)
            
            learner_memory.save_question_result(
                attempt_id=attempt_id,
                sub_concept=q.get("sub_concept"),
                question=q.get("question"),
                student_answer=resolved_ans,
                correct_answer=str(correct_ans),
                is_correct=is_correct,
                question_id=None
            )
            
            learner_memory.update_subconcept_performance(
                student_id=student_id,
                topic=topic,
                sub_concept=q.get("sub_concept"),
                is_correct=is_correct
            )
            
        learner_memory.complete_attempt(attempt_id)
        
        score = correct_count / total if total > 0 else 0.0
        
        return {
            "diagnostic_results": results,
            "diagnostic_score": score,
            "current_state": DIAGNOSIS
        }

    def diagnosis_node(state: EduNexusState):
        logger.info("[EDUNEXUS] DIAGNOSIS")
        check_budget(state)
        
        topic = state["topic"]
        syllabus_context = state["syllabus_context"]
        diagnostic_questions = state.get("diagnostic_questions", [])
        student_answers = state.get("student_answers", [])
        diagnostic_results = state.get("diagnostic_results", [])
        learner_context = state.get("learner_context")
        
        response = diagnosis_agent.diagnose(
            topic=topic,
            syllabus_context=syllabus_context,
            question_results=diagnostic_results,
            learner_context=learner_context
        )
        
        model_calls = state.get("model_calls", 0) + 1
        
        valid_misconception = False
        if response.has_misconception:
            valid_misconception = True
            
        return {
            "diagnosis": response.model_dump(),
            "diagnosis_thinking": getattr(response, "thinking_process", ""),
            "misconception_found": valid_misconception,
            "model_calls": model_calls
        }
        
    def remediation_node(state: EduNexusState):
        logger.info("[EDUNEXUS] REMEDIATION")
        check_budget(state)
        
        topic = state["topic"]
        syllabus_context = state["syllabus_context"]
        diagnosis = state.get("diagnosis", {})
        learner_context = state.get("learner_context")
        
        previous_remediation = state.get("remediation", {})
        previous_intervention = previous_remediation.get("explanation", "") if previous_remediation else None
        
        new_strategy = state.get("previous_strategy")
        
        response = remediation_agent.remediate(
            topic=topic,
            syllabus_context=syllabus_context,
            diagnosis=diagnosis,
            learner_context=learner_context,
            previous_intervention=previous_intervention,
            adaptive_strategy=new_strategy
        )
        
        model_calls = state.get("model_calls", 0) + 1
        
        return {
            "remediation": response.model_dump(),
            "remediation_thinking": getattr(response, "thinking_process", ""),
            "model_calls": model_calls,
            "current_state": AWAITING_LEARNER_DECISION
        }
        
    def process_decision_node(state: EduNexusState):
        return {}

    def verification_node(state: EduNexusState):
        logger.info("[EDUNEXUS] VERIFY")
        check_budget(state)
        
        topic = state["topic"]
        syllabus_context = state["syllabus_context"]
        diagnosis = state.get("diagnosis", {})
        remediation = state.get("remediation", {})
        diagnostic_questions = state.get("diagnostic_questions", [])
        learner_context = state.get("learner_context")
        
        previous_question_ids = [q.get("question") for q in diagnostic_questions]
        
        response = verification_agent.generate_questions(
            topic=topic,
            syllabus_context=syllabus_context,
            diagnosis=diagnosis,
            remediation=remediation,
            previous_question_ids=previous_question_ids,
            learner_context=learner_context
        )
        
        model_calls = state.get("model_calls", 0) + 1
        verification_questions = [(q.model_dump() if hasattr(q, "model_dump") else q) for q in response.questions]

        return {
            "verification_questions": verification_questions,
            "verification_thinking": getattr(response, "thinking_process", ""),
            "model_calls": model_calls,
            "current_state": "AWAITING_VERIFICATION_ANSWERS"
        }

    def score_verification_node(state: EduNexusState):
        logger.info("[EDUNEXUS] SCORING_VERIFICATION")
        questions = state.get("verification_questions", [])
        answers = state.get("verification_answers", [])
        
        if len(questions) != len(answers):
            raise ValueError(f"Mismatch between verification questions ({len(questions)}) and answers ({len(answers)})")
            
        results = []
        correct_count = 0
        total = len(questions)
        
        for q, ans in zip(questions, answers):
            correct_ans = q.get("correct_answer")
            options = q.get("options")
            is_correct = is_answer_correct(ans, correct_ans, options)
            resolved_ans = resolve_student_answer(ans, options)
            
            if is_correct:
                correct_count += 1
                
            res = {
                "question": q.get("question"),
                "student_answer": resolved_ans,
                "correct_answer": correct_ans,
                "is_correct": is_correct
            }
            results.append(res)
            
        score = correct_count / total if total > 0 else 0.0
        passed = (correct_count == 2 and total == 2)
        
        return {
            "verification_results": results,
            "verification_score": score,
            "verification_passed": passed
        }

    def adaptive_strategy_node(state: EduNexusState):
        logger.info("[EDUNEXUS] ADAPTIVE_STRATEGY")
        check_budget(state)
        
        topic = state["topic"]
        syllabus_context = state["syllabus_context"]
        diagnosis = state.get("diagnosis", {})
        remediation = state.get("remediation", {})
        previous_remediation_text = remediation.get("explanation", "")
        
        verification_result = {
            "questions": [q.get("question") for q in state.get("verification_questions", [])],
            "student_answers": state.get("verification_answers", []),
            "correctness": state.get("verification_passed", False),
            "score": state.get("verification_score", 0.0),
            "evidence": "Verification failed."
        }
        learner_context = state.get("learner_context")
        
        remediation_cycle = state.get("remediation_cycle", 1)
        remediation_cycle += 1
        
        response = adaptive_strategy_agent.generate_strategy(
            topic=topic,
            syllabus_context=syllabus_context,
            diagnosis=diagnosis,
            previous_remediation=previous_remediation_text,
            verification_result=verification_result,
            learner_context=learner_context,
            remediation_cycle=remediation_cycle
        )
        
        model_calls = state.get("model_calls", 0) + 1
        
        return {
            "remediation_cycle": remediation_cycle,
            "previous_strategy": response.new_strategy,
            "model_calls": model_calls,
            "current_state": REMEDIATE
        }


    def route_after_diagnosis(state: EduNexusState):
        if state.get("misconception_found"):
            return "remediation"
        return NO_SUPPORTED_MISCONCEPTION

    def route_after_decision(state: EduNexusState):
        decision = state.get("learner_decision")
        if decision == "DEFER":
            logger.info("[EDUNEXUS] DEFERRED")
            return DEFERRED
        return "verification"

    def route_after_verification(state: EduNexusState):
        if state.get("verification_passed"):
            logger.info("[EDUNEXUS] MASTERED")
            return MASTERED
            
        cycle = state.get("remediation_cycle", 1)
        max_cycle = state.get("max_remediation_cycles", 2)
        
        if cycle < max_cycle:
            return "adaptive_strategy"
        else:
            logger.info("[EDUNEXUS] UNRESOLVED_AFTER_LIMIT")
            return UNRESOLVED_AFTER_LIMIT

    # Construct graph
    workflow = StateGraph(EduNexusState)
    
    workflow.add_node("load_context", load_context_node)
    workflow.add_node("diagnostic", diagnostic_node)
    workflow.add_node("score_diagnostic", score_diagnostic_node)
    workflow.add_node("diagnosis", diagnosis_node)
    workflow.add_node("remediation", remediation_node)
    workflow.add_node("process_decision", process_decision_node)
    workflow.add_node("verification", verification_node)
    workflow.add_node("score_verification", score_verification_node)
    workflow.add_node("adaptive_strategy", adaptive_strategy_node)

    workflow.add_edge(START, "load_context")
    workflow.add_edge("load_context", "diagnostic")
    workflow.add_edge("diagnostic", "score_diagnostic")
    workflow.add_edge("score_diagnostic", "diagnosis")
    
    workflow.add_conditional_edges(
        "diagnosis",
        route_after_diagnosis,
        {
            "remediation": "remediation",
            NO_SUPPORTED_MISCONCEPTION: END
        }
    )
    
    workflow.add_edge("remediation", "process_decision")
    
    workflow.add_conditional_edges(
        "process_decision", 
        route_after_decision, 
        {
            DEFERRED: END,
            "verification": "verification"
        }
    )
    
    workflow.add_edge("verification", "score_verification")
    
    workflow.add_conditional_edges(
        "score_verification",
        route_after_verification,
        {
            MASTERED: END,
            UNRESOLVED_AFTER_LIMIT: END,
            "adaptive_strategy": "adaptive_strategy"
        }
    )
    
    workflow.add_edge("adaptive_strategy", "remediation")

    return workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["score_diagnostic", "process_decision", "score_verification"]
    )
