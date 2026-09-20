# Run the EDUNEXUS demo

Run these steps from the repository root.

## One-time setup

```bash
python -m pip install -r requirements.txt
```

Create `.env` and provide the model credential used by the integrated FastAPI demo:

```dotenv
NVIDIA_API_KEY=your-key
NVIDIA_MODEL=nvidia/nemotron-3-super-120b-a12b
```

## Demo command

```bash
python server.py
```

Open <http://localhost:8000> in a browser. Keep the terminal running during the demo. Network access is required for model calls and for the browser-delivered React dependencies.
