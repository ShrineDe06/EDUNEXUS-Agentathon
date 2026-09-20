from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class Question:
    prompt: str
    answer: str
    keywords: List[str]
    explanation: str
    difficulty: str
    options: List[str] = field(default_factory=list)


class StudentQuizAgent:
    def __init__(
        self,
        topic: str,
        use_llm: bool = False,
        llm_api_key: str | None = None,
        llm_model: str | None = None,
        llm_base_url: str | None = None,
    ):
        self.topic = topic.lower()
        self.use_llm = use_llm
        self.llm_api_key = llm_api_key or os.getenv("OPENROUTER_API_KEY") or os.getenv("LLM_API_KEY")
        self.llm_model = llm_model or os.getenv("SLICE_MODEL") or os.getenv("LLM_MODEL") or "inclusionai/ling-3.0-flash"
        self.llm_base_url = llm_base_url or os.getenv("OPENROUTER_BASE_URL") or os.getenv("LLM_BASE_URL") or "https://openrouter.ai/api/v1"
        self.question_bank: Dict[str, List[Question]] = {
            "science": [
                Question(
                    prompt="What do plants use to make food during photosynthesis?",
                    answer="sunlight, water, and carbon dioxide",
                    keywords=["sunlight", "water", "carbon", "dioxide"],
                    explanation="Plants use sunlight, water, and carbon dioxide to create glucose and oxygen.",
                    difficulty="easy",
                    options=[
                        "Sunlight, water, and carbon dioxide",
                        "Only sunlight",
                        "Soil and oxygen",
                        "Moonlight and rocks",
                    ],
                ),
                Question(
                    prompt="What gas do humans breathe in that plants absorb?",
                    answer="carbon dioxide",
                    keywords=["carbon", "dioxide"],
                    explanation="Humans exhale carbon dioxide, and plants absorb it during photosynthesis.",
                    difficulty="easy",
                    options=[
                        "Carbon dioxide",
                        "Oxygen",
                        "Nitrogen",
                        "Hydrogen",
                    ],
                ),
                Question(
                    prompt="What is the main function of the heart in the human body?",
                    answer="to pump blood throughout the body",
                    keywords=["pump", "blood"],
                    explanation="The heart circulates blood so oxygen and nutrients reach tissues and organs.",
                    difficulty="medium",
                    options=[
                        "To pump blood throughout the body",
                        "To digest food",
                        "To filter waste from the blood",
                        "To control breathing",
                    ],
                ),
                Question(
                    prompt="Which organ is responsible for filtering waste from the blood?",
                    answer="kidneys",
                    keywords=["kidney"],
                    explanation="The kidneys filter blood, remove waste, and help regulate water and salts.",
                    difficulty="medium",
                    options=[
                        "Kidneys",
                        "Lungs",
                        "Liver",
                        "Brain",
                    ],
                ),
            ],
            "math": [
                Question(
                    prompt="What is 12 + 8?",
                    answer="20",
                    keywords=["20"],
                    explanation="Twelve plus eight equals twenty.",
                    difficulty="easy",
                    options=["20", "26", "18", "24"],
                ),
                Question(
                    prompt="What is 9 x 6?",
                    answer="54",
                    keywords=["54"],
                    explanation="Nine times six equals fifty-four.",
                    difficulty="easy",
                    options=["54", "56", "48", "60"],
                ),
                Question(
                    prompt="Solve: 3x = 21. What is x?",
                    answer="7",
                    keywords=["7"],
                    explanation="Divide both sides by 3: x = 21 / 3 = 7.",
                    difficulty="medium",
                    options=["5", "7", "8", "9"],
                ),
                Question(
                    prompt="What is the perimeter of a rectangle with length 5 and width 3?",
                    answer="16",
                    keywords=["16"],
                    explanation="Perimeter is 2(l + w) = 2(5 + 3) = 16.",
                    difficulty="medium",
                    options=["12", "14", "16", "18"],
                ),
            ],
            "history": [
                Question(
                    prompt="Who was the first president of the United States?",
                    answer="george washington",
                    keywords=["george", "washington"],
                    explanation="George Washington served as the first U.S. president from 1789 to 1797.",
                    difficulty="easy",
                    options=[
                        "George Washington",
                        "Abraham Lincoln",
                        "Thomas Jefferson",
                        "John Adams",
                    ],
                ),
                Question(
                    prompt="Which ancient civilization built pyramids in Egypt?",
                    answer="ancient egyptians",
                    keywords=["egyptian", "egyptians"],
                    explanation="The ancient Egyptians built the pyramids as monumental structures and tombs.",
                    difficulty="medium",
                    options=[
                        "Ancient Egyptians",
                        "Romans",
                        "Greeks",
                        "Vikings",
                    ],
                ),
                Question(
                    prompt="What event began in 1775 and led to the American Revolution?",
                    answer="the battles of lexington and concord",
                    keywords=["lexington", "concord"],
                    explanation="The fighting at Lexington and Concord marked the start of the American Revolutionary War.",
                    difficulty="medium",
                    options=[
                        "The Battles of Lexington and Concord",
                        "The Boston Tea Party",
                        "The signing of the Declaration of Independence",
                        "The Civil War",
                    ],
                ),
            ],
        }

        self.available_questions = list(self.question_bank.get(self.topic, []))
        if not self.available_questions:
            raise ValueError(f"Unsupported topic '{topic}'. Choose from: {', '.join(self.question_bank.keys())}.")

    @staticmethod
    def normalize(value: str) -> str:
        text = value.lower().strip()
        text = text.replace("&", " and ")
        text = re.sub(r"[^a-z0-9\s]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def resolve_mcq_choice(self, student_answer: str, question: Question) -> str:
        if not question.options:
            return student_answer

        answer = student_answer.strip()
        if not answer:
            return answer

        normalized_input = self.normalize(answer)
        if normalized_input in {"a", "b", "c", "d"}:
            index = ord(normalized_input) - ord("a")
            if 0 <= index < len(question.options):
                return question.options[index]

        if normalized_input.isdigit():
            index = int(normalized_input) - 1
            if 0 <= index < len(question.options):
                return question.options[index]

        for option in question.options:
            if self.normalize(option) == normalized_input:
                return option

        return answer

    def parse_llm_questions(self, response_text: str) -> List[Question]:
        cleaned = response_text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\s*```$", "", cleaned)

        parsed = json.loads(cleaned)

        if isinstance(parsed, dict):
            if "choices" in parsed:
                content = parsed["choices"][0]["message"]["content"]
                parsed = json.loads(content)
            elif "questions" in parsed:
                parsed = parsed["questions"]
            elif "data" in parsed:
                parsed = parsed["data"]

        if not isinstance(parsed, list):
            return []

        questions: List[Question] = []
        for item in parsed:
            prompt = str(item.get("prompt") or item.get("question") or "").strip()
            answer = str(item.get("answer") or item.get("correct_answer") or "").strip()
            options = [str(option).strip() for option in item.get("options", []) if str(option).strip()]
            explanation = str(item.get("explanation") or "").strip()
            difficulty = str(item.get("difficulty") or "medium").strip() or "medium"

            if not prompt or not answer:
                continue

            if not options:
                options = [answer, "Option B", "Option C", "Option D"]

            questions.append(
                Question(
                    prompt=prompt,
                    answer=answer,
                    keywords=self.normalize(answer).split(),
                    explanation=explanation or "No additional explanation provided.",
                    difficulty=difficulty,
                    options=options[:4],
                )
            )

        return questions

    def generate_llm_questions(self, count: int) -> List[Question]:
        if not self.llm_api_key:
            return []

        prompt = (
            "Generate exactly "
            f"{count} multiple-choice questions about {self.topic}. "
            "Return valid JSON only as an array of objects with keys: "
            "prompt, answer, options, explanation, difficulty. "
            "Each object must include 4 answer options and the correct answer must match one of the options."
        )

        payload = {
            "model": self.llm_model,
            "messages": [
                {"role": "system", "content": "You create educational quiz questions in JSON format only."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
        }

        request = urllib.request.Request(
            f"{self.llm_base_url.rstrip('/')}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.llm_api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                response_text = response.read().decode("utf-8")
                parsed = json.loads(response_text)
                content = parsed["choices"][0]["message"]["content"]
                return self.parse_llm_questions(content)
        except (urllib.error.URLError, ValueError, KeyError, json.JSONDecodeError) as exc:
            print(f"Warning: unable to generate LLM questions: {exc}")
            return []

    def evaluate_answer(self, student_answer: str, question: Question) -> bool:
        resolved_answer = self.resolve_mcq_choice(student_answer, question)
        normalized_guess = self.normalize(resolved_answer)
        normalized_answer = self.normalize(question.answer)

        if not normalized_guess:
            return False

        if normalized_guess == normalized_answer:
            return True

        if normalized_answer in normalized_guess or normalized_guess in normalized_answer:
            return True

        guess_words = set(normalized_guess.split())
        answer_words = set(normalized_answer.split())
        overlap = guess_words & answer_words

        # require strong overlap for multi-word answers
        if len(answer_words) <= 2:
            return len(overlap) >= max(1, len(answer_words) - 1)

        return len(overlap) >= max(2, len(answer_words) // 2)

    def pick_questions(self, count: int) -> List[Question]:
        questions = self.available_questions[:]
        if self.use_llm:
            llm_questions = self.generate_llm_questions(count)
            if llm_questions:
                return llm_questions[:count]
            print("LLM generation failed or no API key was provided. Falling back to local questions.")

        shuffled = questions[:]
        random.shuffle(shuffled)
        return shuffled[:count]

    def run_quiz(self, student_name: str, count: int) -> Dict[str, object]:
        questions = self.pick_questions(min(count, len(self.available_questions)))
        score = 0
        results: List[str] = []

        print(f"\nWelcome, {student_name}! I'll quiz you on {self.topic.title()}.")
        print("Answer as best you can. I'll give feedback after each question.\n")

        for index, question in enumerate(questions, start=1):
            print(f"Question {index}/{len(questions)}")
            print(question.prompt)
            if question.options:
                for option_index, option in enumerate(question.options):
                    print(f"  {chr(65 + option_index)}. {option}")
            response = input("Your answer (A/B/C/D or text): ").strip()

            if self.evaluate_answer(response, question):
                score += 1
                print("Correct! " + question.explanation)
                results.append(f"Q{index}: Correct")
            else:
                print(f"Not quite. {question.explanation}")
                results.append(f"Q{index}: Incorrect")

            print("-" * 50)

        percentage = (score / len(questions)) * 100 if questions else 0
        print(f"\nFinal score: {score}/{len(questions)} ({percentage:.0f}%)")

        if percentage >= 80:
            feedback = "Excellent work. You are ready for a tougher challenge."
        elif percentage >= 50:
            feedback = "Good job. A little more practice will make you even stronger."
        else:
            feedback = "Keep going. Review the explanations and try another round."

        print(feedback)

        return {
            "student_name": student_name,
            "topic": self.topic,
            "score": score,
            "total": len(questions),
            "percentage": percentage,
            "results": results,
        }


def run_demo(topic: str, count: int, use_llm: bool = False, llm_api_key: str | None = None):
    demo_answers = {
        "science": [
            "sunlight and water and carbon dioxide",
            "carbon dioxide",
            "pump blood throughout the body",
            "kidneys",
        ],
        "math": [
            "20",
            "54",
            "7",
            "16",
        ],
        "history": [
            "george washington",
            "ancient egyptians",
            "the battles of lexington and concord",
        ],
    }

    agent = StudentQuizAgent(topic, use_llm=use_llm, llm_api_key=llm_api_key)
    questions = agent.pick_questions(min(count, len(agent.available_questions)))
    answers = demo_answers.get(topic, [])

    score = 0
    print(f"\nDemo mode active for topic: {topic.title()}\n")
    for index, question in enumerate(questions, start=1):
        print(f"Question {index}/{len(questions)}")
        print(question.prompt)
        if question.options:
            for option_index, option in enumerate(question.options):
                print(f"  {chr(65 + option_index)}. {option}")
        answer = answers[index - 1] if index - 1 < len(answers) else "wrong answer"
        print(f"Sample answer: {answer}")

        is_correct = agent.evaluate_answer(answer, question)
        if is_correct:
            score += 1
            print("Correct! " + question.explanation)
        else:
            print(f"Not quite. {question.explanation}")
        print("-" * 50)

    percentage = (score / len(questions)) * 100 if questions else 0
    print(f"\nDemo score: {score}/{len(questions)} ({percentage:.0f}%)")


def main():
    parser = argparse.ArgumentParser(description="AI student quiz assistant")
    parser.add_argument("--topic", choices=["science", "math", "history"], default="science")
    parser.add_argument("--count", type=int, default=3)
    parser.add_argument("--demo", action="store_true", help="Run a non-interactive demonstration with sample responses")
    parser.add_argument("--llm", action="store_true", help="Generate fresh multiple-choice questions using an OpenAI-compatible LLM")
    parser.add_argument("--model", default=None, help="LLM model name to use when generating questions")
    parser.add_argument("--base-url", default=None, help="OpenAI-compatible API base URL for LLM calls")
    parser.add_argument("--api-key", default=None, help="API key for the LLM provider")
    parser.add_argument("--name", default="Student")
    args = parser.parse_args()

    if args.count <= 0:
        print("Question count must be greater than zero.")
        sys.exit(1)

    try:
        if args.demo:
            run_demo(args.topic, args.count, use_llm=args.llm, llm_api_key=args.api_key)
        else:
            agent = StudentQuizAgent(
                args.topic,
                use_llm=args.llm,
                llm_api_key=args.api_key,
                llm_model=args.model,
                llm_base_url=args.base_url,
            )
            agent.run_quiz(args.name, args.count)
    except ValueError as exc:
        print(f"Error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
