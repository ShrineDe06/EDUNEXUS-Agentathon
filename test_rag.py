import os
from openai import OpenAI
from dotenv import load_dotenv
from backend.memory.syllabus_memory import SyllabusMemory
from backend.agents.diagnostic import DiagnosticAgent

def main():
    print("Initializing SyllabusMemory...")
    memory = SyllabusMemory(persist_dir="backend/data/syllabus")

    # Clear old data to ensure we are testing with the latest version of the PDF
    print("Clearing old memory...")
    memory.reset()

    print("Ingesting lesson.pdf into memory...")
    memory.ingest_pdf("lesson.pdf")
    print("Data ingested and stored in FAISS.")
    
    query = input("\nEnter a topic from the PDF to generate questions for: ").strip()
    if not query:
        print("Query cannot be empty. Exiting.")
        return
    print(f"\nRetrieving context for query: '{query}'...")
    retrieved_context = memory.retrieve(query=query, top_k=2)
    
    print(f"\n--- Retrieved Context ---\n{retrieved_context}\n-------------------------\n")
    
    # ---------------------------------------------------------
    # Diagnostic Agent Integration
    # ---------------------------------------------------------
    load_dotenv()
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key or api_key == "your_nvidia_nim_api_key_here":
        print("No NVIDIA API key found. Skipping DiagnosticAgent portion of the test.")
        return

    print("Connecting to NVIDIA NIM...")
    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key
    )
    
    agent = DiagnosticAgent(llm=client)
    
    try:
        print("Generating diagnostic questions grounded ONLY in the retrieved context...")
        result = agent.generate_questions(topic=query, syllabus_context=retrieved_context)
        
        print(f"\nSuccessfully generated {len(result.questions)} questions:\n")
        for idx, q in enumerate(result.questions, 1):
            print(f"Q{idx}: {q.question}")
            print(f"  - Correct Answer: {q.correct_answer}\n")
            
    except Exception as e:
        print(f"Failed to generate questions: {e}")

if __name__ == "__main__":
    main()
