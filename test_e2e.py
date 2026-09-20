import os
import sqlite3
import uuid
from openai import OpenAI
from dotenv import load_dotenv

from backend.memory.syllabus_memory import SyllabusMemory
from backend.memory.learner_memory import LearnerMemory
from backend.graph.workflow import create_workflow
from langgraph.checkpoint.sqlite import SqliteSaver

def main():
    load_dotenv()
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        print("Error: NVIDIA_API_KEY is not set.")
        return

    print("Connecting to NVIDIA NIM...")
    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key
    )

    print("Initializing LearnerMemory...")
    learner_memory = LearnerMemory(db_path="backend/data/edunexus.db")
    student_id = "demo_student"
    learner_memory.create_student(student_id)

    print("Initializing SyllabusMemory (RAG)...")
    syllabus_memory = SyllabusMemory(persist_dir="backend/data/syllabus")
    if os.path.exists("lesson.pdf"):
        print("Ingesting lesson.pdf into RAG memory...")
        syllabus_memory.reset()
        syllabus_memory.ingest_pdf("lesson.pdf")
    else:
        print("lesson.pdf not found. Assuming FAISS index is already populated.")

    topic = input("\nEnter a topic from the syllabus to learn: ").strip()
    if not topic:
        return
        
    print(f"\nRetrieving RAG context for '{topic}'...")
    retrieved_context = syllabus_memory.retrieve(query=topic, top_k=2)

    # Initialize LangGraph Checkpointer
    conn = sqlite3.connect("backend/data/checkpoints.db", check_same_thread=False)
    saver = SqliteSaver(conn)

    print("\nCompiling LangGraph Workflow...")
    workflow = create_workflow(client, learner_memory, checkpointer=saver)

    session_id = uuid.uuid4().hex[:8]
    config = {"configurable": {"thread_id": f"e2e_thread_{session_id}"}}

    initial_state = {
        "student_id": student_id,
        "topic": topic,
        "attempt_id": f"attempt_{session_id}",
        "syllabus_context": retrieved_context,
        "max_remediation_cycles": 2,
        "max_model_calls": 14
    }

    print("\n" + "="*50)
    print("STARTING LEARNING LOOP")
    print("="*50)
    
    print("\n[GRAPH] Running Diagnostic Phase...")
    for _ in workflow.stream(initial_state, config):
        pass

    state = workflow.get_state(config).values
    questions = state.get("diagnostic_questions", [])
    
    if not questions:
        print("No questions generated. Check LLM or context.")
        return

    print("\n--- DIAGNOSTIC QUESTIONS ---")
    student_answers = []
    for idx, q in enumerate(questions, 1):
        print(f"\nQ{idx}: {q.get('question')}")
        
        options = q.get('options')
        if options and isinstance(options, list) and len(options) > 0:
            for opt_idx, opt in enumerate(options, 1):
                print(f"  {opt_idx}. {opt}")
                
        ans = input("Your Answer: ")
        student_answers.append(ans)
        
    print("\n[GRAPH] Submitting answers and running diagnosis...")
    workflow.update_state(config, {"student_answers": student_answers})
    for _ in workflow.stream(None, config):
        pass
        
    state = workflow.get_state(config).values
    
    if not state.get("misconception_found"):
        print("\nResult: NO MISCONCEPTION FOUND! You have mastered this concept.")
        return
        
    diag = state.get("diagnosis", {})
    print(f"\n--- DIAGNOSIS ---")
    print(f"Misconception Detected: {diag.get('misconception')}")
    print(f"Sub-concept: {diag.get('sub_concept')}")
    print(f"Evidence: {diag.get('evidence')}")
    
    remed = state.get("remediation", {})
    print(f"\n--- REMEDIATION ---")
    print(f"Explanation: {remed.get('explanation')}")
    print(f"Example: {remed.get('example')}")
    print(f"Key Takeaway: {remed.get('key_takeaway')}")
    print(f"Check Question: {remed.get('check_question')}")
    
    decision = input("\nDo you want to REVISE (verify mastery) or DEFER (skip for now)? [revise/defer]: ").strip().upper()
    if decision not in ["REVISE", "DEFER"]:
        decision = "REVISE"
        
    workflow.update_state(config, {"learner_decision": decision})
    for _ in workflow.stream(None, config):
        pass
        
    state = workflow.get_state(config).values
    
    if decision == "DEFER" or state.get("final_status") == "DEFERRED":
        print("\nResult: REMEDIATION DEFERRED.")
        return
        
    # Verification Loop
    cycle = 1
    while cycle <= 2:
        print(f"\n[GRAPH] Verification Cycle {cycle}...")
        state = workflow.get_state(config).values
        v_questions = state.get("verification_questions", [])
        
        print("\n--- VERIFICATION QUESTIONS ---")
        v_answers = []
        for idx, q in enumerate(v_questions, 1):
            print(f"\nV{idx}: {q.get('question')}")
            
            options = q.get('options')
            if options and isinstance(options, list) and len(options) > 0:
                for opt_idx, opt in enumerate(options, 1):
                    print(f"  {opt_idx}. {opt}")
                    
            ans = input("Your Answer: ")
            v_answers.append(ans)
            
        print("\n[GRAPH] Submitting verification answers...")
        workflow.update_state(config, {"verification_answers": v_answers})
        for _ in workflow.stream(None, config):
            pass
            
        state = workflow.get_state(config).values
        if state.get("verification_passed"):
            print("\nResult: MASTERED! You passed the verification.")
            return
            
        if state.get("final_status") == "UNRESOLVED_AFTER_LIMIT":
            print("\nResult: UNRESOLVED_AFTER_LIMIT. Max remediation cycles reached.")
            return
            
        # We failed, but cycles remain. Graph routed to adaptive_strategy -> remediation -> pause
        print("\n--- VERIFICATION FAILED. ADAPTING STRATEGY ---")
        print(f"New Strategy: {state.get('previous_strategy')}") # It's stored in previous_strategy variable in state
        
        remed = state.get("remediation", {})
        print(f"\n--- NEW REMEDIATION ---")
        print(f"Explanation: {remed.get('explanation')}")
        print(f"Example: {remed.get('example')}")
        
        decision = input("\nDo you want to REVISE or DEFER? [revise/defer]: ").strip().upper()
        if decision not in ["REVISE", "DEFER"]:
            decision = "REVISE"
            
        workflow.update_state(config, {"learner_decision": decision})
        for _ in workflow.stream(None, config):
            pass
            
        state = workflow.get_state(config).values
        if decision == "DEFER" or state.get("final_status") == "DEFERRED":
            print("\nResult: REMEDIATION DEFERRED.")
            return
            
        cycle += 1

if __name__ == "__main__":
    main()
