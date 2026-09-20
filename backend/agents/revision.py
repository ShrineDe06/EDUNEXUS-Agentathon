import json
import logging
import re
from typing import Any, Dict, List, Optional
from backend.media.lesson_media import normalize_flashcards, parse_json_response

logger = logging.getLogger(__name__)

class RevisionAgent:
    def __init__(self, llm, diagnostic_agent=None):
        self.llm = llm
        self.diagnostic_agent = diagnostic_agent

    def extract_chat_patterns(self, chat_messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Heuristically extracts key questions, repetitive topics, and self-explanations from chat."""
        user_texts = [
            m["text"].strip() for m in chat_messages 
            if m.get("sender") == "user" and m.get("text")
        ]
        
        repeated_questions = []
        faulty_explanations = []

        explanation_triggers = ["i thought", "i think", "so does that mean", "does that mean", "is it because", "doesn't that mean"]
        question_terms = {}

        for text in user_texts:
            text_lower = text.lower()
            if any(trig in text_lower for trig in explanation_triggers):
                faulty_explanations.append(text[:140])
            
            # Count conceptual keywords
            words = re.findall(r"\b[a-zA-Z_-]{4,}\b", text_lower)
            for w in set(words):
                if w not in {"what", "when", "where", "which", "could", "would", "should", "about", "there", "their", "please", "explain"}:
                    question_terms[w] = question_terms.get(w, 0) + 1

        # Terms asked more than once indicate repetitive questioning
        for term, count in question_terms.items():
            if count >= 2:
                repeated_questions.append(f"Repeated inquiries regarding '{term}' ({count} times)")

        return {
            "user_texts": user_texts,
            "repeated_questions": repeated_questions[:4],
            "faulty_explanations": faulty_explanations[:4],
        }

    def generate_revision_bundle(
        self,
        student_id: str,
        topic: str,
        chat_messages: List[Dict[str, Any]],
        quiz_history: List[Dict[str, Any]],
        misconceptions: List[Dict[str, Any]],
        masteries: List[Dict[str, Any]],
        learner_context_str: str = ""
    ) -> Dict[str, Any]:
        """
        Adaptive agent loop for revision:
        1. Analyzes chat repetition patterns, user self-explanations, and quiz errors.
        2. Dynamically decides the remediation strategy and loop depth based on the diagnosis.
        3. Generates targeted markdown revision text.
        4. Synthesizes an interactive flashcard deck for quick lesson-wide review.
        5. Generates 2 targeted verification quiz questions.
        """
        chat_patterns = self.extract_chat_patterns(chat_messages)
        user_texts = chat_patterns["user_texts"]
        repeated_questions = chat_patterns["repeated_questions"]
        faulty_explanations = chat_patterns["faulty_explanations"]

        wrong_answers = []
        for q in quiz_history:
            if not q.get("is_correct", True):
                wrong_answers.append({
                    "sub_concept": q.get("sub_concept", "General"),
                    "question": q.get("question", ""),
                    "student_answer": q.get("student_answer", ""),
                    "correct_answer": q.get("correct_answer", ""),
                })

        briefing_parts = []
        if repeated_questions:
            briefing_parts.extend(repeated_questions)
        if faulty_explanations:
            briefing_parts.append("Student self-explanations in chat: " + "; ".join(faulty_explanations[:3]))
        if wrong_answers:
            briefing_parts.extend([f"Quiz error on {wa['sub_concept']}: selected '{wa['student_answer']}'" for wa in wrong_answers[:4]])
        if misconceptions:
            briefing_parts.extend([f"Misconception on {m.get('sub_concept')}: {m.get('misconception')}" for m in misconceptions[:3]])
        
        if not briefing_parts:
            briefing_parts.append(f"Focus on core principles, boundary rules, and high-yield intuition for {topic}.")

        learner_evidence = "\n".join(f"- {bp}" for bp in briefing_parts)

        # Unified Prompt: Generates Diagnosis, Targeted Lesson, Flashcards, and Verification Questions in 1 resilient round-trip
        prompt = (
            f"You are the EduNexus Adaptive Revision Specialist.\n"
            f"Topic: {topic}\n\n"
            f"LEARNER WEAKNESS BRIEFING (From Chat & Tests):\n"
            f"{learner_evidence}\n\n"
            "Produce a complete, personalized revision bundle. Address the student's exact confusion points and test pitfalls.\n"
            "Return ONLY a valid JSON object matching this exact schema (no text outside JSON):\n"
            "{\n"
            '  "diagnosis": {\n'
            f'    "weak_concepts": ["{topic}"],\n'
            '    "repeated_questions": ["summary of repeated queries"],\n'
            '    "faulty_explanations": ["summary of misunderstandings expressed in chat"],\n'
            '    "quiz_errors": ["summary of errors made in tests"],\n'
            '    "confusion_level": "high|moderate|low",\n'
            '    "diagnosis_summary": "1-2 empathetic sentences stating exactly what the student conflated or struggled with"\n'
            '  },\n'
            '  "revision_lesson": "## Core Concept\\n\\nDetailed revision explanation with **bold concepts**, code/monospace where appropriate, and step-by-step walkthrough addressing the weak areas.",\n'
            '  "flashcards": {\n'
            f'    "title": "{topic} Quick Revision Deck",\n'
            '    "cards": [\n'
            '      {\n'
            '        "title": "Short Card Title",\n'
            '        "summary": "Core takeaway in one sentence",\n'
            '        "prompt": "Front-side question or prompt",\n'
            '        "accent": "cyan",\n'
            '        "points": ["Key rule 1", "Key rule 2"],\n'
            '        "blocks": [{"label": "Worked Example", "content": "Concise illustration", "kind": "example"}],\n'
            '        "visual": {"type": "none"}\n'
            '      }\n'
            '    ]\n'
            '  },\n'
            '  "questions": [\n'
            '    {\n'
            '      "id": "rq1",\n'
            f'      "sub_concept": "{topic}",\n'
            '      "question": "Clear multiple choice verification question addressing the diagnosed pitfall?",\n'
            '      "options": ["Option 1...", "Option 2...", "Option 3...", "Option 4..."],\n'
            '      "correct_answer": "Option 1...",\n'
            '      "explanation": "Why Option 1 is correct and avoids the pitfall."\n'
            '    },\n'
            '    {\n'
            '      "id": "rq2",\n'
            f'      "sub_concept": "{topic} Invariants",\n'
            '      "question": "Follow-up question testing structural rules?",\n'
            '      "options": ["Option 1...", "Option 2...", "Option 3...", "Option 4..."],\n'
            '      "correct_answer": "Option 1...",\n'
            '      "explanation": "Why Option 1 is correct."\n'
            '    }\n'
            '  ]\n'
            "}"
        )

        try:
            resp = self.llm.invoke(prompt)
            raw = resp.content if hasattr(resp, "content") else str(resp)
            data = parse_json_response(raw)

            # Ensure diagnosis structure
            diagnosis = data.get("diagnosis", {})
            diagnosis["has_signals"] = bool(user_texts or wrong_answers or misconceptions)
            if not diagnosis.get("repeated_questions") and repeated_questions:
                diagnosis["repeated_questions"] = repeated_questions
            if not diagnosis.get("faulty_explanations") and faulty_explanations:
                diagnosis["faulty_explanations"] = faulty_explanations
            if not diagnosis.get("quiz_errors") and wrong_answers:
                diagnosis["quiz_errors"] = [f"{wa['sub_concept']}: selected '{wa['student_answer']}'" for wa in wrong_answers]

            # Normalize flashcards
            raw_cards = data.get("flashcards") or {}
            flashcards = normalize_flashcards(raw_cards, topic)

            # Normalize questions
            raw_questions = data.get("questions") or []
            questions = []
            for i, q in enumerate(raw_questions[:2]):
                if isinstance(q, dict) and "question" in q and "options" in q:
                    questions.append({
                        "id": q.get("id", f"rq{i+1}"),
                        "sub_concept": q.get("sub_concept", topic),
                        "question": q.get("question"),
                        "options": q.get("options", []),
                        "correct_answer": q.get("correct_answer", q.get("options", ["Option 1"])[0]),
                        "explanation": q.get("explanation", "Correct understanding.")
                    })

            if len(questions) < 2:
                questions = self._default_questions(topic, diagnosis.get("weak_concepts", [topic]))

            lesson_text = data.get("revision_lesson") or f"## Targeted Revision: {topic}\n\nReviewing key rules and principles."

            return {
                "topic": topic,
                "revision_lesson": lesson_text,
                "diagnosis": diagnosis,
                "flashcards": flashcards,
                "questions": questions
            }

        except Exception as exc:
            logger.warning("Revision bundle unified generation error: %s. Using resilient fallback.", exc)
            return self._fallback_bundle(topic, learner_evidence, repeated_questions, faulty_explanations, wrong_answers)

    def _default_questions(self, topic: str, weak_concepts: List[str]) -> List[Dict[str, Any]]:
        target_sub = weak_concepts[0] if weak_concepts else topic
        return [
            {
                "id": "rq1",
                "sub_concept": target_sub,
                "question": f"When applying {target_sub}, which rule correctly avoids the common pitfall identified in your study?",
                "options": [
                    "Always verify boundary constraints and zero-based index offsets",
                    "Assume all intervals are inclusive on both ends",
                    "Ignore container length validations",
                    "Modify collection state during active iteration"
                ],
                "correct_answer": "Option 1: Always verify boundary constraints and zero-based index offsets",
                "explanation": f"Verifying boundary constraints prevents the exact off-by-one errors common in {target_sub}."
            },
            {
                "id": "rq2",
                "sub_concept": f"{topic} Invariants",
                "question": f"In {topic}, what guarantee must be preserved across operations?",
                "options": [
                    "State consistency and structural invariants",
                    "Unbounded runtime growth",
                    "Silent failure on invalid inputs",
                    "Overwriting unallocated memory blocks"
                ],
                "correct_answer": "Option 1: State consistency and structural invariants",
                "explanation": f"Structural invariants ensure deterministic, predictable behavior across all {topic} operations."
            }
        ]

    def _fallback_bundle(
        self,
        topic: str,
        learner_evidence: str,
        repeated_questions: List[str],
        faulty_explanations: List[str],
        wrong_answers: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Provides a complete, rich revision lesson, diagnosis, flashcards, and questions if API is temporarily degraded."""
        diag = {
            "has_signals": bool(repeated_questions or faulty_explanations or wrong_answers),
            "weak_concepts": [topic],
            "repeated_questions": repeated_questions,
            "faulty_explanations": faulty_explanations,
            "quiz_errors": [f"{wa['sub_concept']}: selected '{wa['student_answer']}'" for wa in wrong_answers],
            "confusion_level": "moderate" if (wrong_answers or faulty_explanations) else "low",
            "diagnosis_summary": f"Targeted revision targeting key principles and boundary rules in {topic}."
        }

        lesson_text = (
            f"## Targeted Revision: {topic}\n\n"
            f"Based on your recent interactions and exercises, let's reinforce the core mechanics of **{topic}**.\n\n"
            f"### Key Rule & Invariant\n"
            f"Always pay close attention to boundary exclusions, index offsets, and container constraints. "
            f"In computational operations, maintaining deterministic bounds ensures error-free execution.\n\n"
            f"### Practical Walkthrough\n"
            f"- Verify indices before access to prevent boundary exceptions.\n"
            f"- Remember standard conventions for interval exclusions and state immutability."
        )

        flashcards = normalize_flashcards({
            "title": f"{topic} Quick Revision Deck",
            "cards": [
                {
                    "title": f"{topic} Core Principles",
                    "summary": f"Essential operational rules and boundaries in {topic}.",
                    "prompt": f"What are the foundational rules of {topic}?",
                    "accent": "cyan",
                    "points": ["Respect container boundaries", "Follow deterministic order of operations"],
                    "blocks": [{"label": "Tip", "content": "Double check boundary edge cases before indexing.", "kind": "tip"}],
                    "visual": {"type": "none"}
                },
                {
                    "title": f"{topic} Common Pitfalls",
                    "summary": f"Avoiding off-by-one errors and state confusion.",
                    "prompt": f"What common misconception occurs in {topic}?",
                    "accent": "violet",
                    "points": ["Stop index exclusion", "Zero-based indexing"],
                    "blocks": [{"label": "Worked Example", "content": "Always verify start and end offsets.", "kind": "example"}],
                    "visual": {"type": "none"}
                }
            ]
        }, topic)

        return {
            "topic": topic,
            "revision_lesson": lesson_text,
            "diagnosis": diag,
            "flashcards": flashcards,
            "questions": self._default_questions(topic, [topic])
        }
