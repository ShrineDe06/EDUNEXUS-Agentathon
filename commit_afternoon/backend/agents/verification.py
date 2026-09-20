import os
import json
from typing import List, Optional
from pydantic import ValidationError
from backend.models.schemas import VerificationQuestion, VerificationResponse

class VerificationAgent:
    def __init__(self, llm):
        """
        Initializes the VerificationAgent.
        """
        self.llm = llm

    def generate_questions(
        self,
        topic: str,
        syllabus_context: str,
        diagnosis: dict,
        remediation: dict,
        previous_question_ids: List[str],
        learner_context: Optional[str] = None
    ) -> VerificationResponse:
        """
        Generates 2 verification questions targeting the specific diagnosed misconception after remediation.
        """
        schema_json = VerificationResponse.model_json_schema()

        misconception_text = diagnosis.get("misconception", "") if isinstance(diagnosis, dict) else getattr(diagnosis, "misconception", "")
        sub_concept_text = diagnosis.get("sub_concept", "") if isinstance(diagnosis, dict) else getattr(diagnosis, "sub_concept", "")
        remediation_explanation = remediation.get("explanation", "") if isinstance(remediation, dict) else getattr(remediation, "explanation", "")

        system_prompt = (
            "You are an expert educational Verification Agent.\n"
            "Your goal is to generate exactly 2 distinct, high-quality verification questions (multiple-choice) "
            "to check whether a learner has successfully corrected a specific diagnosed misconception after remediation.\n\n"
            "VERIFICATION RULES:\n"
            "1. Generate exactly 2 questions targeting the remediated sub-concept and misconception.\n"
            "2. Each question MUST have exactly 4 clear options (MCQ).\n"
            "3. Ground all questions strictly in the syllabus_context provided.\n"
            "4. Do NOT repeat or duplicate previous question concepts or texts.\n"
            "5. Make questions test true conceptual understanding rather than simple recall.\n\n"
            "You must respond with valid JSON that matches the following JSON Schema:\n"
            f"{json.dumps(schema_json)}\n"
        )

        user_prompt = (
            f"Topic: {topic}\n\n"
            f"SYLLABUS CONTEXT:\n{syllabus_context}\n\n"
            f"DIAGNOSED MISCONCEPTION:\nSub-concept: {sub_concept_text}\nMisconception: {misconception_text}\n\n"
            f"REMEDIATION PROVIDED:\n{remediation_explanation}\n\n"
            f"PREVIOUS QUESTIONS ASKED:\n{json.dumps(previous_question_ids)}\n"
        )

        model_name = os.environ.get("SLICE_MODEL", "inclusionai/ling-3.0-flash")

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
            raise RuntimeError(f"OpenRouter API failure during verification generation: {e}")

        try:
            content = response.choices[0].message.content
            if content.startswith("```json"):
                content = content[7:-3]
            elif content.startswith("```"):
                content = content[3:-3]

            data = json.loads(content)
            return VerificationResponse.model_validate(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON response from LLM: {e}\nContent was: {content}")
        except ValidationError as e:
            raise ValueError(f"LLM output does not match the required schema: {e}\nContent was: {content}")
        except Exception as e:
            raise RuntimeError(f"An unexpected error occurred while parsing output: {e}")

