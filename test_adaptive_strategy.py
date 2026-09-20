import os
from dotenv import load_dotenv
from openai import OpenAI
from backend.agents.adaptive_strategy import AdaptiveStrategyAgent

load_dotenv()

def test_adaptive_strategy():
    api_key = os.getenv("NVIDIA_API_KEY")
    base_url = "https://integrate.api.nvidia.com/v1"
    
    if not api_key:
        print("Error: NVIDIA_API_KEY is not set in environment variables or .env file.")
        return

    client = OpenAI(
        base_url=base_url,
        api_key=api_key
    )

    agent = AdaptiveStrategyAgent(llm=client)

    topic = "Python Functions & Scope"
    syllabus_context = (
        "In Python, variables defined inside a function have local scope, while variables "
        "defined outside have global scope. Modifying a global variable inside a function requires "
        "the 'global' keyword."
    )
    
    diagnosis = {
        "has_misconception": True,
        "sub_concept": "Variable Scope",
        "misconception": "Believes inner functions automatically modify outer global variables without declaration.",
        "evidence": ["Student answered that global x would be mutated directly without global keyword."],
        "confidence": 0.9,
        "affected_question_ids": ["Q2", "Q5"]
    }
    
    previous_remediation = (
        "Explanation: Variables assigned inside functions are local to that function unless declared global.\n"
        "Example: x = 5; def foo(): global x; x = 10"
    )
    
    verification_result = {
        "questions": ["What happens when you reassign x inside bar()?"],
        "student_answers": ["It changes the global x variable."],
        "correctness": False,
        "score": 0.0,
        "evidence": "Student still assumes assignment inside a function rebinds global names."
    }
    
    learner_context = "Student understands basic function definitions but struggles with scope persistence."

    print("\n--- Test 1: Cycle 1 (Normal Strategy Generation) ---")
    try:
        response_c1 = agent.generate_strategy(
            topic=topic,
            syllabus_context=syllabus_context,
            diagnosis=diagnosis,
            previous_remediation=previous_remediation,
            verification_result=verification_result,
            learner_context=learner_context,
            remediation_cycle=1
        )
        print("Cycle Limit Reached:", response_c1.cycle_limit_reached)
        print("Sub Concept:", response_c1.sub_concept)
        print("Misconception:", response_c1.misconception)
        print("Previous Strategy:", response_c1.previous_strategy)
        print("New Strategy:", response_c1.new_strategy)
        print("Rationale:", response_c1.rationale)
        print("Instructional Approach:", response_c1.instructional_approach)
        print("Key Focus:", response_c1.key_focus)
    except Exception as e:
        print("Test 1 Failed:", e)

    print("\n--- Test 2: Cycle 2 (Limit Reached Check) ---")
    try:
        response_c2 = agent.generate_strategy(
            topic=topic,
            syllabus_context=syllabus_context,
            diagnosis=diagnosis,
            previous_remediation=previous_remediation,
            verification_result=verification_result,
            learner_context=learner_context,
            remediation_cycle=2
        )
        print("Cycle Limit Reached:", response_c2.cycle_limit_reached)
        print("Rationale:", response_c2.rationale)
    except Exception as e:
        print("Test 2 Failed:", e)

if __name__ == "__main__":
    test_adaptive_strategy()
