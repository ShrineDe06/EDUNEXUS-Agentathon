import os
import sqlite3
import uuid
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv

from backend.memory.syllabus_memory import SyllabusMemory
from backend.memory.learner_memory import LearnerMemory
from backend.graph.workflow import create_workflow
from langgraph.checkpoint.sqlite import SqliteSaver

st.set_page_config(
    page_title="EDUNEXUS | Adaptive Mastery Loop",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for rich aesthetics
st.markdown("""
<style>
    /* Dark glassmorphic theme styling */
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%);
        color: #f8fafc;
    }
    
    .main-header {
        font-family: 'Inter', sans-serif;
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(90deg, #38bdf8, #818cf8, #c084fc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    
    .sub-header {
        font-size: 1.1rem;
        color: #94a3b8;
        margin-bottom: 2rem;
    }
    
    .card-container {
        background: rgba(30, 41, 59, 0.7);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
    }
    
    .remediation-card {
        background: rgba(15, 23, 42, 0.8);
        border-left: 4px solid #818cf8;
        border-radius: 12px;
        padding: 20px;
        margin-top: 15px;
    }
    
    .badge-mastered {
        background: linear-gradient(90deg, #10b981, #059669);
        color: white;
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: 600;
        display: inline-block;
    }
    
    .badge-misc {
        background: linear-gradient(90deg, #ef4444, #dc2626);
        color: white;
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: 600;
        display: inline-block;
    }

    .stButton>button {
        border-radius: 10px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
</style>
""", unsafe_allow_html=True)

# Helper for DB connections & Services
@st.cache_resource
def get_services():
    load_dotenv()
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        st.error("OPENROUTER_API_KEY environment variable is missing!")
        st.stop()
        
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key
    )
    
    learner_memory = LearnerMemory(db_path="backend/data/edunexus.db")
    syllabus_memory = SyllabusMemory(persist_dir="backend/data/syllabus")
    
    conn = sqlite3.connect("backend/data/checkpoints.db", check_same_thread=False)
    saver = SqliteSaver(conn)
    workflow = create_workflow(client, learner_memory, checkpointer=saver)
    
    return client, learner_memory, syllabus_memory, workflow

client, learner_memory, syllabus_memory, workflow = get_services()

# Sidebar configuration
with st.sidebar:
    st.markdown("### 🎓 EDUNEXUS Dashboard")
    st.info("System Engine: OpenRouter + LangGraph")
    
    student_id = st.text_input("Learner Student ID", value="student_demo_ui")
    learner_memory.create_student(student_id)
    
    st.markdown("---")
    st.markdown("#### 📚 Syllabus Memory (RAG)")
    if os.path.exists("lesson.pdf"):
        if st.button("Re-ingest `lesson.pdf`"):
            with st.spinner("Ingesting PDF into RAG vector store..."):
                syllabus_memory.reset()
                syllabus_memory.ingest_pdf("lesson.pdf")
            st.success("Successfully ingested `lesson.pdf`!")
    else:
        st.warning("`lesson.pdf` not found in project root.")
        
    st.markdown("---")
    if st.button("Reset Learning Session", type="secondary"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# Session State Initialization
if "session_id" not in st.session_state:
    st.session_state.session_id = uuid.uuid4().hex[:8]
    st.session_state.thread_id = f"ui_thread_{st.session_state.session_id}"
    st.session_state.config = {"configurable": {"thread_id": st.session_state.thread_id}}
    st.session_state.learning_started = False
    st.session_state.diagnostic_submitted = False
    st.session_state.verification_submitted = False

st.markdown("<div class='main-header'>EDUNEXUS: Adaptive Mastery Loop</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-header'>AI-Powered Diagnostic Testing, Misconception Isolation, & Personalised Remediation</div>", unsafe_allow_html=True)

# Main Learning Flow
if not st.session_state.learning_started:
    st.markdown("<div class='card-container'>", unsafe_allow_html=True)
    st.markdown("### 🔍 Select Learning Topic")
    topic_input = st.text_input("Enter a concept or topic from your syllabus:", value="Python Classes and Object-Oriented Programming")
    
    if st.button("Start Diagnostic Assessment", type="primary"):
        if not topic_input.strip():
            st.error("Please enter a valid topic.")
        else:
            with st.spinner(f"Retrieving syllabus context and generating diagnostic assessment for '{topic_input}'..."):
                st.session_state.topic = topic_input.strip()
                st.session_state.syllabus_context = syllabus_memory.retrieve(query=st.session_state.topic, top_k=2)
                
                initial_state = {
                    "student_id": student_id,
                    "topic": st.session_state.topic,
                    "attempt_id": f"attempt_{st.session_state.session_id}",
                    "syllabus_context": st.session_state.syllabus_context,
                    "max_remediation_cycles": 2,
                    "max_model_calls": 14
                }
                
                # Run graph up to interrupt (diagnostic generation)
                for _ in workflow.stream(initial_state, st.session_state.config):
                    pass
                
                st.session_state.learning_started = True
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

else:
    # Fetch current graph state
    graph_state = workflow.get_state(st.session_state.config).values
    
    # -------------------------------------------------------------
    # DIAGNOSTIC PHASE
    # -------------------------------------------------------------
    questions = graph_state.get("diagnostic_questions", [])
    
    if not st.session_state.diagnostic_submitted and questions:
        st.markdown("<div class='card-container'>", unsafe_allow_html=True)
        st.markdown(f"### 📝 Diagnostic Assessment: **{st.session_state.topic}**")
        st.write("Answer the following 5 diagnostic questions to test your conceptual understanding:")
        
        diag_answers = []
        with st.form("diagnostic_form"):
            for idx, q in enumerate(questions, 1):
                st.markdown(f"**Q{idx}: {q.get('question')}**")
                options = q.get("options")
                if options and isinstance(options, list):
                    # Format options
                    formatted_opts = [f"{opt_idx}. {opt}" for opt_idx, opt in enumerate(options, 1)]
                    user_sel = st.radio(f"Select answer for Q{idx}:", options=formatted_opts, key=f"q_{idx}", index=0)
                    # Extract option number
                    diag_answers.append(user_sel.split(".")[0].strip())
                else:
                    user_text = st.text_input(f"Your answer for Q{idx}:", key=f"q_{idx}")
                    diag_answers.append(user_text.strip())
                st.markdown("---")
                
            submit_diag = st.form_submit_button("Submit Diagnostic Answers", type="primary")
            
            if submit_diag:
                with st.spinner("Scoring diagnostic answers & analyzing mental models..."):
                    workflow.update_state(st.session_state.config, {"student_answers": diag_answers})
                    for _ in workflow.stream(None, st.session_state.config):
                        pass
                    st.session_state.diagnostic_submitted = True
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # -------------------------------------------------------------
    # DIAGNOSIS & REMEDIATION / MASTERY DISPLAY
    # -------------------------------------------------------------
    elif st.session_state.diagnostic_submitted:
        graph_state = workflow.get_state(st.session_state.config).values
        misconception_found = graph_state.get("misconception_found", False)
        
        # Scenario A: NO MISCONCEPTION FOUND
        if not misconception_found:
            st.markdown("<div class='card-container'>", unsafe_allow_html=True)
            st.markdown("<span class='badge-mastered'>🎉 CONCEPT MASTERED</span>", unsafe_allow_html=True)
            st.markdown("### Diagnosis Result: Excellent!")
            st.success("No conceptual misconceptions were detected. You have demonstrated a strong understanding of this topic!")
            
            # Show score details
            diag_results = graph_state.get("diagnostic_results", [])
            if diag_results:
                correct_count = sum(1 for r in diag_results if r.get("is_correct"))
                st.metric("Diagnostic Score", f"{correct_count} / {len(diag_results)} ({int(correct_count/len(diag_results)*100)}%)")
                
            if st.button("Start Another Topic", type="primary"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        # Scenario B: MISCONCEPTION DIAGNOSED -> REMEDIATION
        else:
            diag = graph_state.get("diagnosis", {})
            remed = graph_state.get("remediation", {})
            
            st.markdown("<div class='card-container'>", unsafe_allow_html=True)
            st.markdown("<span class='badge-misc'>⚠️ MISCONCEPTION DETECTED</span>", unsafe_allow_html=True)
            st.markdown(f"### Diagnostic Analysis: **{diag.get('sub_concept', 'Sub-concept')}**")
            
            col1, col2 = st.columns(2)
            with col1:
                st.error(f"**Identified Misconception:**\n{diag.get('misconception')}")
            with col2:
                st.warning(f"**Diagnostic Evidence:**\n" + "\n".join([f"- {e}" for e in diag.get('evidence', [])]))
                
            st.markdown("---")
            st.markdown("### 💡 Targeted Learning Intervention")
            st.markdown(f"<div class='remediation-card'>"
                        f"<h4>Explanation</h4><p>{remed.get('explanation')}</p>"
                        f"<h4>Practical Example</h4><p><code>{remed.get('example')}</code></p>"
                        f"<h4>Key Takeaway</h4><p><strong>{remed.get('key_takeaway')}</strong></p>"
                        f"<h4>Check Your Understanding</h4><p><em>{remed.get('check_question')}</em></p>"
                        f"</div>", unsafe_allow_html=True)
            
            # Learner Decision step if not already made
            if graph_state.get("current_state") == "AWAITING_LEARNER_DECISION":
                st.markdown("---")
                st.markdown("#### What would you like to do next?")
                col_rev, col_def = st.columns(2)
                
                with col_rev:
                    if st.button("Revise & Verify Mastery 🚀", type="primary", use_container_width=True):
                        with st.spinner("Generating verification assessment..."):
                            workflow.update_state(st.session_state.config, {"learner_decision": "REVISE"})
                            for _ in workflow.stream(None, st.session_state.config):
                                pass
                            st.rerun()
                            
                with col_def:
                    if st.button("Defer Remediation (Skip) ⏸️", type="secondary", use_container_width=True):
                        workflow.update_state(st.session_state.config, {"learner_decision": "DEFER"})
                        for _ in workflow.stream(None, st.session_state.config):
                            pass
                        st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
            
            # Learner chose DEFER
            if graph_state.get("final_status") == "DEFERRED":
                st.warning("You opted to defer remediation for this concept. You can revisit it anytime!")
                if st.button("Start New Topic"):
                    for key in list(st.session_state.keys()):
                        del st.session_state[key]
                    st.rerun()

            # -------------------------------------------------------------
            # VERIFICATION PHASE
            # -------------------------------------------------------------
            elif graph_state.get("current_state") == "AWAITING_VERIFICATION_ANSWERS":
                v_questions = graph_state.get("verification_questions", [])
                
                st.markdown("<div class='card-container'>", unsafe_allow_html=True)
                st.markdown("### 🎯 Verification Assessment")
                st.write("Answer these 2 questions to prove your mastery of the remediated concept:")
                
                v_answers = []
                with st.form("verification_form"):
                    for idx, q in enumerate(v_questions, 1):
                        st.markdown(f"**V{idx}: {q.get('question')}**")
                        opts = q.get("options")
                        if opts and isinstance(opts, list):
                            formatted_opts = [f"{opt_idx}. {opt}" for opt_idx, opt in enumerate(opts, 1)]
                            sel = st.radio(f"Select answer for V{idx}:", options=formatted_opts, key=f"v_{idx}", index=0)
                            v_answers.append(sel.split(".")[0].strip())
                        else:
                            ans_text = st.text_input(f"Your answer for V{idx}:", key=f"v_{idx}")
                            v_answers.append(ans_text.strip())
                        st.markdown("---")
                        
                    submit_v = st.form_submit_button("Submit Verification Answers", type="primary")
                    if submit_v:
                        with st.spinner("Evaluating verification answers..."):
                            workflow.update_state(st.session_state.config, {"verification_answers": v_answers})
                            for _ in workflow.stream(None, st.session_state.config):
                                pass
                            st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

            # -------------------------------------------------------------
            # FINAL STATUSES
            # -------------------------------------------------------------
            elif graph_state.get("verification_passed"):
                st.balloons()
                st.markdown("<div class='card-container'>", unsafe_allow_html=True)
                st.markdown("<span class='badge-mastered'>🎉 VERIFICATION PASSED - MASTERED!</span>", unsafe_allow_html=True)
                st.success("Congratulations! You answered all verification questions correctly and successfully resolved your misconception.")
                if st.button("Learn Another Concept", type="primary"):
                    for key in list(st.session_state.keys()):
                        del st.session_state[key]
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
                
            elif graph_state.get("final_status") == "UNRESOLVED_AFTER_LIMIT":
                st.markdown("<div class='card-container'>", unsafe_allow_html=True)
                st.error("### ⚠️ Max Remediation Cycles Reached")
                st.write("You have completed 2 remediation & verification cycles. We recommend scheduling a 1-on-1 tutoring session or reviewing foundational materials before attempting again.")
                if st.button("Return to Topic Selection", type="primary"):
                    for key in list(st.session_state.keys()):
                        del st.session_state[key]
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
