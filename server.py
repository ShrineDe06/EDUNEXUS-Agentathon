import os
import uuid
import datetime
import logging
import json
import time
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from backend.memory.learner_memory import LearnerMemory
from backend.memory.chat_memory import ChatMemory
from backend.memory.rag_scope import is_explicit_document_request, select_relevant_document_chunks
from backend.memory.syllabus_memory import SyllabusMemory
from backend.memory.revision_memory import RevisionMemory
from backend.memory.test_memory import TestMemory
from backend.memory.schedule_memory import ScheduleMemory
from backend.memory.progress_memory import ProgressMemory
from backend.services.email_service import send_study_reminder
from backend.media.lesson_media import normalize_flashcards, normalize_storyboard, parse_json_response, render_animated_lesson
from backend.learning.preferences import build_learn_preference_prompt
from backend.graph.workflow import create_workflow, is_answer_correct
from backend.agents.diagnostic import DiagnosticAgent, DiagnosisAgent, DiagnosticAndDiagnosisAgent
from backend.agents.remediation import RemediationAgent
from backend.agents.verification import VerificationAgent
from backend.agents.revision import RevisionAgent
from backend.agents.test_agent import TestAgent


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EDUNEXUS-SERVER")

app = FastAPI(title="EDUNEXUS Adaptive Mastery Engine", version="2.0.0")

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Core Services
learner_memory = LearnerMemory()
chat_memory = ChatMemory()
syllabus_memory = SyllabusMemory()
revision_memory = RevisionMemory()
from openai import OpenAI


class LLMWrapper:
    def __init__(self, client, model_name, fallback_models=None):
        self.client = client
        self.chat = client.chat
        self.model_name = model_name
        self.fallback_models = fallback_models or ["nvidia/nemotron-3-super-120b-a12b", "mistralai/mistral-nemotron"]

    def invoke(self, prompt: str) -> str:
        models = [self.model_name] + [m for m in self.fallback_models if m != self.model_name]
        last_error = None

        for model in models:
            for attempt in range(2):
                try:
                    res = self.client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.2,
                        timeout=60.0
                    )
                    content = res.choices[0].message.content
                    if content and content.strip():
                        return content
                except Exception as e:
                    last_error = e
                    err_text = str(e).lower()
                    if any(k in err_text for k in ["502", "503", "504", "429", "bad gateway", "timeout", "connection"]):
                        wait = 0.8 * (1.5 ** attempt)
                        logger.warning("NVIDIA model %s transient error (attempt %d/2): %s. Switching/retrying...", model, attempt + 1, e)
                        time.sleep(wait)
                    else:
                        logger.warning("NVIDIA model %s failed with non-transient error: %s. Trying fallback...", model, e)
                        break

        logger.error("All models and retries exhausted. Last error: %s", last_error)
        raise RuntimeError(f"NVIDIA API unavailable after retries: {last_error}")

def get_llm():
    api_key = os.getenv("NVIDIA_API_KEY") or os.getenv("OPENAI_API_KEY", "mock-key")
    model_name = os.getenv("NVIDIA_MODEL", "nvidia/nemotron-3-ultra-550b-a55b")
    base_url = "https://integrate.api.nvidia.com/v1" if os.getenv("NVIDIA_API_KEY") else None
    
    client = OpenAI(base_url=base_url, api_key=api_key, max_retries=1, timeout=60.0)
    return LLMWrapper(client, model_name)

llm = get_llm()

diagnostic_agent = DiagnosticAgent(llm)
diagnosis_agent = DiagnosisAgent(llm)
remediation_agent = RemediationAgent(llm)
verification_agent = VerificationAgent(llm)
revision_agent = RevisionAgent(llm, diagnostic_agent=diagnostic_agent)
test_agent = TestAgent(llm)
test_memory = TestMemory()
schedule_memory = ScheduleMemory()
progress_memory = ProgressMemory()
workflow = create_workflow(llm, learner_memory)

# UPLOAD DIR & STATIC DIR
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "backend", "data", "uploads")
MEDIA_DIR = os.path.join(os.path.dirname(__file__), "backend", "data", "generated")
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(MEDIA_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def read_root():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "EDUNEXUS API running."}

# -------------------------------------------------------------------
# PYDANTIC SCHEMAS
# -------------------------------------------------------------------
class LearnPreferences(BaseModel):
    chat_style: str = "auto"
    chat_custom_instruction: str = ""
    animation_style: str = "auto"
    animation_content: str = "auto"
    animation_custom_instruction: str = ""
    animation_engine: str = "auto"
    flashcard_style: str = "auto"
    flashcard_content: str = "auto"
    flashcard_custom_instruction: str = ""


class LearnChatRequest(BaseModel):
    student_id: str = "student_1"
    topic: str
    message: str
    document_name: Optional[str] = None
    session_id: Optional[str] = None
    response_mode: str = "text"
    preferences: Optional[LearnPreferences] = None


class CreateChatSessionRequest(BaseModel):
    student_id: str = "student_1"
    title: str
    description: str

class SaveEventRequest(BaseModel):
    student_id: str = "student_1"
    topic: str
    sub_concept: Optional[str] = None
    source_type: str = "freeform"
    document_name: Optional[str] = None
    mode: str = "learn"
    status: str = "EXPOSED"

class CheckUnderstandingRequest(BaseModel):
    student_id: str = "student_1"
    topic: str
    document_name: Optional[str] = None

class ReviseStartRequest(BaseModel):
    student_id: str = "student_1"
    topic: str

class ReviseVerifyRequest(BaseModel):
    student_id: str = "student_1"
    topic: str
    answers: Dict[str, str]
    questions: List[Dict[str, Any]]
    session_id: Optional[str] = None

class TestStartRequest(BaseModel):
    student_id: str = "student_1"
    topic: str
    subsection: str = "studied_concept"  # 'studied_concept' or 'uploaded_file'
    document_name: Optional[str] = None
    question_count: int = 5  # min 5, max 25
    custom_questions: Optional[List[Dict[str, Any]]] = None
    loop_round: int = 1

class TestSubmitRequest(BaseModel):
    student_id: str = "student_1"
    topic: str
    attempt_id: str
    session_id: Optional[str] = None
    answers: Dict[str, str]
    questions: List[Dict[str, Any]]
    timing: Optional[Dict[str, float]] = None  # { question_id: seconds_spent }

class TestReviewRequest(BaseModel):
    student_id: str = "student_1"
    topic: str
    session_id: Optional[str] = None
    review_mode: str = "text"  # 'text' or 'flashcards'
    failed_results: List[Dict[str, Any]]
    timings: Optional[Dict[str, float]] = None

class ScheduleCreateRequest(BaseModel):
    student_id: str = "student_1"
    topic: str
    mode: str = "revise"  # 'revise' or 'test'
    date: str  # YYYY-MM-DD
    time_slots: List[str]  # e.g. ["09:00", "15:30"]
    email: Optional[str] = None
    student_name: Optional[str] = None
    note: Optional[str] = None
    send_notification: bool = True

RAG_RELEVANCE_THRESHOLD = float(os.getenv("RAG_RELEVANCE_THRESHOLD", "0.42"))

# -------------------------------------------------------------------
# HELPER FUNCTIONS FOR SAFE VISUALIZATIONS
# -------------------------------------------------------------------
def generate_safe_visualization(topic: str, text: str = "") -> Optional[Dict[str, Any]]:
    topic_lower = (topic or "").lower().strip()
    
    if "python slicing" in topic_lower or ("slicing" in topic_lower and "array" in topic_lower):
        return {
            "type": "array_indexing",
            "title": "Array Indexing & Slicing",
            "elements": ["P", "y", "t", "h", "o", "n"],
            "positive_indices": [0, 1, 2, 3, 4, 5],
            "negative_indices": [-6, -5, -4, -3, -2, -1],
            "highlight_slice": [1, 4],
            "explanation": "Slice [1:4] extracts indices 1, 2, and 3 ('y', 't', 'h'). Stop index 4 is excluded."
        }
    return None

# -------------------------------------------------------------------
# API ENDPOINTS
# -------------------------------------------------------------------

@app.get("/api/health")
def health():
    return {"status": "ok", "app": "EDUNEXUS Mastery Engine"}

@app.get("/api/learner/{student_id}")
def get_learner_profile(student_id: str):
    return learner_memory.get_learner_summary(student_id)

@app.get("/api/learn/sessions/{student_id}")
def list_chat_sessions(student_id: str):
    return {"sessions": chat_memory.list_sessions(student_id)}

@app.post("/api/learn/sessions", status_code=status.HTTP_201_CREATED)
def create_chat_session(req: CreateChatSessionRequest):
    title = req.title.strip()
    description = req.description.strip()
    if not title:
        raise HTTPException(status_code=400, detail="A lesson title is required.")
    if not description:
        raise HTTPException(status_code=400, detail="A short lesson description is required.")
    learner_memory.create_student(req.student_id)
    return chat_memory.create_session(req.student_id, title[:120], description[:500])

@app.get("/api/learn/session/{session_id}")
def get_chat_session(session_id: str):
    session = chat_memory.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")
    return session

@app.delete("/api/learn/session/{session_id}")
def delete_chat_session(session_id: str):
    session = chat_memory.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")
    
    student_id = session["student_id"]
    topic = session["title"]
    attachments = session.get("attachments", [])
    
    success = chat_memory.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Chat session not found.")
    
    # Check if learner has any remaining sessions with this topic
    remaining = chat_memory.list_sessions(student_id)
    has_same_topic = any(s["title"].strip().lower() == topic.strip().lower() for s in remaining)
    if not has_same_topic:
        learner_memory.delete_topic_data(student_id, topic)
        revision_memory.delete_sessions_for_topic(student_id, topic)
        test_memory.delete_sessions_for_topic(student_id, topic)
        
    stored_names = [a["stored_name"] for a in attachments if a.get("stored_name")]
    if stored_names:
        try:
            syllabus_memory.delete_documents(stored_names)
        except Exception as e:
            logger.warning("Failed to clean up syllabus documents: %s", e)

    return {"status": "success", "message": f"Chat session {session_id} deleted."}

@app.post("/api/learn/session/{session_id}/documents", status_code=status.HTTP_201_CREATED)
async def upload_session_document(session_id: str, file: UploadFile = File(...)):
    session = chat_memory.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")

    display_name = os.path.basename(file.filename or "document.pdf")
    extension = os.path.splitext(display_name)[1].lower()
    if extension not in {".pdf", ".txt"}:
        raise HTTPException(status_code=400, detail="Only PDF and TXT files are supported.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Files must be 20 MB or smaller.")

    stored_name = f"{session_id}_{uuid.uuid4().hex[:8]}_{display_name}"
    file_path = os.path.join(UPLOAD_DIR, stored_name)
    with open(file_path, "wb") as destination:
        destination.write(content)

    try:
        if extension == ".pdf":
            syllabus_memory.ingest_pdf(file_path)
        else:
            text_content = content.decode("utf-8", errors="ignore")
            syllabus_memory.add_text(text_content, source_name=stored_name)
        return chat_memory.add_attachment(
            session_id=session_id,
            display_name=display_name,
            stored_name=stored_name,
            file_path=file_path,
            content_type=file.content_type,
            size=len(content),
        )
    except Exception as exc:
        if os.path.exists(file_path):
            os.remove(file_path)
        logger.error("Error ingesting session file %s: %s", display_name, exc)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}")

@app.get("/api/learn/attachments/{attachment_id}/download")
def download_session_attachment(attachment_id: str):
    attachment = chat_memory.get_attachment(attachment_id)
    if not attachment or not os.path.isfile(attachment["file_path"]):
        raise HTTPException(status_code=404, detail="Attachment not found.")
    return FileResponse(
        attachment["file_path"],
        media_type=attachment.get("content_type") or "application/octet-stream",
        filename=attachment["display_name"],
    )

@app.get("/api/learn/media/{filename}")
def get_generated_lesson_media(filename: str):
    safe_name = os.path.basename(filename)
    if safe_name != filename or not safe_name.endswith((".mp4", ".gif")):
        raise HTTPException(status_code=400, detail="Invalid media filename.")
    media_path = os.path.join(MEDIA_DIR, safe_name)
    if not os.path.isfile(media_path):
        raise HTTPException(status_code=404, detail="Generated media not found.")
    media_type = "video/mp4" if safe_name.endswith(".mp4") else "image/gif"
    return FileResponse(media_path, media_type=media_type)

@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    if not (file.filename.endswith(".pdf") or file.filename.endswith(".txt")):
        raise HTTPException(status_code=400, detail="Only PDF and TXT files are supported.")
    
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
        
    try:
        if file.filename.endswith(".pdf"):
            syllabus_memory.ingest_pdf(file_path)
        else:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                text_content = f.read()
            chunks = syllabus_memory._chunk_text(text_content, 1, file.filename)
            embeddings = syllabus_memory.model.encode([c["text"] for c in chunks], normalize_embeddings=True)
            syllabus_memory.index.add(embeddings)
            syllabus_memory.metadata.extend(chunks)
            syllabus_memory.save()
            
        return {
            "status": "success",
            "document_name": file.filename,
            "message": f"Successfully ingested {file.filename} into RAG vector store."
        }
    except Exception as e:
        logger.error(f"Error ingesting file {file.filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

@app.post("/api/learn/chat")
async def learn_chat(req: LearnChatRequest):
    learner_memory.create_student(req.student_id)

    session = None
    attachments = []
    conversation = []
    if req.session_id:
        session = chat_memory.get_session(req.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found.")
        if session["student_id"] != req.student_id:
            raise HTTPException(status_code=403, detail="This chat belongs to a different learner.")
        attachments = session["attachments"]
        conversation = chat_memory.recent_messages(req.session_id, limit=12)

    grounded_context = ""
    is_grounded = False
    document_names = [attachment["stored_name"] for attachment in attachments]
    if req.document_name and req.document_name not in document_names:
        document_names.append(req.document_name)

    user_query_lower = req.message.lower()
    explicitly_asking_doc = is_explicit_document_request(user_query_lower)

    if document_names and syllabus_memory.index is not None and syllabus_memory.index.ntotal:
        all_meta = syllabus_memory.metadata
        matching_chunks = [item for item in all_meta if item.get("document") in document_names]
        if matching_chunks:
            query_emb = syllabus_memory.model.encode([req.message], normalize_embeddings=True)
            distances, indices = syllabus_memory.index.search(
                query_emb,
                k=syllabus_memory.index.ntotal,
            )
            relevant_texts = select_relevant_document_chunks(
                metadata=all_meta,
                scores=distances[0],
                indices=indices[0],
                allowed_documents=document_names,
                query=req.message,
                explicit_document_request=explicitly_asking_doc,
                threshold=0.28 if explicitly_asking_doc else RAG_RELEVANCE_THRESHOLD,
            )
            if relevant_texts:
                grounded_context = "\n---\n".join(relevant_texts)
                is_grounded = True

    conversation_text = "\n".join(
        f"{'Student' if message['sender'] == 'user' else 'Tutor'}: {message['text']}"
        for message in conversation
    )
    session_context = ""
    if session:
        session_context = (
            f"Lesson: {session['title']}\n"
            f"Learning goal: {session['description']}\n"
        )
    history_context = f"Recent conversation history:\n{conversation_text}\n\n" if conversation_text else ""

    formatting_rules = (
        "Formatting rules:\n"
        "- Use bold markdown (**concept**) for emphasis and key terms.\n"
        "- Use code blocks or inline code (`code`) for technical terms or code.\n"
        "- Use standard numbered (1.) or dashed (-) lists instead of raw asterisks for bullet points.\n"
        "- Do not output raw asterisks without a markdown purpose."
    )

    response_mode = req.response_mode.lower().strip()
    if response_mode not in {"text", "flashcards", "video"}:
        raise HTTPException(status_code=400, detail="Response mode must be text, flashcards, or video.")
    preference_prompt = build_learn_preference_prompt(req.preferences, response_mode)

    if is_grounded:
        knowledge_prompt = (
            f"You are the EduNexus AI tutor. Continue the lesson naturally and maintain conversational flow using the chat history.\n"
            f"{session_context}{history_context}"
            f"Reference Material from Uploaded Document:\n{grounded_context}\n\n"
            f"Student Question: {req.message}\n\n"
            f"Answer the student's question accurately using the relevant material from their uploaded document.\n"
        )
    else:
        knowledge_prompt = (
            f"You are the EduNexus AI tutor. Answer the student's current question directly using general knowledge. "
            f"Use prior turns only when they are relevant to the current question.\n"
            f"{session_context}{history_context}"
            f"Student Question: {req.message}\n\n"
            f"The uploaded files are not relevant to this question. Ignore them completely: do not mention them, "
            f"do not discuss their subject, and do not ask permission to answer outside them. "
            f"Prioritize the current question even when it differs from the lesson title or earlier conversation.\n"
        )

    if req.session_id:
        chat_memory.add_message(req.session_id, "user", req.message)

    content_data = None
    if response_mode == "flashcards":
        prompt = knowledge_prompt + preference_prompt + (
            "Create vibrant, interactive teaching flashcards for the concept. Keep every point crisp and self-contained. "
            "Give every card a distinct accent color and 1 to 3 expandable blocks such as a fact, worked example, tip, or formula. "
            "Use a visual only when it materially improves understanding: bar or line for numeric relationships, "
            "process for sequences, otherwise none. Return ONLY valid JSON with this exact shape:\n"
            '{"title":"deck title","cards":[{"title":"card title","summary":"one-sentence idea",'
            '"prompt":"short front-side prompt","accent":"cyan|violet|orange|pink|green",'
            '"points":["point 1","point 2"],"blocks":[{"label":"Try this","content":"concise interactive detail","kind":"fact|example|tip|formula"}],'
            '"visual":{"type":"none|bar|line|process","title":"visual title",'
            '"labels":["A","B"],"values":[1,2],"steps":["step 1","step 2"]}}]}\n'
            "Generate 4 to 7 cards. Do not include markdown or commentary outside the JSON."
        )
        raw_response = llm.invoke(prompt)
        raw_text = raw_response.content if hasattr(raw_response, "content") else str(raw_response)
        try:
            content_data = normalize_flashcards(parse_json_response(raw_text), req.message)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            logger.warning("Flashcard JSON fallback used: %s", exc)
            content_data = normalize_flashcards({}, req.message)
        answer_text = f"Interactive flashcards: {content_data['title']}"
    elif response_mode == "video":
        prompt = knowledge_prompt + preference_prompt + (
            "Design a concise, genuinely visual animated teaching storyboard. Each scene must communicate one idea with animated objects and very little text. "
            "Do not create a text-only storyboard when the concept can be pictured. Choose render_style manim for algorithms, simulations, state changes, "
            "data structures, math, or mechanical motion; choose motion_graphics for a mostly narrative or high-level sequence; otherwise choose auto. "
            "For computer-science topics, select the most precise visual: array_sort for insertion/bubble/selection sort, binary_search for search, "
            "stack or queue for their operations, linked_list for pointer links, tree or graph for traversal, code_trace for execution and variables, "
            "memory for layouts/pointers, network for packet flow, and state_machine or process for protocols. "
            "For non-CS topics use engine_cycle for a four-stroke engine, particles or molecule for microscopic motion, bar for quantities, "
            "number_line for numeric movement, and process for sequential systems. Use 5 to 8 meaningful values/nodes and an explicit traversal, trace, "
            "operation list, or phase list whenever appropriate. For sorting, set algorithm to insertion_sort, bubble_sort, or selection_sort. "
            "The JSON is consumed by a trusted Manim scene runtime and by local FFmpeg/Pillow visual fallbacks; never emit Python code. "
            "Return ONLY valid JSON with this exact shape:\n"
            '{"title":"lesson title","render_style":"auto|manim|motion_graphics","scenes":[{"title":"scene title","caption":"short explanation",'
            '"points":["short supporting point"],"accent":"teal|blue|violet|amber",'
            '"visual":{"type":"none|array_sort|binary_search|stack|queue|tree|graph|linked_list|code_trace|memory|state_machine|network|bar|process|number_line|engine_cycle|particles|molecule",'
            '"algorithm":"insertion_sort|bubble_sort|selection_sort or empty","target":23,"count":12,'
            '"values":[7,3,5,2],"labels":["A","B"],"steps":["step 1","step 2"],'
            '"nodes":["A","B"],"edges":[["A","B"]],"operations":["push D"],"traversal":["A","B"],'
            '"code":["result = 1"],"trace":[{"line":1,"variables":{"result":1}}],"phases":["Intake","Compression","Power","Exhaust"]}}]}\n'
            "Generate 3 to 6 scenes. Do not include markdown, Python, or commentary outside the JSON."
        )
        raw_response = llm.invoke(prompt)
        raw_text = raw_response.content if hasattr(raw_response, "content") else str(raw_response)
        try:
            storyboard = normalize_storyboard(parse_json_response(raw_text), req.message)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            logger.warning("Storyboard JSON fallback used: %s", exc)
            storyboard = normalize_storyboard({}, req.message)
        preferred_engine = req.preferences.animation_engine.lower().strip() if req.preferences else "auto"
        if preferred_engine in {"manim", "motion_graphics"}:
            storyboard["render_style"] = preferred_engine
        content_data = render_animated_lesson(storyboard, MEDIA_DIR)
        answer_text = f"Animated lesson: {content_data['title']}"
    else:
        prompt = knowledge_prompt + preference_prompt + formatting_rules
        response_msg = llm.invoke(prompt)
        answer_text = response_msg.content if hasattr(response_msg, 'content') else str(response_msg)

    visualization = generate_safe_visualization(req.topic, answer_text) if not req.session_id and response_mode == "text" else None
    saved_message = None
    if req.session_id:
        saved_message = chat_memory.add_message(
            req.session_id,
            "tutor",
            answer_text,
            visualization=None,
            is_grounded=is_grounded,
            content_type=response_mode,
            content_data=content_data,
        )

    primary_document = attachments[0]["display_name"] if attachments else req.document_name
    learner_memory.save_learning_event(
        student_id=req.student_id,
        topic=req.topic,
        source_type="uploaded_document" if primary_document else "freeform",
        document_name=primary_document,
        mode="learn",
        status="EXPOSED",
        details=req.message
    )

    return {
        "response": answer_text,
        "visualization": visualization,
        "is_grounded": is_grounded,
        "document_name": primary_document,
        "content_type": response_mode,
        "content_data": content_data,
        "message": saved_message,
    }

@app.post("/api/learn/save_event")
def save_learning_event(req: SaveEventRequest):
    result = learner_memory.save_learning_event(
        student_id=req.student_id,
        topic=req.topic,
        sub_concept=req.sub_concept,
        source_type=req.source_type,
        document_name=req.document_name,
        mode=req.mode,
        status=req.status
    )
    return result

@app.post("/api/learn/check_understanding")
async def check_understanding(req: CheckUnderstandingRequest):
    # Retrieve grounded context if document
    context = ""
    if req.document_name:
        all_meta = syllabus_memory.metadata
        matching = [c["text"] for c in all_meta if c.get("document") == req.document_name]
        if matching:
            context = "\n---\n".join(matching[:3])
            
    if not context:
        chunks = syllabus_memory.search(query=req.topic, top_k=3)
        if chunks:
            context = "\n---\n".join([c["text"] for c in chunks])
            
    try:
        diag = diagnostic_agent.generate_diagnostic(
            topic=req.topic,
            source_context=context if context else f"General computer science topic: {req.topic}"
        )
        # Take 2 questions for quick check
        questions = [q.model_dump() for q in diag.questions[:2]]
        return {"topic": req.topic, "questions": questions}
    except Exception as e:
        logger.error(f"Error generating check understanding quiz: {e}")
        # Return fallback structured questions
        return {
            "topic": req.topic,
            "questions": [
                {
                    "id": "q1",
                    "sub_concept": f"{req.topic} Core",
                    "question": f"What is the primary purpose of {req.topic}?",
                    "options": [
                        "To structure and manipulate data efficiently",
                        "To format terminal output text",
                        "To handle network socket connections",
                        "To compile C extensions"
                    ],
                    "correct_answer": "Option 1: To structure and manipulate data efficiently",
                    "explanation": f"{req.topic} organizes data for computational efficiency."
                },
                {
                    "id": "q2",
                    "sub_concept": f"{req.topic} Behavior",
                    "question": f"Which statement best describes {req.topic}?",
                    "options": [
                        "It provides deterministic bounds for data operations",
                        "It only works on floating point values",
                        "It requires explicit memory deallocation",
                        "It replaces database indexes"
                    ],
                    "correct_answer": "Option 1: It provides deterministic bounds for data operations",
                    "explanation": f"{req.topic} operates under deterministic computational rules."
                }
            ]
        }

@app.get("/api/revise/topics/{student_id}")
def get_revision_topics(student_id: str):
    active_sessions = chat_memory.list_sessions(student_id)
    
    if active_sessions:
        # Group active sessions by normalized topic title
        active_topics_map = {}
        for s in active_sessions:
            norm_key = s["title"].strip().lower()
            if norm_key not in active_topics_map:
                active_topics_map[norm_key] = s
        
        memory_topics = learner_memory.get_topics_for_revision(student_id)
        topics_by_name = {t["topic"].strip().lower(): t for t in memory_topics}
        
        result = []
        for low_title, session in active_topics_map.items():
            topic_title = session["title"]
            rev_sessions = revision_memory.list_sessions(student_id, topic_title)
            rev_count = len(rev_sessions)

            if low_title in topics_by_name:
                item = dict(topics_by_name[low_title])
                if not item.get("document_name") and session.get("attachments"):
                    item["document_name"] = session["attachments"][0]["display_name"]
                item["revision_count"] = rev_count
                result.append(item)
            else:
                primary_doc = session["attachments"][0]["display_name"] if session.get("attachments") else None
                result.append({
                    "topic": topic_title,
                    "source_type": "uploaded_document" if primary_doc else "freeform",
                    "document_name": primary_doc,
                    "last_studied": session.get("updated_at") or session.get("created_at"),
                    "status": "LEARNING",
                    "weak_subconcepts": [],
                    "misconceptions": [],
                    "mastered_subconcepts": [],
                    "revision_count": rev_count
                })
        return result
    else:
        # If student has NO active sessions in Learn, return empty list
        # (Fallback to learner memory only for headless test scripts starting with test_)
        if student_id.startswith("test_"):
            return learner_memory.get_topics_for_revision(student_id)
        return []

@app.get("/api/revise/sessions/{student_id}/{topic}")
def get_topic_revision_sessions(student_id: str, topic: str):
    return revision_memory.list_sessions(student_id, topic)

@app.get("/api/revise/session/{session_id}")
def get_revision_session_by_id(session_id: str):
    session = revision_memory.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Revision session not found")
    return session

@app.delete("/api/revise/session/{session_id}")
def delete_revision_session_by_id(session_id: str):
    success = revision_memory.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Revision session not found")
    return {"status": "success", "message": f"Revision session {session_id} deleted."}

@app.post("/api/revise/start")
async def start_revision(req: ReviseStartRequest):
    # Fetch chat messages for this student and topic
    chat_messages = chat_memory.get_messages_for_topic(req.student_id, req.topic)
    
    # Fetch quiz/attempt history, active misconceptions, and masteries from learner_memory
    quiz_history = learner_memory.get_quiz_history(req.student_id, req.topic)
    misconceptions = learner_memory.get_topic_misconceptions(req.student_id, req.topic)
    masteries = learner_memory.get_topic_masteries(req.student_id, req.topic)

    context_str = learner_memory.get_learner_context(req.student_id, req.topic)
    
    # Run RevisionAgent adaptive loop
    bundle = revision_agent.generate_revision_bundle(
        student_id=req.student_id,
        topic=req.topic,
        chat_messages=chat_messages,
        quiz_history=quiz_history,
        misconceptions=misconceptions,
        masteries=masteries,
        learner_context_str=context_str
    )
    
    # Save the generated revision text, flashcards, and quiz entirely
    # as a session under that specific topic locally as "Revision 'n' in <topic>"
    saved_session = revision_memory.save_session(
        student_id=req.student_id,
        topic=req.topic,
        bundle=bundle
    )
    
    return saved_session

@app.post("/api/revise/verify")
async def verify_revision(req: ReviseVerifyRequest):
    score = 0.0
    total = len(req.questions)
    results = []
    
    for i, q in enumerate(req.questions):
        q_id = q.get("id", f"rq{i+1}")
        user_ans = req.answers.get(q_id, "")
        correct_ans = q.get("correct_answer", "")
        options = q.get("options", [])
        
        correct = is_answer_correct(user_ans, correct_ans, options)
        if correct:
            score += 1.0
            
        results.append({
            "question": q.get("question"),
            "sub_concept": q.get("sub_concept"),
            "user_answer": user_ans,
            "correct_answer": correct_ans,
            "is_correct": correct,
            "explanation": q.get("explanation")
        })
        
    final_acc = score / total if total > 0 else 0.0
    passed = final_acc >= 1.0
    
    if passed:
        # Mark mastered in DB
        for r in results:
            sc = r.get("sub_concept", req.topic)
            learner_memory.update_subconcept_mastery(req.student_id, req.topic, sc, is_correct=True)
            learner_memory.resolve_misconception(req.student_id, req.topic, sc)
        learner_memory.save_learning_event(req.student_id, req.topic, mode="revise", status="MASTERED")
        response_payload = {
            "passed": True,
            "score": final_acc,
            "status": "MASTERED",
            "message": f"Congratulations! You answered {int(score)}/{total} correctly and have MASTERED {req.topic}!",
            "results": results
        }
    else:
        # Trigger remediation for failed subconcept
        failed_q = [r for r in results if not r["is_correct"]][0]
        sub_concept = failed_q.get("sub_concept", req.topic)
        
        rem_res = remediation_agent.remediate(
            topic=req.topic,
            sub_concept=sub_concept,
            misconception=f"Failed revision check on {sub_concept}. Student selected: '{failed_q['user_answer']}'",
            student_answer=failed_q['user_answer'],
            correct_answer=failed_q['correct_answer'],
            source_context=failed_q.get('explanation', '')
        )
        
        ver_q = verification_agent.generate_verification_question(
            topic=req.topic,
            sub_concept=sub_concept,
            misconception=rem_res.misconception,
            strategy=rem_res.remediation_strategy
        )
        
        response_payload = {
            "passed": False,
            "score": final_acc,
            "status": "NEEDS_REMEDIATION",
            "message": f"Score {int(score)}/{total}. Let's remediate your understanding of {sub_concept}.",
            "results": results,
            "remediation": rem_res.model_dump() if hasattr(rem_res, 'model_dump') else rem_res,
            "verification_question": ver_q.model_dump() if hasattr(ver_q, 'model_dump') else ver_q
        }

    # Update the local revision session with verification results
    if req.session_id:
        try:
            revision_memory.update_session_verification(
                session_id=req.session_id,
                answers=req.answers,
                verify_result=response_payload
            )
        except Exception as e:
            logger.warning("Failed to update revision session verification: %s", e)

    return response_payload

@app.post("/api/test/start")
async def start_test(req: TestStartRequest):
    learner_memory.create_student(req.student_id)
    count = max(5, min(25, req.question_count or 5))

    if req.custom_questions and len(req.custom_questions) > 0:
        valid_qs = []
        for i, cq in enumerate(req.custom_questions[:count]):
            if "question" in cq and "options" in cq:
                valid_qs.append({
                    "id": f"cq_{i+1}",
                    "sub_concept": cq.get("sub_concept", f"{req.topic} Custom"),
                    "question": cq["question"],
                    "options": cq["options"],
                    "correct_answer": cq.get("correct_answer", cq["options"][0]),
                    "explanation": cq.get("explanation", "Custom question validation.")
                })
        questions = valid_qs
    elif req.subsection == "uploaded_file" or req.document_name:
        # Extract content from uploaded document in syllabus_memory
        doc_name = req.document_name
        doc_chunks = []
        if doc_name:
            all_meta = syllabus_memory.metadata
            doc_chunks = [c["text"] for c in all_meta if c.get("document") == doc_name]
        if not doc_chunks and req.topic:
            chunks = syllabus_memory.search(query=req.topic, top_k=6)
            if chunks:
                doc_chunks = [c["text"] for c in chunks]
        doc_context = "\n---\n".join(doc_chunks) if doc_chunks else ""

        questions = test_agent.generate_quiz(
            topic=req.topic,
            question_count=count,
            doc_context=doc_context
        )
    else:
        # Studied concept: Cross-reference chat history, revision sessions, and past test performance
        chat_messages = chat_memory.get_messages_for_topic(req.student_id, req.topic)
        rev_sessions = revision_memory.list_sessions(req.student_id, req.topic)
        past_quiz = learner_memory.get_quiz_history(req.student_id, req.topic)

        questions = test_agent.generate_quiz(
            topic=req.topic,
            question_count=count,
            chat_messages=chat_messages,
            revision_sessions=rev_sessions,
            past_quiz_history=past_quiz
        )

    attempt_id = f"att_{uuid.uuid4().hex[:8]}"
    learner_memory.create_attempt(attempt_id, req.student_id, req.topic)

    # Save session in test_memory
    saved_session = test_memory.create_session(
        student_id=req.student_id,
        topic=req.topic,
        subsection=req.subsection,
        questions=questions,
        document_name=req.document_name,
        loop_round=req.loop_round or 1
    )

    return {
        "session_id": saved_session["id"],
        "attempt_id": attempt_id,
        "title": saved_session["title"],
        "topic": req.topic,
        "subsection": req.subsection,
        "document_name": req.document_name,
        "question_count": len(questions),
        "questions": questions,
        "loop_round": req.loop_round or 1
    }

@app.post("/api/test/submit")
async def submit_test(req: TestSubmitRequest):
    score = 0.0
    total = len(req.questions)
    results = []
    timing = req.timing or {}
    total_time = sum(float(t) for t in timing.values()) if timing else 0.0
    avg_time = (total_time / total) if total > 0 else 0.0

    attempt = learner_memory.create_attempt(req.attempt_id, req.student_id, req.topic)

    # Calculate flagged hesitations (e.g. questions taking >= 30s or >= 2.2x average)
    flagged_hesitations = []
    for q_id, sec in timing.items():
        if sec >= 30.0 or (avg_time > 8.0 and sec >= avg_time * 2.2):
            flagged_hesitations.append(q_id)

    for q in req.questions:
        q_id = q.get("id")
        user_ans = req.answers.get(q_id, "")
        correct_ans = q.get("correct_answer", "")
        options = q.get("options", [])
        sub_concept = q.get("sub_concept", req.topic)
        time_spent = timing.get(q_id, 0.0)

        correct = is_answer_correct(user_ans, correct_ans, options)
        if correct:
            score += 1.0

        learner_memory.save_question_result(
            attempt_id=req.attempt_id,
            sub_concept=sub_concept,
            question=q.get("question"),
            student_answer=user_ans,
            correct_answer=correct_ans,
            is_correct=correct,
            question_id=q_id
        )

        learner_memory.update_subconcept_mastery(
            student_id=req.student_id,
            topic=req.topic,
            sub_concept=sub_concept,
            is_correct=correct
        )

        results.append({
            "question_id": q_id,
            "sub_concept": sub_concept,
            "question": q.get("question"),
            "user_answer": user_ans,
            "correct_answer": correct_ans,
            "is_correct": correct,
            "explanation": q.get("explanation"),
            "time_spent_seconds": time_spent,
            "is_hesitant": q_id in flagged_hesitations
        })

    accuracy = score / total if total > 0 else 0.0
    marks = int(score)
    passed = accuracy >= 0.8
    status = "MASTERED" if passed else "WEAKNESS_DETECTED"

    learner_memory.complete_attempt(req.attempt_id)
    learner_memory.save_learning_event(req.student_id, req.topic, mode="test", status=status)

    # Update TestMemory session
    if req.session_id:
        try:
            test_memory.update_submission(
                session_id=req.session_id,
                answers=req.answers,
                timing=timing,
                score=accuracy,
                marks=marks,
                passed=passed,
                total_time_seconds=total_time
            )
        except Exception as e:
            logger.warning("Failed to update test session submission: %s", e)

    failed_items = [r for r in results if not r["is_correct"]]

    return {
        "attempt_id": req.attempt_id,
        "session_id": req.session_id,
        "topic": req.topic,
        "score": accuracy,
        "marks": marks,
        "total": total,
        "passed": passed,
        "status": status,
        "results": results,
        "timing": timing,
        "total_time_seconds": total_time,
        "average_time_per_question": avg_time,
        "flagged_hesitations": flagged_hesitations,
        "failed_results": failed_items
    }

@app.post("/api/test/review")
async def review_test_remediation(req: TestReviewRequest):
    review_data = test_agent.generate_remediation_review(
        topic=req.topic,
        failed_results=req.failed_results,
        review_mode=req.review_mode,
        timings=req.timings
    )

    if req.session_id:
        try:
            test_memory.update_review(
                session_id=req.session_id,
                review_mode=req.review_mode,
                review_content=review_data["content"]
            )
        except Exception as e:
            logger.warning("Failed to update review content in test session: %s", e)

    return review_data

@app.get("/api/test/sessions/{student_id}")
def get_student_test_sessions(
    student_id: str,
    topic: Optional[str] = None,
    subsection: Optional[str] = None
):
    return test_memory.list_sessions(student_id, topic=topic, subsection=subsection)

@app.get("/api/test/session/{session_id}")
def get_test_session_details(session_id: str):
    session = test_memory.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Test session not found")
    return session

@app.delete("/api/test/session/{session_id}")
def delete_test_session(session_id: str):
    success = test_memory.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Test session not found")
    return {"status": "success", "message": f"Test session {session_id} deleted."}

# -------------------------------------------------------------------
# STUDY & TEST SCHEDULING WITH EMAIL REMINDERS
# -------------------------------------------------------------------
@app.post("/api/schedule/create")
def create_study_schedule(req: ScheduleCreateRequest):
    schedule = schedule_memory.create_schedule(
        student_id=req.student_id,
        topic=req.topic,
        mode=req.mode,
        date=req.date,
        time_slots=req.time_slots,
        email=req.email,
        note=req.note
    )

    delivery = None
    if req.email and req.send_notification:
        delivery = send_study_reminder(
            to_email=req.email,
            student_name=req.student_name or req.student_id,
            topic=req.topic,
            mode=req.mode,
            date=req.date,
            time_slots=req.time_slots,
            note=req.note
        )

    return {
        "status": "success",
        "schedule": schedule,
        "email_delivery": delivery
    }

@app.get("/api/schedule/list/{student_id}")
def list_study_schedules(
    student_id: str,
    mode: Optional[str] = None,
    topic: Optional[str] = None
):
    return schedule_memory.list_schedules(student_id, mode=mode, topic=topic)

@app.delete("/api/schedule/{schedule_id}")
def delete_study_schedule(schedule_id: str):
    success = schedule_memory.delete_schedule(schedule_id)
    if not success:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return {"status": "success", "message": f"Schedule {schedule_id} deleted."}

# -------------------------------------------------------------------
# PROGRESS HUB: REPORT ON LEARN, REVISE, TEST & TIMETABLE
# -------------------------------------------------------------------
class EmailConfigRequest(BaseModel):
    smtp_host: str
    smtp_port: int = 587
    smtp_user: str
    smtp_pass: str
    smtp_from: Optional[str] = None

class EmailTestRequest(BaseModel):
    recipient_email: str

@app.get("/api/email/status")
def get_email_status():
    smtp_host = os.getenv("SMTP_HOST")
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    configured = bool(smtp_host and smtp_user and smtp_pass)
    return {
        "configured": configured,
        "smtp_host": smtp_host or "smtp.gmail.com",
        "smtp_user": smtp_user or "",
        "method": "custom_smtp" if configured else "none"
    }

@app.post("/api/email/test")
def test_email_delivery(req: EmailTestRequest):
    res = send_study_reminder(
        to_email=req.recipient_email,
        student_name="EduNexus Learner",
        topic="EduNexus Email Verification Test",
        mode="test",
        date=datetime.date.today().isoformat(),
        time_slots=["Right Now"],
        note="Congratulations! Your real email delivery is properly configured and verified."
    )
    return res

@app.post("/api/email/config")
def configure_email_settings(req: EmailConfigRequest):
    try:
        env_path = os.path.join(os.path.dirname(__file__), ".env")
        lines = []
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

        keys_to_update = {
            "SMTP_HOST": req.smtp_host,
            "SMTP_PORT": str(req.smtp_port),
            "SMTP_USER": req.smtp_user,
            "SMTP_PASS": req.smtp_pass,
            "SMTP_FROM": req.smtp_from or req.smtp_user,
        }

        existing_keys = set()
        new_lines = []
        for line in lines:
            parts = line.split("=", 1)
            if len(parts) == 2 and parts[0].strip() in keys_to_update:
                k = parts[0].strip()
                new_lines.append(f"{k}={keys_to_update[k]}\n")
                existing_keys.add(k)
            else:
                new_lines.append(line)

        for k, v in keys_to_update.items():
            if k not in existing_keys:
                new_lines.append(f"{k}={v}\n")

        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

        os.environ.update(keys_to_update)

        return {"status": "success", "message": "SMTP settings saved successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save SMTP settings: {e}")

def _generate_student_report_data(student_id: str) -> Dict[str, Any]:
    # 1. Learnt topics from chat_memory
    chat_sessions = chat_memory.list_sessions(student_id)
    learnt_map: Dict[str, Any] = {}
    for cs in chat_sessions:
        t = cs.get("title") or "General Knowledge"
        if t not in learnt_map:
            learnt_map[t] = {
                "topic": t,
                "sessions_count": 0,
                "total_messages": 0,
                "last_active": cs.get("updated_at")
            }
        learnt_map[t]["sessions_count"] += 1
        learnt_map[t]["total_messages"] += cs.get("message_count", 0)

    # 2. Revisions from revision_memory
    rev_sessions = revision_memory.list_sessions(student_id)
    rev_map: Dict[str, Any] = {}
    for rs in rev_sessions:
        t = rs.get("topic") or "General Knowledge"
        if t not in rev_map:
            rev_map[t] = {
                "topic": t,
                "revisions_count": 0,
                "completed_count": 0,
                "last_score": None,
                "passed_count": 0
            }
        rev_map[t]["revisions_count"] += 1
        if rs.get("score") is not None:
            rev_map[t]["completed_count"] += 1
            rev_map[t]["last_score"] = rs.get("score")
            if rs.get("passed"):
                rev_map[t]["passed_count"] += 1

    # 3. Tests from test_memory
    test_sessions = test_memory.list_sessions(student_id)
    test_map: Dict[str, Any] = {}
    test_history: List[Dict[str, Any]] = []
    all_test_scores: List[float] = []
    total_time_all_tests = 0.0
    total_questions_all_tests = 0

    for ts in test_sessions:
        t = ts.get("topic") or "General Knowledge"
        score = ts.get("score")
        if t not in test_map:
            test_map[t] = {
                "topic": t,
                "tests_count": 0,
                "completed_count": 0,
                "scores": [],
                "best_score": 0.0,
                "latest_score": 0.0,
                "passed_count": 0,
                "total_time_seconds": 0.0,
                "total_questions": 0
            }
        test_map[t]["tests_count"] += 1

        if score is not None:
            score_pct = round(score * 100) if score <= 1.0 else round(score)
            test_history.append({
                "id": ts.get("id"),
                "topic": t,
                "score_pct": score_pct,
                "marks": ts.get("marks", 0),
                "total": ts.get("question_count", 0),
                "created_at": ts.get("created_at") or "",
                "mode": ts.get("mode", "studied_concept"),
                "passed": bool(ts.get("passed"))
            })
            all_test_scores.append(score)
            test_map[t]["completed_count"] += 1
            test_map[t]["scores"].append({
                "date": ts.get("created_at"),
                "score": score,
                "marks": ts.get("marks"),
                "total": ts.get("question_count"),
                "passed": bool(ts.get("passed"))
            })
            test_map[t]["best_score"] = max(test_map[t]["best_score"], score)
            test_map[t]["latest_score"] = score
            if ts.get("passed"):
                test_map[t]["passed_count"] += 1

        t_time = ts.get("total_time_seconds") or 0.0
        q_cnt = ts.get("question_count") or 0
        test_map[t]["total_time_seconds"] += t_time
        test_map[t]["total_questions"] += q_cnt
        total_time_all_tests += t_time
        total_questions_all_tests += q_cnt

    # Sort test history chronologically
    test_history.sort(key=lambda x: x.get("created_at") or "")

    # 4. Schedules
    schedules = schedule_memory.list_schedules(student_id)

    # 5. Union of all unique topics
    all_topic_names = sorted(list(set(list(learnt_map.keys()) + list(rev_map.keys()) + list(test_map.keys()))))

    # Learner profile concepts and misconceptions
    learner_profile = learner_memory.get_learner_summary(student_id)
    mastered_sub_list = []
    active_misc_list = learner_profile.get("misconceptions", [])

    # Topic breakdown
    topics_breakdown = []
    for topic in all_topic_names:
        l_info = learnt_map.get(topic, {"sessions_count": 0, "total_messages": 0})
        r_info = rev_map.get(topic, {"revisions_count": 0, "completed_count": 0, "passed_count": 0})
        t_info = test_map.get(topic, {"tests_count": 0, "completed_count": 0, "best_score": 0.0, "latest_score": 0.0, "scores": []})

        best_score = t_info.get("best_score", 0.0)
        best_score_pct = round(best_score * 100) if best_score <= 1.0 else round(best_score)

        if best_score >= 0.8 or r_info.get("passed_count", 0) > 0:
            status = "MASTERED"
            mastery_score = max(85, best_score_pct)
        elif t_info.get("tests_count", 0) > 0 and best_score < 0.6:
            status = "REVISION_NEEDED"
            mastery_score = max(35, best_score_pct)
        elif t_info.get("tests_count", 0) > 0 or r_info.get("revisions_count", 0) > 0:
            status = "IN_PROGRESS"
            mastery_score = max(60, best_score_pct)
        else:
            status = "LEARNED"
            mastery_score = 45

        # Subconcepts related to this topic
        topic_mastered_subs = [s for s in mastered_sub_list if topic.lower() in s.lower() or len(mastered_sub_list) < 5]
        topic_misconceptions = [m["details"] if isinstance(m, dict) else str(m) for m in active_misc_list if topic.lower() in str(m).lower() or len(active_misc_list) < 5]

        topics_breakdown.append({
            "topic": topic,
            "status": status,
            "mastery_score": mastery_score,
            "learn_chats_count": l_info.get("sessions_count", 0),
            "revision_sessions_count": r_info.get("revisions_count", 0),
            "test_attempts_count": t_info.get("tests_count", 0),
            "learn": l_info,
            "revise": r_info,
            "test": t_info,
            "mastered_subconcepts": topic_mastered_subs[:4],
            "active_misconceptions": topic_misconceptions[:3]
        })

    # Summary metrics
    avg_accuracy = (sum(all_test_scores) / len(all_test_scores)) if all_test_scores else 0.0
    avg_accuracy_pct = round(avg_accuracy * 100) if avg_accuracy <= 1.0 else round(avg_accuracy)
    mastered_topics_count = sum(1 for tb in topics_breakdown if tb["status"] == "MASTERED")

    # Generate Cognitive Feedback
    if not all_topic_names:
        feedback = "Welcome to EduNexus! You haven't started any study sessions yet. Begin by exploring your syllabus in the Learn tab or uploading course materials."
    else:
        # Prompt LLM for high-value diagnostic synthesis
        prompt = (
            f"You are the EduNexus Cognitive Diagnostic AI. Analyze the learner's data and write a concise, encouraging 3-part diagnostic summary:\n"
            f"- Student: {student_id}\n"
            f"- Studied Topics: {', '.join(all_topic_names)}\n"
            f"- Mastered Topics ({mastered_topics_count}/{len(all_topic_names)})\n"
            f"- Total Tests Attempted: {len(test_sessions)}, Average Score: {avg_accuracy_pct}%\n"
            f"- Revisions Completed: {sum(r['revisions_count'] for r in rev_map.values())}\n"
            f"- Active Misconceptions Count: {len(active_misc_list)}\n\n"
            f"Write 2-3 concise paragraphs covering: 1) Overall retention and momentum, 2) Specific cognitive strengths and weak points needing reinforcement, 3) Actionable next steps (e.g. flashcard revision or diagnostic test)."
        )
        try:
            feedback = llm.invoke(prompt).strip()
        except Exception as e:
            logger.warning("LLM feedback generation fallback: %s", e)
            if avg_accuracy_pct >= 80:
                feedback = f"Outstanding performance! You have mastered {mastered_topics_count} topic(s) with an average diagnostic score of {avg_accuracy_pct}%. Your recall patterns are exceptionally stable. Continue consistent spaced revisions to lock in conceptual depth."
            elif avg_accuracy_pct >= 60:
                feedback = f"Solid progress across {len(all_topic_names)} topic(s) with a {avg_accuracy_pct}% diagnostic average. Core fundamentals are in place, but several edge cases in recent assessments require focused flashcard drill sessions in Revise mode."
            else:
                feedback = f"You are actively laying the groundwork across {len(all_topic_names)} topic(s). With an average test accuracy of {avg_accuracy_pct}%, we recommend revisiting your earlier chat self-explanations and completing targeted revisions before your next test."

    metrics = {
        "total_topics": len(all_topic_names),
        "mastered_topics": mastered_topics_count,
        "total_chats": sum(l["sessions_count"] for l in learnt_map.values()),
        "total_revisions": sum(r["revisions_count"] for r in rev_map.values()),
        "total_tests": len(test_sessions),
        "average_test_accuracy": avg_accuracy_pct,
        "total_study_time_seconds": total_time_all_tests,
        "total_questions_answered": total_questions_all_tests,
        "active_misconceptions_count": len(active_misc_list)
    }

    # 6. Compute Actionable Improvement Areas ("What you need to work on")
    improvement_areas = []

    # Priority 1: Known misconceptions from learner memory
    for m in active_misc_list:
        t_name = m.get("topic") if isinstance(m, dict) else "General"
        desc = m.get("details") or m.get("misconception") if isinstance(m, dict) else str(m)
        improvement_areas.append({
            "priority": "HIGH",
            "type": "misconception",
            "topic": t_name,
            "title": f"Resolve Misconception in '{t_name}'",
            "description": desc,
            "action_mode": "revise",
            "action_label": f"Revise {t_name}"
        })

    # Priority 2: Topics with test accuracy < 75%
    for tb in topics_breakdown:
        t_score = tb["test"].get("latest_score", 0.0)
        t_count = tb["test"].get("tests_count", 0)
        if t_count > 0 and t_score < 0.75:
            score_pct = round(t_score * 100) if t_score <= 1.0 else round(t_score)
            improvement_areas.append({
                "priority": "HIGH" if score_pct < 60 else "MEDIUM",
                "type": "low_score",
                "topic": tb["topic"],
                "title": f"Strengthen Foundations in '{tb['topic']}'",
                "description": f"Latest assessment score is {score_pct}%. Review targeted concept flashcards and retake the test to reach 80%+ mastery.",
                "action_mode": "revise",
                "action_label": f"Revise {tb['topic']}"
            })

    # Priority 3: Topics with active discussions in Learn but 0 test attempts
    for tb in topics_breakdown:
        if tb["learn"].get("sessions_count", 0) > 0 and tb["test"].get("tests_count", 0) == 0:
            improvement_areas.append({
                "priority": "MEDIUM",
                "type": "untested",
                "topic": tb["topic"],
                "title": f"Verify Mastery in '{tb['topic']}'",
                "description": f"You've completed learning discussions on {tb['topic']}, but haven't validated recall with a diagnostic test yet.",
                "action_mode": "test",
                "action_label": f"Take {tb['topic']} Test"
            })

    # Default encouragement if no weaknesses found
    if not improvement_areas:
        if all_topic_names:
            improvement_areas.append({
                "priority": "MAINTAIN",
                "type": "maintenance",
                "topic": all_topic_names[0],
                "title": "Maintain High Spaced Recall",
                "description": "All your studied topics are currently showing high mastery! Continue spaced flashcard drills to lock knowledge into long-term memory.",
                "action_mode": "revise",
                "action_label": "Schedule Spaced Revision"
            })
        else:
            improvement_areas.append({
                "priority": "GET_STARTED",
                "type": "starter",
                "topic": "Getting Started",
                "title": "Begin Your Learning Journey",
                "description": "Explore your first syllabus topic in the Learn tab to start building your conceptual mastery profile.",
                "action_mode": "learn",
                "action_label": "Go to Learn Mode"
            })

    report_payload = {
        "student_id": student_id,
        "metrics": metrics,
        "summary": metrics, # alias for compatibility
        "topics_breakdown": topics_breakdown,
        "topic_reports": topics_breakdown, # alias for compatibility
        "test_history": test_history,
        "improvement_areas": improvement_areas,
        "scheduled_timetable": schedules,
        "schedules": schedules, # alias for compatibility
        "feedback": feedback,
        "diagnostic_feedback": feedback # alias for compatibility
    }

    return report_payload

@app.get("/api/progress/latest/{student_id}")
def get_latest_progress_report(student_id: str):
    latest = progress_memory.get_latest_report(student_id)
    if latest:
        return {"has_report": True, "report": latest}
    return {"has_report": False, "report": None}

@app.post("/api/progress/generate/{student_id}")
def generate_latest_progress_report(student_id: str):
    report_data = _generate_student_report_data(student_id)
    saved = progress_memory.save_report(student_id, report_data)
    return {"has_report": True, "report": saved}

@app.get("/api/progress/summary/{student_id}")
def get_student_progress_summary(student_id: str):
    # Check if latest report already exists
    latest = progress_memory.get_latest_report(student_id)
    if latest:
        return latest
    # Otherwise generate and save an initial one
    report_data = _generate_student_report_data(student_id)
    return progress_memory.save_report(student_id, report_data)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
