# Run the EDUNEXUS demo

Run these steps from the repository root.

## One-time setup

```bash
python -m pip install -r requirements.txt
```

Create `.env` and provide your OpenRouter credential. Never commit the real key:

```dotenv
OPENROUTER_API_KEY=your-openrouter-key
SLICE_MODEL=inclusionai/ling-3.0-flash
SLICE_FALLBACK_MODEL=mistralai/mistral-small-3.2-24b-instruct
SLICE_ESCALATION_MODEL=anthropic/claude-haiku-4.5
MISTRAL_API_KEY=
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_HOST=https://cloud.langfuse.com
SLICE_MAX_TOKENS_PER_RUN=250000
SLICE_MAX_TOKENS=1200
SLICE_MAX_ATTEMPTS_PER_STEP=3
SLICE_EXPERT_TIMEOUT_MINUTES=45
```

## Demo command

```bash
python server.py
```

Open <http://localhost:8000> in a browser. Keep the terminal running during the demo. Network access is required for model calls and for the browser-delivered React dependencies.
