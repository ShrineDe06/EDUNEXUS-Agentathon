"""
EDUNEXUS Backend Audit Test Suite
=================================
Executes every major path through the LangGraph workflow using deterministic mocks.
Captures state traces, validates scoring, cycle limits, budget, and routing.
"""
import os
import sys
import sqlite3
import json
import traceback
from typing import Optional, List, Dict, Any

# ---------------------------------------------------------------------------
# Mock classes
# ---------------------------------------------------------------------------

class MockAgentResponse:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
    def model_dump(self):
        return {k: v for k, v in self.__dict__.items()}

class MockQuestion:
    def __init__(self, q, sub, correct, options=None):
        self.question = q
        self.sub_concept = sub
        self.correct_answer = correct
        self.options = options
    def model_dump(self):
        return self.__dict__.copy()

class MockLLM:
    pass

class MockDiagnosticAgent:
    def generate_questions(self, *args, **kwargs):
        return MockAgentResponse(questions=[
            MockQuestion("What is index 0 of [10,20,30]?", "Indexing", "10",
                         options=["10", "20", "30", "0"]),
            MockQuestion("What is index 2 of [10,20,30]?", "Indexing", "30",
                         options=["10", "20", "30", "2"]),
            MockQuestion("How do you traverse an array?", "Traversal", "for loop",
                         options=["for loop", "while only", "goto", "print"]),
            MockQuestion("What does arr[1] return in [10,20,30]?", "Indexing", "20",
                         options=["10", "20", "30", "1"]),
            MockQuestion("What is the length of [10,20,30]?", "Traversal", "3",
                         options=["2", "3", "4", "0"]),
        ])

class ConfigurableDiagnosisAgent:
    def __init__(self, has_misc=True, affected=None):
        self.has_misc = has_misc
        self.affected = affected or (["Q1", "Q2"] if has_misc else [])
    def diagnose(self, *args, **kwargs):
        return MockAgentResponse(
            has_misconception=self.has_misc,
            sub_concept="Indexing",
            misconception="Confuses index with value",
            evidence=["Q1 wrong", "Q2 wrong"],
            confidence=0.9 if self.has_misc else 0.1,
            affected_question_ids=self.affected
        )

class MockRemediationAgent:
    def remediate(self, *args, **kwargs):
        return MockAgentResponse(
            sub_concept="Indexing",
            misconception="Confuses index with value",
            explanation="An index is the position, not the value.",
            example="arr[0] = 10, arr[1] = 20",
            key_takeaway="Index != Value",
            check_question="What is arr[2] in [5,10,15]?"
        )

class MockVerificationAgent:
    def generate_questions(self, *args, **kwargs):
        return MockAgentResponse(questions=[
            MockQuestion("What is arr[0] in [5,10,15]?", "Indexing", "5",
                         options=["0", "5", "10", "15"]),
            MockQuestion("What is arr[2] in [5,10,15]?", "Indexing", "15",
                         options=["5", "10", "15", "2"]),
        ])

class MockAdaptiveStrategyAgent:
    def generate_strategy(self, *args, **kwargs):
        return MockAgentResponse(
            cycle_limit_reached=False,
            new_strategy="Concrete analogy + visual representation",
            rationale="Previous conceptual explanation was insufficient",
            sub_concept="Indexing",
            misconception="Confuses index with value"
        )

# ---------------------------------------------------------------------------
# Test infrastructure
# ---------------------------------------------------------------------------

results = []

def patch_workflow(has_misc=True, affected=None):
    import backend.graph.workflow as wf
    wf.DiagnosticAgent = lambda llm: MockDiagnosticAgent()
    wf.DiagnosisAgent = lambda llm: ConfigurableDiagnosisAgent(has_misc, affected)
    wf.RemediationAgent = lambda llm: MockRemediationAgent()
    wf.VerificationAgent = lambda llm: MockVerificationAgent()
    wf.AdaptiveStrategyAgent = lambda llm: MockAdaptiveStrategyAgent()

def create_test_workflow(has_misc=True, affected=None):
    from backend.memory.learner_memory import LearnerMemory
    from langgraph.checkpoint.sqlite import SqliteSaver

    patch_workflow(has_misc, affected)
    import backend.graph.workflow as wf

    learner_memory = LearnerMemory(db_path=":memory:")
    learner_memory.create_student("student_1")

    conn = sqlite3.connect(":memory:", check_same_thread=False)
    saver = SqliteSaver(conn)
    workflow = wf.create_workflow(MockLLM(), learner_memory, checkpointer=saver)
    return workflow, learner_memory, conn

def make_config(thread_id="test"):
    return {"configurable": {"thread_id": thread_id}}

def record(test_name, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    results.append({"test": test_name, "status": status, "detail": detail})
    icon = "+" if passed else "X"
    print(f"  [{icon}] {test_name}" + (f" -- {detail}" if detail and not passed else ""))

# ---------------------------------------------------------------------------
# TESTS
# ---------------------------------------------------------------------------

def test_01_no_misconception():
    print("\n" + "="*70)
    print("TEST 01: No misconception (all correct)")
    print("="*70)
    trace = []
    workflow, lm, conn = create_test_workflow(has_misc=False)
    config = make_config("t01")
    initial = {
        "student_id": "student_1", "topic": "Arrays", "attempt_id": "att_01",
        "syllabus_context": "Arrays store elements.", "max_remediation_cycles": 2, "max_model_calls": 14
    }
    for ev in workflow.stream(initial, config):
        for k in ev: trace.append(k)
    workflow.update_state(config, {"student_answers": ["1", "3", "1", "2", "2"]})
    for ev in workflow.stream(None, config):
        for k in ev: trace.append(k)
    state = workflow.get_state(config).values
    record("No-misconception routing", not state.get("misconception_found"),
           f"misconception_found={state.get('misconception_found')}")
    record("Graph terminated at END", workflow.get_state(config).next == (),
           f"next={workflow.get_state(config).next}")
    node_trace = [t for t in trace if t != '__interrupt__']
    record("State trace no-misc", node_trace == ["load_context", "diagnostic", "score_diagnostic", "diagnosis"],
           f"trace={trace}")
    print(f"  Observed trace: {trace}")



def test_02_one_isolated_wrong():
    print("\n" + "="*70)
    print("TEST 02: One isolated wrong answer (diagnosis says no misconception)")
    print("="*70)
    trace = []
    workflow, lm, conn = create_test_workflow(has_misc=False)
    config = make_config("t02")
    initial = {
        "student_id": "student_1", "topic": "Arrays", "attempt_id": "att_02",
        "syllabus_context": "Arrays.", "max_remediation_cycles": 2, "max_model_calls": 14
    }
    for ev in workflow.stream(initial, config):
        for k in ev: trace.append(k)
    workflow.update_state(config, {"student_answers": ["1", "3", "WRONG", "2", "2"]})
    for ev in workflow.stream(None, config):
        for k in ev: trace.append(k)
    state = workflow.get_state(config).values
    score = state.get("diagnostic_score", -1)
    record("Scoring deterministic (4/5=0.8)", abs(score - 0.8) < 0.01, f"score={score}")
    record("No misconception flagged", not state.get("misconception_found"))
    print(f"  Observed trace: {trace}")


def test_03_misconception_detected_revise_pass():
    print("\n" + "="*70)
    print("TEST 03: Misconception -> Revise -> Verification Pass -> MASTERED")
    print("="*70)
    trace = []
    workflow, lm, conn = create_test_workflow(has_misc=True)
    config = make_config("t03")
    initial = {
        "student_id": "student_1", "topic": "Arrays", "attempt_id": "att_03",
        "syllabus_context": "Arrays.", "max_remediation_cycles": 2, "max_model_calls": 14
    }
    for ev in workflow.stream(initial, config):
        for k in ev: trace.append(k)
    workflow.update_state(config, {"student_answers": ["WRONG", "WRONG", "1", "WRONG", "2"]})
    for ev in workflow.stream(None, config):
        for k in ev: trace.append(k)
    state = workflow.get_state(config).values
    record("Misconception found", state.get("misconception_found") == True)
    record("Remediation generated", "remediation" in state and state["remediation"].get("explanation") is not None)
    workflow.update_state(config, {"learner_decision": "REVISE"})
    for ev in workflow.stream(None, config):
        for k in ev: trace.append(k)
    workflow.update_state(config, {"verification_answers": ["2", "3"]})
    for ev in workflow.stream(None, config):
        for k in ev: trace.append(k)
    state = workflow.get_state(config).values
    record("Verification passed (2/2)", state.get("verification_passed") == True, f"passed={state.get('verification_passed')}")
    record("Graph ended (MASTERED)", workflow.get_state(config).next == (),
           f"next={workflow.get_state(config).next}")
    print(f"  Observed trace: {trace}")


def test_04_misconception_defer():
    print("\n" + "="*70)
    print("TEST 04: Misconception -> DEFER")
    print("="*70)
    trace = []
    workflow, lm, conn = create_test_workflow(has_misc=True)
    config = make_config("t04")
    initial = {
        "student_id": "student_1", "topic": "Arrays", "attempt_id": "att_04",
        "syllabus_context": "Arrays.", "max_remediation_cycles": 2, "max_model_calls": 14
    }
    for ev in workflow.stream(initial, config):
        for k in ev: trace.append(k)
    workflow.update_state(config, {"student_answers": ["WRONG", "WRONG", "1", "WRONG", "2"]})
    for ev in workflow.stream(None, config):
        for k in ev: trace.append(k)
    workflow.update_state(config, {"learner_decision": "DEFER"})
    for ev in workflow.stream(None, config):
        for k in ev: trace.append(k)
    state = workflow.get_state(config).values
    at_end = workflow.get_state(config).next == ()
    record("DEFER routes to END", at_end, f"next={workflow.get_state(config).next}")
    record("Not marked mastered", state.get("verification_passed") != True)
    print(f"  Observed trace: {trace}")


def test_05_verification_fail_adaptive_then_mastered():
    print("\n" + "="*70)
    print("TEST 05: Verification FAIL -> Adaptive Strategy -> 2nd Remediation -> MASTERED")
    print("="*70)
    trace = []
    workflow, lm, conn = create_test_workflow(has_misc=True)
    config = make_config("t05")
    initial = {
        "student_id": "student_1", "topic": "Arrays", "attempt_id": "att_05",
        "syllabus_context": "Arrays.", "max_remediation_cycles": 2, "max_model_calls": 14
    }
    for ev in workflow.stream(initial, config):
        for k in ev: trace.append(k)
    workflow.update_state(config, {"student_answers": ["WRONG", "WRONG", "1", "WRONG", "2"]})
    for ev in workflow.stream(None, config):
        for k in ev: trace.append(k)
    workflow.update_state(config, {"learner_decision": "REVISE"})
    for ev in workflow.stream(None, config):
        for k in ev: trace.append(k)
    # Verification cycle 1: 1/2 FAIL
    workflow.update_state(config, {"verification_answers": ["2", "WRONG"]})
    for ev in workflow.stream(None, config):
        for k in ev: trace.append(k)
    state = workflow.get_state(config).values
    record("Verification failed (1/2)", state.get("verification_passed") == False,
           f"passed={state.get('verification_passed')}, score={state.get('verification_score')}")
    record("Adaptive strategy executed", "adaptive_strategy" in trace)
    record("Second remediation generated", trace.count("remediation") >= 2,
           f"remediation count={trace.count('remediation')}")
    # Revise again
    workflow.update_state(config, {"learner_decision": "REVISE"})
    for ev in workflow.stream(None, config):
        for k in ev: trace.append(k)
    # Verification cycle 2: 2/2 PASS
    workflow.update_state(config, {"verification_answers": ["2", "3"]})
    for ev in workflow.stream(None, config):
        for k in ev: trace.append(k)
    state = workflow.get_state(config).values
    record("Mastered after cycle 2", state.get("verification_passed") == True)
    record("Graph ended", workflow.get_state(config).next == ())
    print(f"  Observed trace: {trace}")


def test_06_unresolved_after_limit():
    print("\n" + "="*70)
    print("TEST 06: Both verifications fail -> UNRESOLVED_AFTER_LIMIT")
    print("="*70)
    trace = []
    workflow, lm, conn = create_test_workflow(has_misc=True)
    config = make_config("t06")
    initial = {
        "student_id": "student_1", "topic": "Arrays", "attempt_id": "att_06",
        "syllabus_context": "Arrays.", "max_remediation_cycles": 2, "max_model_calls": 14
    }
    for ev in workflow.stream(initial, config):
        for k in ev: trace.append(k)
    workflow.update_state(config, {"student_answers": ["WRONG", "WRONG", "1", "WRONG", "2"]})
    for ev in workflow.stream(None, config):
        for k in ev: trace.append(k)
    workflow.update_state(config, {"learner_decision": "REVISE"})
    for ev in workflow.stream(None, config):
        for k in ev: trace.append(k)
    workflow.update_state(config, {"verification_answers": ["WRONG", "WRONG"]})
    for ev in workflow.stream(None, config):
        for k in ev: trace.append(k)
    workflow.update_state(config, {"learner_decision": "REVISE"})
    for ev in workflow.stream(None, config):
        for k in ev: trace.append(k)
    workflow.update_state(config, {"verification_answers": ["WRONG", "WRONG"]})
    for ev in workflow.stream(None, config):
        for k in ev: trace.append(k)
    state = workflow.get_state(config).values
    at_end = workflow.get_state(config).next == ()
    record("Graph terminated at END", at_end)
    record("Not mastered", state.get("verification_passed") != True)
    print(f"  Observed trace: {trace}")


def test_07_deterministic_scoring():
    print("\n" + "="*70)
    print("TEST 07: Deterministic scoring validation")
    print("="*70)
    workflow, lm, conn = create_test_workflow(has_misc=False)
    config = make_config("t07")
    initial = {
        "student_id": "student_1", "topic": "Arrays", "attempt_id": "att_07",
        "syllabus_context": "Arrays.", "max_remediation_cycles": 2, "max_model_calls": 14
    }
    for ev in workflow.stream(initial, config):
        pass
    # Q1(Indexing,"10"): "1" -> option[0]="10" -> correct
    # Q2(Indexing,"30"): "WRONG" -> incorrect
    # Q3(Traversal,"for loop"): "1" -> option[0]="for loop" -> correct
    # Q4(Indexing,"20"): "WRONG" -> incorrect
    # Q5(Traversal,"3"): "2" -> option[1]="3" -> correct
    workflow.update_state(config, {"student_answers": ["1", "WRONG", "1", "WRONG", "2"]})
    for ev in workflow.stream(None, config):
        pass
    state = workflow.get_state(config).values
    score = state.get("diagnostic_score", -1)
    expected_score = 3 / 5
    record("Score matches 3/5=0.6", abs(score - expected_score) < 0.01,
           f"score={score}, expected={expected_score}")
    results_list = state.get("diagnostic_results", [])
    expected_correct = [True, False, True, False, True]
    actual_correct = [r["is_correct"] for r in results_list]
    record("Per-question correctness", actual_correct == expected_correct,
           f"actual={actual_correct}, expected={expected_correct}")
    perf = lm.get_topic_performance("student_1", "Arrays")
    record("Learner memory has Indexing", "Indexing" in perf, f"perf keys={list(perf.keys())}")
    record("Learner memory has Traversal", "Traversal" in perf)
    if "Indexing" in perf:
        idx_data = perf["Indexing"]
        record("Indexing: 1/3 correct", idx_data["correct"] == 1 and idx_data["attempts"] == 3,
               f"correct={idx_data['correct']}, attempts={idx_data['attempts']}")
        record("Indexing status=weak (<60%)", idx_data["status"] == "weak",
               f"status={idx_data['status']}, accuracy={idx_data['accuracy']}")
    if "Traversal" in perf:
        trav_data = perf["Traversal"]
        record("Traversal: 2/2 correct", trav_data["correct"] == 2 and trav_data["attempts"] == 2,
               f"correct={trav_data['correct']}, attempts={trav_data['attempts']}")
        record("Traversal status=strong (100%)", trav_data["status"] == "strong",
               f"status={trav_data['status']}")


def test_08_verification_scoring():
    print("\n" + "="*70)
    print("TEST 08: Verification scoring (2/2 = pass, 1/2 = fail)")
    print("="*70)
    workflow, lm, conn = create_test_workflow(has_misc=True)
    config = make_config("t08")
    initial = {
        "student_id": "student_1", "topic": "Arrays", "attempt_id": "att_08",
        "syllabus_context": "Arrays.", "max_remediation_cycles": 2, "max_model_calls": 14
    }
    for ev in workflow.stream(initial, config):
        pass
    workflow.update_state(config, {"student_answers": ["WRONG", "WRONG", "1", "WRONG", "2"]})
    for ev in workflow.stream(None, config):
        pass
    workflow.update_state(config, {"learner_decision": "REVISE"})
    for ev in workflow.stream(None, config):
        pass
    workflow.update_state(config, {"verification_answers": ["2", "WRONG"]})
    for ev in workflow.stream(None, config):
        pass
    state = workflow.get_state(config).values
    record("1/2 verification = FAIL", state.get("verification_passed") == False,
           f"passed={state.get('verification_passed')}, score={state.get('verification_score')}")
    record("Score = 0.5", abs(state.get("verification_score", -1) - 0.5) < 0.01)


def test_09_model_call_budget():
    print("\n" + "="*70)
    print("TEST 09: Model call budget tracking")
    print("="*70)
    workflow, lm, conn = create_test_workflow(has_misc=True)
    config = make_config("t09")
    initial = {
        "student_id": "student_1", "topic": "Arrays", "attempt_id": "att_09",
        "syllabus_context": "Arrays.", "max_remediation_cycles": 2, "max_model_calls": 14
    }
    for ev in workflow.stream(initial, config):
        pass
    state = workflow.get_state(config).values
    calls_after_diag = state.get("model_calls", 0)
    record("After diagnostic: 1 model call", calls_after_diag == 1,
           f"model_calls={calls_after_diag}")
    workflow.update_state(config, {"student_answers": ["WRONG", "WRONG", "1", "WRONG", "2"]})
    for ev in workflow.stream(None, config):
        pass
    state = workflow.get_state(config).values
    calls_after = state.get("model_calls", 0)
    # score_diagnostic=no LLM, diagnosis=+1, remediation=+1 -> 3
    record("After diagnosis+remediation: 3 model calls", calls_after == 3,
           f"model_calls={calls_after}")


def test_10_pause_resume_points():
    print("\n" + "="*70)
    print("TEST 10: Pause/Resume at correct points")
    print("="*70)
    workflow, lm, conn = create_test_workflow(has_misc=True)
    config = make_config("t10")
    initial = {
        "student_id": "student_1", "topic": "Arrays", "attempt_id": "att_10",
        "syllabus_context": "Arrays.", "max_remediation_cycles": 2, "max_model_calls": 14
    }
    for ev in workflow.stream(initial, config):
        pass
    next_nodes = workflow.get_state(config).next
    record("Pauses before score_diagnostic", "score_diagnostic" in next_nodes,
           f"next={next_nodes}")
    workflow.update_state(config, {"student_answers": ["WRONG", "WRONG", "1", "WRONG", "2"]})
    for ev in workflow.stream(None, config):
        pass
    next_nodes = workflow.get_state(config).next
    record("Pauses before process_decision", "process_decision" in next_nodes,
           f"next={next_nodes}")
    workflow.update_state(config, {"learner_decision": "REVISE"})
    for ev in workflow.stream(None, config):
        pass
    next_nodes = workflow.get_state(config).next
    record("Pauses before score_verification", "score_verification" in next_nodes,
           f"next={next_nodes}")


def test_11_learner_memory_persistence():
    print("\n" + "="*70)
    print("TEST 11: Learner memory persistence")
    print("="*70)
    from backend.memory.learner_memory import LearnerMemory
    lm = LearnerMemory(db_path=":memory:")
    lm.create_student("S001")
    ctx = lm.get_learner_context("S001", "Arrays")
    record("New learner = no history", "No previous" in ctx, f"context='{ctx[:60]}...'")
    lm.create_attempt("att_11", "S001", "Arrays")
    lm.save_question_result("att_11", "Indexing", "Q1", "wrong", "right", False)
    lm.save_question_result("att_11", "Indexing", "Q2", "wrong", "right", False)
    lm.save_question_result("att_11", "Traversal", "Q3", "right", "right", True)
    lm.update_subconcept_performance("S001", "Arrays", "Indexing", False)
    lm.update_subconcept_performance("S001", "Arrays", "Indexing", False)
    lm.update_subconcept_performance("S001", "Arrays", "Traversal", True)
    lm.complete_attempt("att_11")
    ctx = lm.get_learner_context("S001", "Arrays")
    record("Returning learner has history", "Indexing" in ctx, f"context='{ctx[:100]}...'")
    record("History contains accuracy", "%" in ctx)


def test_12_is_answer_correct_logic():
    print("\n" + "="*70)
    print("TEST 12: is_answer_correct logic")
    print("="*70)
    from backend.graph.workflow import is_answer_correct
    record("Direct match '10'='10'", is_answer_correct("10", "10"))
    record("Case insensitive", is_answer_correct("True", "true"))
    opts = ["10", "20", "30", "0"]
    record("Answer '1' -> option[0]='10' matches correct='10'",
           is_answer_correct("1", "10", opts))
    record("Answer '3' -> option[2]='30' matches correct='30'",
           is_answer_correct("3", "30", opts))
    record("Answer '4' -> option[3]='0' != correct='10' -> False",
           not is_answer_correct("4", "10", opts))
    record("Wrong answer 'WRONG' != '10'", not is_answer_correct("WRONG", "10", opts))
    record("None answer", not is_answer_correct(None, "10"))
    record("None correct", not is_answer_correct("1", None))


def test_13_workflow_does_not_use_input():
    print("\n" + "="*70)
    print("TEST 13: No blocking input() in workflow")
    print("="*70)
    import inspect
    from backend.graph import workflow as wf_module
    source = inspect.getsource(wf_module)
    has_input = "input(" in source
    record("No input() in workflow.py", not has_input,
           "workflow.py calls input()" if has_input else "")


def test_14_remediation_agent_signature():
    print("\n" + "="*70)
    print("TEST 14: Remediation agent method name compatibility")
    print("="*70)
    from backend.agents.remediation import RemediationAgent
    has_remediate = hasattr(RemediationAgent, 'remediate')
    has_generate = hasattr(RemediationAgent, 'generate_remediation')
    record("RemediationAgent has 'remediate' method", has_remediate,
           f"has remediate={has_remediate}, has generate_remediation={has_generate}")
    if not has_remediate and has_generate:
        record("SIGNATURE MISMATCH: workflow calls .remediate() but agent defines .generate_remediation()", False,
               "CRITICAL: Method name mismatch between workflow and agent")


def test_15_verification_agent_is_stub():
    print("\n" + "="*70)
    print("TEST 15: VerificationAgent implementation check")
    print("="*70)
    import inspect
    from backend.agents.verification import VerificationAgent
    source = inspect.getsource(VerificationAgent.generate_questions)
    is_stub = "pass" in source.strip().split("\n")[-1]
    record("VerificationAgent is NOT a stub", not is_stub,
           f"Source ends with: {source.strip().split(chr(10))[-1].strip()}")


def test_16_verification_question_schema():
    print("\n" + "="*70)
    print("TEST 16: Verification question schema")
    print("="*70)
    from backend.agents.verification import VerificationQuestion
    fields = list(VerificationQuestion.model_fields.keys())
    record("Has 'question' field", "question" in fields, f"fields={fields}")
    record("Has 'correct_answer' field", "correct_answer" in fields)
    record("Has 'sub_concept' field", "sub_concept" in fields,
           f"MISSING sub_concept -- cannot track which concept is verified")
    record("Has 'explanation' field", "explanation" in fields,
           f"MISSING explanation -- no rationale for correct answer")
    record("Has 'options' field", "options" in fields,
           f"MISSING options -- MCQ support absent in verification")


def test_17_60_percent_weakness_threshold():
    print("\n" + "="*70)
    print("TEST 17: 60% weakness threshold")
    print("="*70)
    from backend.memory.learner_memory import LearnerMemory
    lm = LearnerMemory(db_path=":memory:")
    record("59% -> weak", lm._determine_status(0.59) == "weak")
    record("60% -> developing", lm._determine_status(0.60) == "developing")
    record("79% -> developing", lm._determine_status(0.79) == "developing")
    record("80% -> strong", lm._determine_status(0.80) == "strong")
    record("0% -> weak", lm._determine_status(0.0) == "weak")
    record("100% -> strong", lm._determine_status(1.0) == "strong")


# ---------------------------------------------------------------------------
# Run all tests
# ---------------------------------------------------------------------------

def main():
    print("=" * 70)
    print("EDUNEXUS BACKEND AUDIT -- AUTOMATED TEST SUITE")
    print("=" * 70)

    tests = [
        test_01_no_misconception,
        test_02_one_isolated_wrong,
        test_03_misconception_detected_revise_pass,
        test_04_misconception_defer,
        test_05_verification_fail_adaptive_then_mastered,
        test_06_unresolved_after_limit,
        test_07_deterministic_scoring,
        test_08_verification_scoring,
        test_09_model_call_budget,
        test_10_pause_resume_points,
        test_11_learner_memory_persistence,
        test_12_is_answer_correct_logic,
        test_13_workflow_does_not_use_input,
        test_14_remediation_agent_signature,
        test_15_verification_agent_is_stub,
        test_16_verification_question_schema,
        test_17_60_percent_weakness_threshold,
    ]

    for t in tests:
        try:
            t()
        except Exception as e:
            print(f"  [X] {t.__name__} EXCEPTION: {e}")
            traceback.print_exc()
            results.append({"test": t.__name__, "status": "ERROR", "detail": str(e)})

    print("\n" + "=" * 70)
    print("AUDIT TEST SUMMARY")
    print("=" * 70)
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    errors = sum(1 for r in results if r["status"] == "ERROR")
    total = len(results)
    print(f"  PASSED:  {passed}/{total}")
    print(f"  FAILED:  {failed}/{total}")
    print(f"  ERRORS:  {errors}/{total}")
    if failed > 0 or errors > 0:
        print("\n  FAILURES AND ERRORS:")
        for r in results:
            if r["status"] != "PASS":
                print(f"    [{r['status']}] {r['test']}: {r['detail']}")
    return results


if __name__ == "__main__":
    main()
