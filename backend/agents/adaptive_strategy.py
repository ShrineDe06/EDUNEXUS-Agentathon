import os
import json
from pydantic import ValidationError
from backend.models.schemas import AdaptiveStrategyResponse

class AdaptiveStrategyAgent:
    def __init__(self, llm):
        """
        Initializes the AdaptiveStrategyAgent.
        """
        self.llm = llm

    def generate_strategy(
        self,
        topic: str,
        syllabus_context: str,
        diagnosis: dict,
        previous_remediation: str,
        verification_result: dict,
        learner_context: str,
        remediation_cycle: int
    ) -> AdaptiveStrategyResponse:
        """
        Determines how the next remediation should be meaningfully different from the previous intervention.
        """
        
        # Enforce deterministic application limit
        if remediation_cycle >= 2:
            return AdaptiveStrategyResponse(
                cycle_limit_reached=True,
                rationale="Maximum remediation cycles (2) reached. No further strategies should be generated."
            )

        schema_json = AdaptiveStrategyResponse.model_json_schema()

        system_prompt = (
            "You are an expert educational Adaptive Strategy Agent.\n"
            "Your goal is to determine how the NEXT remediation should be meaningfully different from the PREVIOUS intervention, given that the student failed verification.\n\n"
            "STRATEGY RULES:\n"
            "1. The new strategy MUST explicitly differ from the previous strategy. Do NOT simply rewrite the same explanation.\n"
            "2. Analyze the specific misconception diagnosed, the previous intervention, and the verification failure evidence.\n"
            "3. Do NOT speculate about the learner's psychology. Only use evidence available in the inputs.\n"
            "4. Ground your strategy in the provided syllabus_context as the source of truth.\n"
            "5. Examples of differing strategies:\n"
            "   - If first was a Direct Conceptual Explanation -> Second might be a Concrete Analogy + Worked Example.\n"
            "   - If first was a Textual Explanation -> Second might be Step-by-Step Problem Solving.\n"
            "   - If first was Definition-Based -> Second might Compare Two Contrasting Cases.\n"
            "6. You are ONLY determining the strategy. Do NOT generate the actual remediation text.\n\n"
            "You must respond with valid JSON that matches the following JSON Schema:\n"
            f"{json.dumps(schema_json)}\n"
        )

        user_prompt = f"Topic: {topic}\n\nSYLLABUS CONTEXT:\n{syllabus_context}\n\n"
        
        user_prompt += "DIAGNOSIS:\n"
        user_prompt += f"{json.dumps(diagnosis, indent=2)}\n\n"
        
        user_prompt += "PREVIOUS REMEDIATION INTERVENTION:\n"
        user_prompt += f"{previous_remediation}\n\n"
        
        user_prompt += "VERIFICATION RESULT (FAILURE EVIDENCE):\n"
        user_prompt += f"{json.dumps(verification_result, indent=2)}\n\n"
        
        if learner_context:
            user_prompt += f"LEARNER CONTEXT:\n{learner_context}\n\n"
            
        user_prompt += f"CURRENT REMEDIATION CYCLE: {remediation_cycle}\n"

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
            return AdaptiveStrategyResponse.model_validate(data)
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON response from LLM: {e}\nContent was: {content}")
        except ValidationError as e:
            raise ValueError(f"LLM output does not match the required schema: {e}\nContent was: {content}")
        except Exception as e:
            raise RuntimeError(f"An unexpected error occurred while parsing output: {e}")
