import os
import json
from pydantic import ValidationError
from backend.models.schemas import RemediationResponse, DiagnosisResponse

class RemediationAgent:
    def __init__(self, llm):
        """
        Initializes the RemediationAgent.
        """
        self.llm = llm

    def remediate(self, *args, **kwargs):
        """Alias for generate_remediation."""
        return self.generate_remediation(*args, **kwargs)

    def generate_remediation(
        self,
        topic: str,
        syllabus_context: str,
        diagnosis: getattr(DiagnosisResponse, "__typing_unpacked__", object),
        learner_context: str = None,
        previous_intervention: str = None,
        adaptive_strategy: str = None
    ) -> RemediationResponse:
        """
        Creates a focused learning intervention targeting a specifically diagnosed misconception.
        """
        
        if isinstance(diagnosis, dict):
            diag_obj = DiagnosisResponse.model_validate(diagnosis) if diagnosis else None
        else:
            diag_obj = diagnosis

        if not diag_obj or not getattr(diag_obj, "has_misconception", False):
            raise ValueError("Cannot generate remediation: No misconception was diagnosed.")

        schema_json = RemediationResponse.model_json_schema()

        system_prompt = (
            "You are an expert educational Remediation Agent.\n"
            "Your goal is to create a focused learning intervention targeting a specifically diagnosed misconception.\n\n"
            "REMEDIATION RULES:\n"
            "1. Address the specific misconception directly. Do NOT teach the entire topic.\n"
            "2. Ground your explanation strictly in the syllabus_context provided. Do not introduce unsupported concepts.\n"
            "3. Explain the correct conceptual model clearly.\n"
            "4. Explicitly contrast the student's likely incorrect mental model with the correct model.\n"
            "5. Include a small, relevant example.\n"
            "6. Include a short 'check your understanding' question at the end. Do not provide the answer to it.\n"
            "7. Avoid overwhelming the learner with unrelated material.\n"
            "8. Use terminology consistent with the syllabus.\n\n"
        )
        
        if learner_context or previous_intervention or adaptive_strategy:
            system_prompt += "PERSONALIZATION INSTRUCTIONS:\n"
            if learner_context:
                system_prompt += "- Use the learner_context to understand if this misconception is recurring. If so, make the explanation especially targeted.\n"
            if previous_intervention:
                system_prompt += "- The student has previously received the provided intervention. Do NOT blindly repeat it. Improve, vary, or take a different angle in your explanation.\n"
            if adaptive_strategy:
                system_prompt += f"- Adapt your teaching style based on this new strategy: {adaptive_strategy}\n"
            system_prompt += "\n"

        system_prompt += (
            "You must respond with valid JSON that matches the following JSON Schema:\n"
            f"{json.dumps(schema_json)}\n"
        )

        user_prompt = f"Topic: {topic}\n\nSYLLABUS CONTEXT:\n{syllabus_context}\n\n"
        
        user_prompt += "DIAGNOSIS TO REMEDIATE:\n"
        sub_concept = getattr(diag_obj, "sub_concept", "")
        misconception = getattr(diag_obj, "misconception", "")
        evidence = getattr(diag_obj, "evidence", [])
        user_prompt += f"Sub-concept: {sub_concept}\n"
        user_prompt += f"Misconception: {misconception}\n"
        user_prompt += f"Evidence: {', '.join(evidence) if isinstance(evidence, list) else evidence}\n\n"
        
        if learner_context:
            user_prompt += f"LEARNER CONTEXT:\n{learner_context}\n\n"
            
        if previous_intervention:
            user_prompt += f"PREVIOUS INTERVENTION:\n{previous_intervention}\n\n"

        if adaptive_strategy:
            user_prompt += f"NEW ADAPTIVE STRATEGY:\n{adaptive_strategy}\n\n"


        model_name = os.environ.get("SLICE_MODEL", "inclusionai/ling-3.0-flash")

        try:
            response = self.llm.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
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
            return RemediationResponse.model_validate(data)
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON response from LLM: {e}\nContent was: {content}")
        except ValidationError as e:
            raise ValueError(f"LLM output does not match the required schema: {e}\nContent was: {content}")
        except Exception as e:
            raise RuntimeError(f"An unexpected error occurred while parsing output: {e}")
