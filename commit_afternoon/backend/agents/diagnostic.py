import os
import json
from pydantic import ValidationError
from backend.models.schemas import DiagnosticResponse

class DiagnosticAgent:
    def __init__(self, llm):
        """
        Initializes the DiagnosticAgent.
        
        :param llm: An instance of an OpenAI client or a similar client
                    configured to talk to OpenRouter.
        """
        self.llm = llm

    def generate_questions(self, topic: str, syllabus_context: str, learner_context: str = None) -> DiagnosticResponse:
        """
        Generates exactly 5 diagnostic questions based on the topic and syllabus context.
        Optionally uses learner_context to adapt questions to the student's weaknesses.
        """
        if not topic or not topic.strip():
            raise ValueError("Topic cannot be empty")
        if not syllabus_context or not syllabus_context.strip():
            raise ValueError("Syllabus context cannot be empty")

        schema_json = DiagnosticResponse.model_json_schema()

        system_prompt = (
            "You are an expert educational Diagnostic Agent.\n"
            "Your goal is to generate exactly 5 diagnostic questions based ONLY on the provided syllabus context.\n"
            "Do not introduce concepts that are absent from the syllabus context.\n"
            "Focus on 2 to 3 core sub-concepts from the context, creating 2 to 3 questions per sub-concept.\n"
            "Tag every question with its corresponding sub-concept.\n"
            "Prefer questions that expose conceptual misunderstandings.\n"
            "Use appropriate question types such as conceptual, application, reasoning, or code/problem interpretation.\n"
            "Avoid duplicate or near-duplicate questions.\n"
            "Keep difficulty appropriate for diagnosis.\n"
            "Ensure each question can be answered independently.\n"
            "Include the correct answer and a concise explanation of why the answer is correct.\n"
            "Do not reveal the answer inside the question itself.\n\n"
        )
        
        if learner_context:
            system_prompt += (
                "LEARNER HISTORY ADAPTATION INSTRUCTIONS:\n"
                "- Use the provided learner history to adapt question selection.\n"
                "- Give additional diagnostic attention to weak sub-concepts.\n"
                "- Check whether previously observed weaknesses still exist.\n"
                "- Do not assume that a misconception is still present without testing it.\n"
                "- Do not ignore strong areas completely; maintain reasonable coverage.\n"
                "- Do not invent concepts based on learner history.\n"
                "- Do not repeat previous questions unnecessarily.\n\n"
            )
            
        system_prompt += (
            "You must respond with valid JSON that matches the following JSON Schema:\n"
            f"{json.dumps(schema_json)}\n"
        )

        user_prompt = f"Topic: {topic}\n\nSYLLABUS CONTEXT:\n{syllabus_context}\n"
        if learner_context:
            user_prompt += f"\nLEARNER HISTORY:\n{learner_context}\n"

        model_name = os.environ.get("SLICE_MODEL", "inclusionai/ling-3.0-flash")

        try:
            response = self.llm.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                # Ensure the model tries to return JSON
                response_format={"type": "json_object"},
                temperature=0.2, # Low temperature for more deterministic/structured output
                stream=False
            )
        except Exception as e:
            raise RuntimeError(f"OpenRouter API failure: {e}")

        try:
            content = response.choices[0].message.content
            # The model could wrap JSON in markdown blocks
            if content.startswith("```json"):
                content = content[7:-3]
            elif content.startswith("```"):
                content = content[3:-3]

            data = json.loads(content)
            
            # If the response just returned a list instead of an object, wrap it
            if isinstance(data, list):
                data = {"questions": data}
            elif "questions" not in data:
                # Fallback if it returned some other key
                for key, val in data.items():
                    if isinstance(val, list):
                        data = {"questions": val}
                        break
                        
            return DiagnosticResponse.model_validate(data)
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON response from LLM: {e}\nContent was: {content}")
        except ValidationError as e:
            raise ValueError(f"LLM output does not match the required schema: {e}\nContent was: {content}")
        except Exception as e:
            raise RuntimeError(f"An unexpected error occurred while parsing output: {e}")
