import os
import json
from typing import Optional, List
from pydantic import ValidationError
from backend.models.schemas import DiagnosticResponse, DiagnosisResponse
from backend.tools.agent_tools import search_syllabus_rag, get_student_progress

class DiagnosticAndDiagnosisAgent:
    """
    Unified Looping Agent responsible for:
    1. Evaluating RAG syllabus relevance & student DB progress.
    2. Generating diagnostic questions with dynamic thinking traces.
    3. Analyzing student answer patterns & diagnosing conceptual misconceptions.
    4. Running multi-turn diagnostic loops.
    """
    def __init__(self, llm):
        self.llm = llm

    def generate_questions(self, topic: str, syllabus_context: str, learner_context: str = None) -> DiagnosticResponse:
        """
        Generates exactly 5 diagnostic questions based on the topic, syllabus context (if relevant), and student DB progress.
        """
        if not topic or not topic.strip():
            raise ValueError("Topic cannot be empty")

        # Check RAG relevance
        is_rag_relevant = True
        if not syllabus_context or "NO_RELEVANT_RAG_CONTEXT" in syllabus_context or len(syllabus_context.strip()) < 15:
            is_rag_relevant = False
            effective_context = "TOPIC IS OUTSIDE UPLOADED SYLLABUS PDF. Relying on general domain knowledge."
        else:
            effective_context = syllabus_context

        schema_json = DiagnosticResponse.model_json_schema()

        system_prompt = (
            "You are an expert educational Diagnostic & Assessment Agent.\n"
            "Your goal is to generate exactly 5 diagnostic questions targeting core sub-concepts.\n\n"
            "DYNAMIC REASONING REQUIREMENT:\n"
            "You MUST generate a detailed, non-hardcoded `thinking_process` string explaining your step-by-step agentic thoughts:\n"
            "- Step 1: Evaluate whether RAG context is relevant to the user topic or if general domain knowledge must be used.\n"
            "- Step 2: Inspect student database progress (if provided) to identify historical weak sub-concepts.\n"
            "- Step 3: Explain your question design strategy and why specific sub-concepts were selected for diagnosis.\n\n"
            "DIAGNOSTIC QUESTION RULES:\n"
            "1. Focus on 2 to 3 core sub-concepts, creating 2 to 3 questions per sub-concept.\n"
            "2. Tag every question with its corresponding sub-concept.\n"
            "3. Questions should expose conceptual misunderstandings.\n"
            "4. Include 4 multiple-choice options, correct answer, and explanation.\n\n"
        )
        
        if is_rag_relevant:
            system_prompt += "RAG RULE: Ground questions in the provided syllabus context.\n\n"
        else:
            system_prompt += "NON-RAG RULE: The topic is not covered in the PDF. Use authoritative general domain knowledge.\n\n"

        if learner_context:
            system_prompt += (
                "STUDENT DATABASE PROGRESS INSTRUCTIONS:\n"
                f"{learner_context}\n"
                "- Give additional diagnostic weight to sub-concepts marked as 'weak' in the DB.\n\n"
            )
            
        system_prompt += (
            "You must respond with valid JSON that matches the following JSON Schema:\n"
            f"{json.dumps(schema_json)}\n"
        )

        user_prompt = f"Topic: {topic}\n\nCONTEXT:\n{effective_context}\n"
        if learner_context:
            user_prompt += f"\nSTUDENT DB PROGRESS:\n{learner_context}\n"

        model_name = os.environ.get("NVIDIA_MODEL", "nvidia/nemotron-3-ultra-550b-a55b")

        try:
            response = self.llm.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                stream=False
            )
        except Exception as e:
            raise RuntimeError(f"NVIDIA API failure: {e}")

        try:
            content = response.choices[0].message.content
            if content.startswith("```json"):
                content = content[7:-3]
            elif content.startswith("```"):
                content = content[3:-3]

            data = json.loads(content)
            if isinstance(data, list):
                data = {"questions": data, "used_rag": is_rag_relevant}
            else:
                data["used_rag"] = is_rag_relevant
                if "questions" not in data:
                    for key, val in data.items():
                        if isinstance(val, list):
                            data["questions"] = val
                            break
                        
            res = DiagnosticResponse.model_validate(data)
            res.used_rag = is_rag_relevant
            return res
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON response from LLM: {e}\nContent was: {content}")
        except ValidationError as e:
            raise ValueError(f"LLM output does not match the required schema: {e}\nContent was: {content}")
        except Exception as e:
            raise RuntimeError(f"An unexpected error occurred while parsing output: {e}")

    def diagnose(
        self,
        topic: str,
        syllabus_context: str,
        question_results: list,
        learner_context: str = None
    ) -> DiagnosisResponse:
        """
        Analyzes student responses to diagnostic questions and isolates conceptual misconceptions with dynamic thinking traces.
        """
        schema_json = DiagnosisResponse.model_json_schema()

        system_prompt = (
            "You are an expert educational Diagnostic & Assessment Agent.\n"
            "Your goal is to analyze student diagnostic test results and identify recurring conceptual misconceptions.\n\n"
            "DYNAMIC REASONING REQUIREMENT:\n"
            "You MUST populate the `thinking_process` field in your JSON output with your step-by-step reasoning:\n"
            "- Step 1: Analyze overall student score and per-question correctness.\n"
            "- Step 2: Compare incorrect student answers against expected conceptual models.\n"
            "- Step 3: Check student progress DB history to verify if this is a recurring misconception.\n"
            "- Step 4: Cite specific evidence Q-IDs and calculate misconception confidence (0.0 - 1.0).\n\n"
            "DIAGNOSIS RULES:\n"
            "1. If student responses show conceptual flaws, set has_misconception=True.\n"
            "2. Identify sub_concept, misconception description, and affected_question_ids.\n"
            "3. Set has_misconception=False ONLY IF the student demonstrated complete mastery.\n\n"
        )
        
        if learner_context:
            system_prompt += f"STUDENT DATABASE PROGRESS:\n{learner_context}\n\n"
            
        system_prompt += (
            "You must respond with valid JSON that matches the following JSON Schema:\n"
            f"{json.dumps(schema_json)}\n"
        )

        user_prompt = f"Topic: {topic}\n\nCONTEXT:\n{syllabus_context}\n\n"
        if learner_context:
            user_prompt += f"STUDENT DB PROGRESS:\n{learner_context}\n\n"
            
        user_prompt += "STUDENT DIAGNOSTIC RESULTS:\n"
        for idx, res in enumerate(question_results, 1):
            status = "CORRECT" if res.get('is_correct') else "INCORRECT"
            user_prompt += f"Q{idx}:\n"
            user_prompt += f"  Sub-concept: {res.get('sub_concept')}\n"
            user_prompt += f"  Question: {res.get('question')}\n"
            user_prompt += f"  Student Answer: {res.get('student_answer')}\n"
            user_prompt += f"  Correct Answer: {res.get('correct_answer')}\n"
            user_prompt += f"  Result: {status}\n\n"

        model_name = os.environ.get("NVIDIA_MODEL", "nvidia/nemotron-3-ultra-550b-a55b")

        try:
            response = self.llm.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                stream=False
            )
        except Exception as e:
            raise RuntimeError(f"NVIDIA API failure: {e}")

        try:
            content = response.choices[0].message.content
            if content.startswith("```json"):
                content = content[7:-3]
            elif content.startswith("```"):
                content = content[3:-3]

            data = json.loads(content)
            return DiagnosisResponse.model_validate(data)
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON response from LLM: {e}\nContent was: {content}")
        except ValidationError as e:
            raise ValueError(f"LLM output does not match the required schema: {e}\nContent was: {content}")
        except Exception as e:
            raise RuntimeError(f"An unexpected error occurred while parsing output: {e}")

    def run_diagnostic_loop(self, topic: str, syllabus_context: str, student_answers: list = None, learner_context: str = None):
        """
        Looping interface for unified diagnostic generation & diagnosis evaluation.
        """
        questions = self.generate_questions(topic, syllabus_context, learner_context)
        if not student_answers:
            return {"status": "AWAITING_ANSWERS", "questions": questions, "thinking_process": questions.thinking_process}
        
        results = []
        for q, ans in zip(questions.questions, student_answers):
            results.append({
                "question": q.question,
                "sub_concept": q.sub_concept,
                "student_answer": str(ans),
                "correct_answer": q.correct_answer,
                "is_correct": str(ans).strip().lower() == q.correct_answer.strip().lower()
            })
        diagnosis = self.diagnose(topic, syllabus_context, results, learner_context)
        return {"status": "DIAGNOSED", "questions": questions, "diagnosis": diagnosis, "thinking_process": diagnosis.thinking_process}

    def generate_diagnostic(self, topic: str, source_context: str = "", allowed_subconcepts: list = None, **kwargs):
        return self.generate_questions(topic=topic, syllabus_context=source_context)


DiagnosticAgent = DiagnosticAndDiagnosisAgent
DiagnosisAgent = DiagnosticAndDiagnosisAgent



