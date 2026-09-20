import os
import uuid
from openai import OpenAI
from dotenv import load_dotenv
from backend.memory.learner_memory import LearnerMemory
from backend.memory.syllabus_memory import SyllabusMemory
from backend.agents.diagnostic import DiagnosticAgent

def main():
    db_path = "backend/data/edunexus.db"
    
    # We remove the DB for a clean test run
    if os.path.exists(db_path):
        os.remove(db_path)
        
    print("1. Initializing LearnerMemory...")
    learner_memory = LearnerMemory(db_path=db_path)
    
    student_id = "student_001"
    topic = "Arrays"
    
    print(f"2. Creating student: {student_id}")
    learner_memory.create_student(student_id)
    
    attempt_id = str(uuid.uuid4())
    print(f"3. Creating attempt for topic: {topic} (Attempt ID: {attempt_id})")
    learner_memory.create_attempt(attempt_id, student_id, topic)
    
    print("4. Saving 5 mock question results...")
    # Q1 - indexing - incorrect
    learner_memory.save_question_result(attempt_id, "indexing", "What is array indexing?", "Value", "Position", False)
    learner_memory.update_subconcept_performance(student_id, topic, "indexing", False)
    
    # Q2 - indexing - incorrect
    learner_memory.save_question_result(attempt_id, "indexing", "First index of array?", "1", "0", False)
    learner_memory.update_subconcept_performance(student_id, topic, "indexing", False)
    
    # Q3 - traversal - correct
    learner_memory.save_question_result(attempt_id, "traversal", "How to visit all elements?", "Loop", "Loop", True)
    learner_memory.update_subconcept_performance(student_id, topic, "traversal", True)
    
    # Q4 - insertion - correct
    learner_memory.save_question_result(attempt_id, "insertion", "Complexity of inserting at start?", "O(n)", "O(n)", True)
    learner_memory.update_subconcept_performance(student_id, topic, "insertion", True)
    
    # Q5 - indexing - incorrect
    learner_memory.save_question_result(attempt_id, "indexing", "Index of 5th element?", "5", "4", False)
    learner_memory.update_subconcept_performance(student_id, topic, "indexing", False)

    print("5. Completing the attempt...")
    learner_memory.complete_attempt(attempt_id)
    
    print("\n6. Retrieving topic performance:")
    perf = learner_memory.get_topic_performance(student_id, topic)
    import json
    print(json.dumps(perf, indent=2))
    
    print("\n7. Retrieving generated learner context:")
    learner_context = learner_memory.get_learner_context(student_id, topic)
    print("====================================")
    print(learner_context)
    print("====================================\n")
    
    # Optional: Run DiagnosticAgent with this context
    load_dotenv()
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key or api_key == "your_nvidia_nim_api_key_here":
        print("No NVIDIA API key found. Skipping DiagnosticAgent portion of the test.")
        return

    print("8. Fetching syllabus context via SyllabusMemory...")
    syllabus_mem = SyllabusMemory(persist_dir="backend/data/syllabus")
    if syllabus_mem.index is None or syllabus_mem.index.ntotal == 0:
         print("No syllabus data found. Please run test_rag.py first to ingest lesson.pdf.")
         return
         
    syllabus_context = syllabus_mem.retrieve(topic, top_k=3)
    
    print("9. Running Diagnostic Agent with syllabus AND learner context...")
    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key
    )
    agent = DiagnosticAgent(llm=client)
    
    try:
        result = agent.generate_questions(topic=topic, syllabus_context=syllabus_context, learner_context=learner_context)
        print(f"\nSuccessfully generated {len(result.questions)} adapted questions:\n")
        for idx, q in enumerate(result.questions, 1):
            print(f"Q{idx}: {q.question}")
            print(f"  - Sub-concept: {q.sub_concept}")
            print(f"  - Difficulty: {q.difficulty}")
            print(f"  - Explanation: {q.explanation}\n")
    except Exception as e:
        print(f"Failed to generate questions: {e}")

if __name__ == "__main__":
    main()
