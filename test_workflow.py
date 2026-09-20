import os
import sqlite3
from typing import Optional
from backend.graph.workflow import create_workflow
from backend.memory.learner_memory import LearnerMemory
from langgraph.checkpoint.sqlite import SqliteSaver

class MockAgentResponse:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
    def model_dump(self):
        return self.__dict__

class MockQuestion:
    def __init__(self, q, sub, correct):
        self.question = q
        self.sub_concept = sub
        self.correct_answer = correct
    def model_dump(self):
        return self.__dict__

# Mock Agents
class MockLLM:
    pass

class MockDiagnosticAgent:
    def generate_questions(self, *args, **kwargs):
        return MockAgentResponse(questions=[MockQuestion(f"Q{i}", "Sub", "A") for i in range(5)])

class MockDiagnosisAgent:
    def __init__(self, has_misc=True):
        self.has_misc = has_misc
    def diagnose(self, *args, **kwargs):
        return MockAgentResponse(
            has_misconception=self.has_misc,
            sub_concept="Sub",
            misconception="Misc",
            evidence=["E1", "E2"],
            confidence=0.9,
            affected_question_ids=["Q0", "Q1"]
        )

class MockRemediationAgent:
    def remediate(self, *args, **kwargs):
        return MockAgentResponse(
            sub_concept="Sub",
            misconception="Misc",
            explanation="Explanation",
            example="Example",
            key_takeaway="Key",
            check_question="Check"
        )
    generate_remediation = remediate


class MockVerificationAgent:
    def generate_questions(self, *args, **kwargs):
        return MockAgentResponse(questions=[MockQuestion(f"V{i}", "Sub", "B") for i in range(2)])

class MockAdaptiveStrategyAgent:
    def generate_strategy(self, *args, **kwargs):
        return MockAgentResponse(
            cycle_limit_reached=False,
            new_strategy="New Strategy",
            rationale="Rationale"
        )


def run_path(test_name: str, has_misc: bool, learner_decision: str, verification_answers_cycle1: list, verification_answers_cycle2: Optional[list] = None):
    print(f"\n{'='*50}\nRunning {test_name}\n{'='*50}")
    
    # In-memory DBs for testing
    learner_memory = LearnerMemory(db_path=":memory:")
    learner_memory.create_student("student_1")
    
    # Mock the agents in the workflow module
    import backend.graph.workflow as wf
    wf.DiagnosticAgent = lambda llm: MockDiagnosticAgent()
    wf.DiagnosisAgent = lambda llm: MockDiagnosisAgent(has_misc)
    wf.RemediationAgent = lambda llm: MockRemediationAgent()
    wf.VerificationAgent = lambda llm: MockVerificationAgent()
    wf.AdaptiveStrategyAgent = lambda llm: MockAdaptiveStrategyAgent()
    
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    saver = SqliteSaver(conn)
    workflow = wf.create_workflow(MockLLM(), learner_memory, checkpointer=saver)
    
    config = {"configurable": {"thread_id": "test_thread"}}
    
    # 1. Start Workflow
    initial_state = {
        "student_id": "student_1",
        "topic": "Python Recursion",
        "attempt_id": "attempt_1",
        "syllabus_context": "Recursion calls itself.",
        "max_remediation_cycles": 2,
        "max_model_calls": 14
    }
    
    print("-> Starting diagnostic...")
    for event in workflow.stream(initial_state, config):
        pass # Pauses before score_diagnostic
    
    # Provide answers and resume
    print("-> Providing diagnostic answers...")
    answers = ["A", "A", "A", "A", "A"] if not has_misc else ["A", "A", "A", "Wrong", "Wrong"]
    workflow.update_state(config, {"student_answers": answers})
    for event in workflow.stream(None, config):
        pass
    
    state = workflow.get_state(config).values
    if not state.get("misconception_found"):
        print("Result: No Misconception Found")
        return
        
    # Provide learner decision
    print(f"-> Providing learner decision: {learner_decision}")
    workflow.update_state(config, {"learner_decision": learner_decision})
    for event in workflow.stream(None, config):
        pass
        
    state = workflow.get_state(config).values
    if state.get("learner_decision") == "DEFER":
        print("Result: DEFERRED")
        return
        
    # Provide verification answers for Cycle 1
    print(f"-> Providing verification answers Cycle 1: {verification_answers_cycle1}")
    workflow.update_state(config, {"verification_answers": verification_answers_cycle1})
    for event in workflow.stream(None, config):
        pass
        
    state = workflow.get_state(config).values
    if state.get("verification_passed"):
        print("Result: MASTERED (Cycle 1)")
        return
        
    if verification_answers_cycle2 is None:
        print("Cycle 1 failed, but no answers provided for Cycle 2. Test incomplete.")
        return
        
    # It paused at process_decision for cycle 2. Let's resume with REVISE again.
    print(f"-> Providing learner decision Cycle 2: {learner_decision}")
    workflow.update_state(config, {"learner_decision": learner_decision})
    for event in workflow.stream(None, config):
        pass
        
    # Provide verification answers for Cycle 2
    print(f"-> Providing verification answers Cycle 2: {verification_answers_cycle2}")
    workflow.update_state(config, {"verification_answers": verification_answers_cycle2})
    for event in workflow.stream(None, config):
        pass
        
    state = workflow.get_state(config).values
    if state.get("verification_passed"):
        print("Result: MASTERED (Cycle 2)")
    else:
        print("Result: UNRESOLVED_AFTER_LIMIT")


if __name__ == "__main__":
    # Test: No Misconception
    run_path("Test: No Misconception", has_misc=False, learner_decision="", verification_answers_cycle1=[])
    
    # Path A: Mastery
    run_path("Path A: Mastery (Cycle 1)", has_misc=True, learner_decision="REVISE", verification_answers_cycle1=["B", "B"])
    
    # Path B: Failed verf, then mastery
    run_path("Path B: Adaptive Strategy -> Mastery", has_misc=True, learner_decision="REVISE", verification_answers_cycle1=["B", "Wrong"], verification_answers_cycle2=["B", "B"])
    
    # Path C: Failure limit reached
    run_path("Path C: Unresolved After Limit", has_misc=True, learner_decision="REVISE", verification_answers_cycle1=["Wrong", "Wrong"], verification_answers_cycle2=["B", "Wrong"])
    
    # Test: Defer
    run_path("Test: Deferred", has_misc=True, learner_decision="DEFER", verification_answers_cycle1=[])
