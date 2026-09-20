import os
from openai import OpenAI
from dotenv import load_dotenv
from backend.agents.diagnostic import DiagnosisAgent

def print_result(case_name, result):
    print(f"\n{'='*50}\n{case_name}\n{'='*50}")
    print(f"Has Misconception: {result.has_misconception}")
    if result.has_misconception:
        print(f"Sub-concept:       {result.sub_concept}")
        print(f"Misconception:     {result.misconception}")
        print(f"Affected Q-IDs:    {result.affected_question_ids}")
    print(f"Confidence:        {result.confidence}")
    print("Evidence:")
    for ev in result.evidence:
        print(f" - {ev}")
    print("\n")

def main():
    load_dotenv()
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key or api_key == "your_nvidia_nim_api_key_here":
        print("No NVIDIA API key found. Skipping test.")
        return

    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key
    )
    
    agent = DiagnosisAgent(llm=client)

    topic = "Arrays"
    syllabus_context = (
        "An array stores elements in contiguous memory locations. "
        "Array indexing begins at 0. Accessing elements by index is O(1). "
        "Inserting an element at the beginning requires shifting all other elements, resulting in an O(n) operation."
    )

    print("Running Diagnosis Agent Tests...")

    # CASE 1: Repeated errors on the same sub-concept -> Evidence-backed misconception
    results_repeated_error = [
        {"question": "What is the first index of an array?", "sub_concept": "indexing", "student_answer": "1", "correct_answer": "0", "is_correct": False},
        {"question": "How do you access the 5th element?", "sub_concept": "indexing", "student_answer": "array[5]", "correct_answer": "array[4]", "is_correct": False},
        {"question": "What is the time complexity of element access?", "sub_concept": "access time", "student_answer": "O(1)", "correct_answer": "O(1)", "is_correct": True},
        {"question": "What is the complexity of inserting at the beginning?", "sub_concept": "insertion", "student_answer": "O(n)", "correct_answer": "O(n)", "is_correct": True},
        {"question": "Are arrays contiguous in memory?", "sub_concept": "memory", "student_answer": "Yes", "correct_answer": "Yes", "is_correct": True},
    ]

    try:
        diagnosis_1 = agent.diagnose(topic, syllabus_context, results_repeated_error)
        print_result("CASE 1: Repeated errors (Should diagnose misconception)", diagnosis_1)
    except Exception as e:
        print(f"Error in Case 1: {e}")

    # CASE 2: Only one error -> Insufficient evidence
    results_single_error = [
        {"question": "What is the first index of an array?", "sub_concept": "indexing", "student_answer": "1", "correct_answer": "0", "is_correct": False},
        {"question": "How do you access the 5th element?", "sub_concept": "indexing", "student_answer": "array[4]", "correct_answer": "array[4]", "is_correct": True},
        {"question": "What is the time complexity of element access?", "sub_concept": "access time", "student_answer": "O(1)", "correct_answer": "O(1)", "is_correct": True},
        {"question": "What is the complexity of inserting at the beginning?", "sub_concept": "insertion", "student_answer": "O(n)", "correct_answer": "O(n)", "is_correct": True},
        {"question": "Are arrays contiguous in memory?", "sub_concept": "memory", "student_answer": "Yes", "correct_answer": "Yes", "is_correct": True},
    ]

    try:
        diagnosis_2 = agent.diagnose(topic, syllabus_context, results_single_error)
        print_result("CASE 2: Single error (Should return insufficient evidence)", diagnosis_2)
    except Exception as e:
        print(f"Error in Case 2: {e}")

if __name__ == "__main__":
    main()
