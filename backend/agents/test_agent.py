import json
import logging
import re
from typing import Any, Dict, List, Optional
from backend.media.lesson_media import normalize_flashcards, parse_json_response

logger = logging.getLogger("EDUNEXUS-TEST-AGENT")


class TestAgent:
    """
    Adaptive Test Agent:
    - Generates 5 to 25 diagnostic questions cross-referencing chat history, revision sessions, and past test performance.
    - Or generates questions strictly from an uploaded file/concept.
    - Analyzes only test answer patterns to synthesize targeted text explanations or flashcard decks.
    """

    def __init__(self, llm):
        self.llm = llm

    def generate_quiz(
        self,
        topic: str,
        question_count: int = 5,
        chat_messages: Optional[List[Dict[str, Any]]] = None,
        revision_sessions: Optional[List[Dict[str, Any]]] = None,
        past_quiz_history: Optional[List[Dict[str, Any]]] = None,
        doc_context: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Generates between 5 and 25 questions with deterministic options and explanations."""
        count = max(5, min(25, question_count))
        chat_messages = chat_messages or []
        revision_sessions = revision_sessions or []
        past_quiz_history = past_quiz_history or []

        # 1. Compile prior learning evidence
        evidence_lines = []

        # Document context takes highest priority if testing an uploaded file
        if doc_context and doc_context.strip():
            evidence_lines.append(f"UPLOADED DOCUMENT EXCERPTS:\n{doc_context[:3000]}\n")

        # Chat interaction signals
        user_queries = [m["text"] for m in chat_messages if m.get("sender") == "user"]
        if user_queries:
            evidence_lines.append(f"Student queries in Learn chat ({len(user_queries)} messages):\n" + "\n".join(f"- {q[:120]}" for q in user_queries[-8:]))

        # Revision signals
        if revision_sessions:
            rev_points = []
            for s in revision_sessions[:3]:
                diag = s.get("diagnosis")
                if isinstance(diag, dict) and diag.get("diagnosis_summary"):
                    rev_points.append(diag["diagnosis_summary"])
            if rev_points:
                evidence_lines.append("Prior Revision Diagnoses:\n" + "\n".join(f"- {rp}" for rp in rev_points))

        # Past quiz errors
        wrong_answers = [q for q in past_quiz_history if not q.get("is_correct", True)]
        if wrong_answers:
            evidence_lines.append("Past Test Errors:\n" + "\n".join(
                f"- Concept: {wa.get('sub_concept')} | Mistake: answered '{wa.get('student_answer')}' instead of '{wa.get('correct_answer')}'"
                for wa in wrong_answers[:5]
            ))

        context_brief = "\n\n".join(evidence_lines) if evidence_lines else f"Topic: {topic}. Cover core rules, invariants, operations, and common edge-case misconceptions."

        prompt = (
            f"You are the EDUNEXUS Assessment Specialist.\n"
            f"Topic: {topic}\n"
            f"Question Count: {count}\n\n"
            f"LEARNER STUDY SIGNALS & CONTENT CONTEXT:\n{context_brief}\n\n"
            f"Task: Generate exactly {count} challenging, high-yield multiple-choice questions for '{topic}'.\n"
            f"If an uploaded document is provided, test specifically on concepts from that document.\n"
            f"Target known misconception areas, boundary constraints, and practical application.\n\n"
            f"Return ONLY valid JSON with this exact schema (no text outside JSON):\n"
            "{\n"
            '  "questions": [\n'
            "    {\n"
            '      "id": "q_1",\n'
            '      "sub_concept": "Subconcept Name",\n'
            '      "question": "Question text?",\n'
            '      "options": [\n'
            '        "Option 1: ...",\n'
            '        "Option 2: ...",\n'
            '        "Option 3: ...",\n'
            '        "Option 4: ..."\n'
            "      ],\n"
            '      "correct_answer": "Option 1: ...",\n'
            '      "explanation": "Clear explanation of why this answer is correct and why other options are pitfalls."\n'
            "    }\n"
            "  ]\n"
            "}"
        )

        try:
            resp = self.llm.invoke(prompt)
            raw = resp.content if hasattr(resp, "content") else str(resp)
            data = parse_json_response(raw)
            raw_qs = data.get("questions") or []

            questions = []
            for i, q in enumerate(raw_qs):
                if isinstance(q, dict) and "question" in q and "options" in q and len(q["options"]) >= 2:
                    options = q["options"]
                    correct = q.get("correct_answer") or options[0]
                    # Format options uniformly
                    clean_options = [opt if re.match(r"^Option\s+\d+:", opt) else f"Option {j+1}: {opt}" for j, opt in enumerate(options)]
                    clean_correct = correct if re.match(r"^Option\s+\d+:", correct) else clean_options[0]

                    questions.append({
                        "id": q.get("id", f"q_{i+1}"),
                        "sub_concept": q.get("sub_concept", topic),
                        "question": q["question"],
                        "options": clean_options,
                        "correct_answer": clean_correct,
                        "explanation": q.get("explanation", f"Evaluates core understanding of {topic}.")
                    })

            if len(questions) >= count:
                return questions[:count]
            elif len(questions) > 0:
                # Supplement remaining questions if count was slightly under
                return self._supplement_questions(topic, questions, count)
        except Exception as exc:
            logger.warning("Test generation failed via LLM: %s. Using resilient fallback.", exc)

        return self._fallback_quiz(topic, count)

    def generate_remediation_review(
        self,
        topic: str,
        failed_results: List[Dict[str, Any]],
        review_mode: str = "text",
        timings: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Analyzes only the test answer patterns, missed questions, and response timings
        to generate either a targeted text concept or interactive flashcards.
        """
        timings = timings or {}
        error_summary_lines = []
        for r in failed_results:
            q_id = r.get("question_id") or r.get("id")
            time_spent = timings.get(q_id)
            time_str = f" (Time spent: {time_spent:.1f}s)" if time_spent is not None else ""
            error_summary_lines.append(
                f"- Question: {r.get('question')}\n"
                f"  Sub-concept: {r.get('sub_concept')}\n"
                f"  Student selected: {r.get('user_answer')}\n"
                f"  Correct answer: {r.get('correct_answer')}{time_str}\n"
                f"  Diagnostic context: {r.get('explanation')}"
            )

        error_context = "\n".join(error_summary_lines)

        if review_mode == "flashcards":
            prompt = (
                f"You are the EDUNEXUS Flashcard Remediation Specialist.\n"
                f"Topic: {topic}\n\n"
                f"STUDENT TEST ANSWER PATTERN & MISSED QUESTIONS:\n{error_context}\n\n"
                f"Generate a customized set of 3 to 6 interactive flashcards specifically targeting the concepts, rules, and formulas that the student missed on the test.\n"
                f"Return ONLY valid JSON matching this exact schema:\n"
                "{\n"
                f'  "title": "{topic} Remediation Deck",\n'
                '  "cards": [\n'
                "    {\n"
                '      "title": "Short Card Title",\n'
                '      "summary": "Key rule resolving the mistake in one sentence",\n'
                '      "prompt": "Front question challenging the missed concept",\n'
                '      "accent": "violet",\n'
                '      "points": ["Crucial rule 1", "Pitfall to avoid"],\n'
                '      "blocks": [{"label": "Worked Example", "content": "Clear example contrasting wrong vs right", "kind": "example"}],\n'
                '      "visual": {"type": "none"}\n'
                "    }\n"
                "  ]\n"
                "}"
            )
            try:
                resp = self.llm.invoke(prompt)
                raw = resp.content if hasattr(resp, "content") else str(resp)
                data = parse_json_response(raw)
                cards = normalize_flashcards(data, topic)
                return {"review_mode": "flashcards", "content": cards}
            except Exception as exc:
                logger.warning("Flashcard remediation failed: %s. Using fallback.", exc)
                return {
                    "review_mode": "flashcards",
                    "content": normalize_flashcards({
                        "title": f"{topic} Remediation Deck",
                        "cards": [
                            {
                                "title": f"{topic} Core Invariants",
                                "summary": f"Review key operational boundaries for {topic}.",
                                "prompt": f"What was the key rule missed on {topic}?",
                                "accent": "violet",
                                "points": ["Always inspect index boundaries", "Maintain state consistency"],
                                "blocks": [{"label": "Key Insight", "content": "Verify each operation step carefully.", "kind": "tip"}],
                                "visual": {"type": "none"}
                            }
                        ]
                    }, topic)
                }
        else:
            # review_mode == 'text'
            prompt = (
                f"You are the EDUNEXUS Concept Remediation Specialist.\n"
                f"Topic: {topic}\n\n"
                f"STUDENT TEST ANSWER PATTERN & MISSED QUESTIONS:\n{error_context}\n\n"
                f"Write a focused, targeted concept explanation addressing only the exact mistakes and misconceptions demonstrated in the student's test answers.\n"
                f"Explain the underlying principles, highlight where the reasoning went wrong, and provide a clear, step-by-step example.\n"
                f"Use bold markdown (**key concepts**) and code formatting where helpful. Keep it concise, insightful, and practical."
            )
            try:
                resp = self.llm.invoke(prompt)
                lesson_text = resp.content if hasattr(resp, "content") else str(resp)
                return {"review_mode": "text", "content": lesson_text}
            except Exception as exc:
                logger.warning("Text remediation failed: %s. Using fallback.", exc)
                return {
                    "review_mode": "text",
                    "content": f"## Targeted Review: {topic}\n\nReviewing key principles from your test:\n\n" + "\n".join(
                        f"- **{r.get('sub_concept', topic)}**: Correct answer was `{r.get('correct_answer')}`. Ensure you avoid assuming inclusive stop bounds or uncontrolled state mutations."
                        for r in failed_results
                    )
                }

    def _supplement_questions(self, topic: str, existing: List[Dict[str, Any]], target_count: int) -> List[Dict[str, Any]]:
        needed = target_count - len(existing)
        subconcepts = ["Boundary Invariants", "State Mutation", "Algorithmic Complexity", "Error Handling", "Memory Management"]
        for i in range(needed):
            sc = subconcepts[i % len(subconcepts)]
            existing.append({
                "id": f"q_{len(existing) + 1}",
                "sub_concept": f"{topic} {sc}",
                "question": f"In {topic}, which behavior correctly respects {sc.lower()} constraints?",
                "options": [
                    "Option 1: Enforces deterministic boundaries and invariant preservation",
                    "Option 2: Allows silent overflows outside defined bounds",
                    "Option 3: Bypasses validation during active execution",
                    "Option 4: Converts all exceptions into silent no-ops"
                ],
                "correct_answer": "Option 1: Enforces deterministic boundaries and invariant preservation",
                "explanation": f"Deterministic execution guarantees correctness when handling {sc} in {topic}."
            })
        return existing

    def _fallback_quiz(self, topic: str, count: int) -> List[Dict[str, Any]]:
        subconcepts = [
            "Syntax & Structure",
            "Indexing & Boundaries",
            "State Mutation",
            "Performance & Complexity",
            "Common Pitfalls",
            "Exception Handling",
            "Optimization Rules",
            "Data Consistency"
        ]
        questions = []
        for i in range(count):
            sc = subconcepts[i % len(subconcepts)]
            questions.append({
                "id": f"q_{i + 1}",
                "sub_concept": f"{topic} {sc}",
                "question": f"Regarding {topic} ({sc}), which principle guarantees correct behavior?",
                "options": [
                    "Option 1: Maintaining deterministic structural invariants and boundary checks",
                    "Option 2: Bypassing bounds validation for rapid memory allocation",
                    "Option 3: Silently ignoring type mismatches during runtime",
                    "Option 4: Executing arbitrary non-deterministic state shifts"
                ],
                "correct_answer": "Option 1: Maintaining deterministic structural invariants and boundary checks",
                "explanation": f"Structural invariants and boundary validation ensure deterministic execution for {sc} in {topic}."
            })
        return questions
