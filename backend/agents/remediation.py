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
        """Flexible alias for generate_remediation supporting both standard diagnosis objects and direct kwargs."""
        if "diagnosis" in kwargs:
            return self.generate_remediation(*args, **kwargs)
        if len(args) >= 3 and isinstance(args[2], (DiagnosisResponse, dict)):
            return self.generate_remediation(*args, **kwargs)

        topic = kwargs.get("topic") or (args[0] if len(args) > 0 else "")
        sub_concept = kwargs.get("sub_concept", "")
        misconception = kwargs.get("misconception", "")
        evidence = kwargs.get("student_answer") or kwargs.get("evidence", [])
        if isinstance(evidence, str):
            evidence = [evidence] if evidence else ["Student answer pattern"]
        elif not evidence:
            evidence = ["Student answer pattern"]
        syllabus_context = kwargs.get("source_context") or kwargs.get("syllabus_context", "")

        diag_obj = DiagnosisResponse(
            has_misconception=bool(misconception),
            sub_concept=sub_concept,
            misconception=misconception,
            evidence=evidence,
            confidence=0.85,
            thinking_process="Remediation for detected misconception"
        )
        return self.generate_remediation(
            topic=topic,
            syllabus_context=syllabus_context,
            diagnosis=diag_obj,
            learner_context=kwargs.get("learner_context"),
            previous_intervention=kwargs.get("previous_intervention"),
            adaptive_strategy=kwargs.get("adaptive_strategy")
        )

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
            "You are an expert educational Remediation Agent operating in a looping reflection cycle.\n"
            "Your goal is to create a highly focused learning intervention targeting a specifically diagnosed misconception.\n\n"
            "DYNAMIC REASONING REQUIREMENT:\n"
            "You MUST generate a detailed, non-hardcoded `thinking_process` string in your JSON output detailing your step-by-step agentic thoughts:\n"
            "- Step 1: Analyze the diagnosed misconception and evidence from student results.\n"
            "- Step 2: Inspect student database progress & past interventions to see what failed previously.\n"
            "- Step 3: Align with any new adaptive strategy provided.\n"
            "- Step 4: Self-critique your draft explanation to ensure it explicitly contrasts the incorrect mental model with the correct one.\n\n"
            "REMEDIATION RULES:\n"
            "1. Address the specific misconception directly. Do NOT teach the entire topic.\n"
            "2. Ground your explanation in the context provided.\n"
            "3. Explain the correct conceptual model clearly.\n"
            "4. Explicitly contrast the student's incorrect mental model with the correct model.\n"
            "5. Include a small, relevant code/conceptual example.\n"
            "6. Include a short 'check your understanding' question at the end.\n\n"
        )
        
        if learner_context or previous_intervention or adaptive_strategy:
            system_prompt += "PERSONALIZATION & ADAPTATION INSTRUCTIONS:\n"
            if learner_context:
                system_prompt += f"- Student DB Progress: {learner_context}\n"
            if previous_intervention:
                system_prompt += f"- Previous Failed Intervention: {previous_intervention}\n  Do NOT repeat this failed explanation. Pivot to a different angle!\n"
            if adaptive_strategy:
                system_prompt += f"- New Adaptive Strategy: {adaptive_strategy}\n  You MUST structure your explanation around this new instructional approach!\n"
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


        model_name = os.environ.get("NVIDIA_MODEL", "nvidia/nemotron-3-ultra-550b-a55b")

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
            raise RuntimeError(f"NVIDIA API failure: {e}")

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
