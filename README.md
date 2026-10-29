# Self-Healing + Cost-Aware Data Pipeline

**Vultr Agent Rush Hackathon — Blast Radius Zero**

An autonomous data cleaning agent that proposes multiple strategies, executes them in isolated sandboxes with resource limits, measures real outcomes (success, time, memory), selects the best path, and self-heals on failure. Every run produces a clear containment proof.

## Why this project
- Real multi-strategy execution inside hard-limited sandboxes
- Visible self-healing loop driven by actual runtime results
- Cost-aware selection (time + memory + success)
- Clear “blast radius zero” moment for the demo video
- Production-style web UI

## Architecture
- **Orchestrator** (runs on Vultr VM): plans strategies, dispatches to sandboxes, collects metrics, decides next action
- **Sandbox Runner**: Docker containers with CPU/memory/time limits, no network, non-root, auto-remove
- **LLM**: Vultr Serverless Inference (`https://api.vultrinference.com/v1`)
- **UI**: Streamlit web application

## Setup (local development)
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export VULTR_INFERENCE_API_KEY=your_key
streamlit run app.py
```

## Vultr Deployment Notes
- Deploy the Streamlit/FastAPI app on a Vultr Compute Instance (VM)
- All LLM calls go through Vultr Serverless Inference
- Sandboxes run as Docker containers on the same VM (or throwaway instances)
- Document resource limits and lifecycle in the final README

## Demo Video Requirements
Must show at least one containment moment (infinite loop or destructive command killed by the sandbox while other strategies continue).

## License
MIT
