import os
from openai import OpenAI
from dotenv import load_dotenv
from backend.agents.diagnostic import DiagnosticAgent

def main():
    # Load environment variables from .env
    load_dotenv()
    
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key or api_key == "your_nvidia_nim_api_key_here":
        print("Error: NVIDIA_API_KEY not found or not set properly.")
        print("Please create a .env file and add your actual API key.")
        return

    print("Connecting to NVIDIA NIM...")
    # Initialize the OpenAI client for NVIDIA NIM
    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key
    )

    # Instantiate our agent
    agent = DiagnosticAgent(llm=client)

    # Define our inputs
    topic = "Arrays"
    syllabus_context = """
    An array stores elements in contiguous memory.
    Array indexing begins at 0.
    Arrays have a fixed size upon creation in many statically typed languages.
    Accessing elements by index is an O(1) time complexity operation.
    Inserting an element at the beginning requires shifting all other elements, which is O(n).
    """

    try:
        print(f"Generating diagnostic questions for topic: '{topic}'...\n")
        result = agent.generate_questions(topic=topic, syllabus_context=syllabus_context)
        
        print(f"Successfully generated {len(result.questions)} questions:\n")
        for idx, q in enumerate(result.questions, 1):
            print(f"Q{idx}: {q.question}")
            print(f"  - Sub-concept: {q.sub_concept}")
            print(f"  - Type: {q.question_type}")
            print(f"  - Difficulty: {q.difficulty}")
            if q.options:
                print(f"  - Options: {', '.join(q.options)}")
            print(f"  - Correct Answer: {q.correct_answer}")
            print(f"  - Explanation: {q.explanation}\n")
            
    except Exception as e:
        print(f"Failed to generate questions: {e}")

if __name__ == "__main__":
    main()
