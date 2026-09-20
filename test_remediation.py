import os
from openai import OpenAI
from dotenv import load_dotenv
from backend.agents.remediation import RemediationAgent
from backend.models.schemas import DiagnosisResponse

def print_result(result):
    print(f"\n{'='*50}\nRemediation Intervention\n{'='*50}")
    print(f"Sub-concept:    {result.sub_concept}")
    print(f"Misconception:  {result.misconception}\n")
    print(f"Explanation:\n{result.explanation}\n")
    print(f"Example:\n{result.example}\n")
    print(f"Key Takeaway:   {result.key_takeaway}\n")
    print(f"Check Question:\n{result.check_question}\n{'='*50}\n")

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
    
    agent = RemediationAgent(llm=client)

    topic = "Arrays"
    syllabus_context = (
        "An array stores elements in contiguous memory locations. "
        "Array indexing begins at 0. Accessing elements by index is O(1). "
        "Inserting an element at the beginning requires shifting all other elements, resulting in an O(n) operation."
    )

    # Mocking a DiagnosisResponse from the Diagnosis Agent
    diagnosis = DiagnosisResponse(
        has_misconception=True,
        sub_concept="indexing",
        misconception="Confuses 1-based indexing with 0-based indexing.",
        evidence=["Q1: answered 1 instead of 0 for the first index", "Q2: answered array[5] instead of array[4] to access the fifth element"],
        confidence=0.95,
        affected_question_ids=["Q1", "Q2"]
    )

    print("Running Remediation Agent Test...")

    try:
        remediation = agent.generate_remediation(topic, syllabus_context, diagnosis)
        print_result(remediation)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
