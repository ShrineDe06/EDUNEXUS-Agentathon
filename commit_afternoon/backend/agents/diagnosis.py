import os
import json
from pydantic import ValidationError
from backend.models.schemas import DiagnosisResponse

class DiagnosisAgent:
    def __init__(self, llm):
        """
        Initializes the DiagnosisAgent.
        """
        self.llm = llm

    def diagnose(
        self,
        topic: str,
        syllabus_context: str,
        question_results: list,
        learner_context: str = None
    ) -> DiagnosisResponse:
        """
        Analyzes a student's responses to diagnostic questions and identifies likely recurring misconceptions.
        """
        
        schema_json = DiagnosisResponse.model_json_schema()

        system_prompt = (
            "You are an expert educational Diagnosis Agent.\n"
            "Your goal is to analyze a student's diagnostic test results and identify likely recurring misconceptions.\n"
            "A misconception is a specific conceptual misunderstanding that explains incorrect responses.\n\n"
            "DIAGNOSIS RULES:\n"
            "1. If the student has any incorrect responses indicating a conceptual misunderstanding, set has_misconception=True.\n"
            "2. Identify the core sub-concept and describe the specific misconception in detail.\n"
            "3. List all affected question identifiers in affected_question_ids (e.g. ['Q2', 'Q4', 'Q5']).\n"
            "4. Set has_misconception=False ONLY IF the student demonstrated complete mastery with all answers correct or no conceptual flaws.\n"
            "5. The syllabus_context is the authoritative source for the underlying concept. Do not introduce concepts absent from it.\n"
            "6. Explain the relationship between the syllabus concept and the student's response pattern in your evidence.\n"
            "7. Confidence must reflect the strength of the evidence (0.0 to 1.0).\n\n"
        )
        
        if learner_context:
            system_prompt += (
                "LEARNER HISTORY INSTRUCTIONS:\n"
                "You have access to the student's past learner history. Use this to determine if the current evidence repeats a known issue or suggests a different one.\n"
                "Do not blindly assume a previous misconception is still present. Current evidence must still support your diagnosis.\n\n"
            )
            
        system_prompt += (
            "You must respond with valid JSON that matches the following JSON Schema:\n"
            f"{json.dumps(schema_json)}\n"
        )

        user_prompt = f"Topic: {topic}\n\nSYLLABUS CONTEXT:\n{syllabus_context}\n\n"
        
        if learner_context:
            user_prompt += f"LEARNER HISTORY:\n{learner_context}\n\n"
            
        user_prompt += "STUDENT DIAGNOSTIC RESULTS:\n"
        for idx, res in enumerate(question_results, 1):
            status = "CORRECT" if res.get('is_correct') else "INCORRECT"
            user_prompt += f"Q{idx}:\n"
            user_prompt += f"  Sub-concept: {res.get('sub_concept')}\n"
            user_prompt += f"  Question: {res.get('question')}\n"
            user_prompt += f"  Student Answer: {res.get('student_answer')}\n"
            user_prompt += f"  Correct Answer: {res.get('correct_answer')}\n"
            user_prompt += f"  Result: {status}\n\n"

        model_name = os.environ.get("SLICE_MODEL", "inclusionai/ling-3.0-flash")

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
            raise RuntimeError(f"OpenRouter API failure: {e}")

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
