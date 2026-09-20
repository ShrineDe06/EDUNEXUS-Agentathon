# Student Quiz Agent

This project creates a lightweight AI-style quiz agent that tests students on a chosen topic, gives instant feedback, and tracks a score summary.

## Features

- Topic-based quiz flow for science, math, or history
- Adaptive scoring and feedback
- Quick demo mode for testing without an interactive session
- Simple answer evaluator that handles common variations

## Run the app

```bash
python quiz_agent.py --name "Alice" --topic science --count 3
```

## Run the demo

```bash
python quiz_agent.py --demo --topic math --count 2
```

## Generate questions with a real LLM

Set an OpenAI-compatible API key and run the quiz with LLM mode enabled:

```bash
set OPENROUTER_API_KEY=your_key_here
python quiz_agent.py --topic science --count 3 --llm
```

You can also override the model and base URL if needed:

```bash
python quiz_agent.py --topic science --count 3 --llm --model inclusionai/ling-3.0-flash --base-url https://openrouter.ai/api/v1
```

If no key is configured, the app falls back to the built-in question bank automatically.

## Notes

This version uses built-in questions by default and can optionally call an OpenAI-compatible LLM for fresh MCQ generation.
