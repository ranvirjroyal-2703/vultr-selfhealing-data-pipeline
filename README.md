# Self-Healing + Cost-Aware Data Pipeline

**Vultr Agent Rush Hackathon — Blast Radius Zero**

Autonomous data cleaning agent that proposes multiple strategies, executes them inside hard-limited Docker sandboxes, measures real outcomes, selects the best path, and self-heals. Every run can demonstrate blast-radius-zero containment.

## Key Features
- Multi-strategy generation via Vultr Serverless Inference
- Isolated Docker sandboxes (memory, CPU, timeout, no network, non-root)
- Metrics dashboard (success, duration, containment events)
- One-click forced containment demo (infinite loop killed by sandbox)
- Clean Streamlit UI ready for public demo

## Local Run
```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export VULTR_INFERENCE_API_KEY=your_key
streamlit run app.py
```

## Vultr Deployment (recommended)
1. Create a Vultr Compute Instance (Ubuntu) and install Docker.
2. Claim $200 hackathon credits.
3. Clone this repo on the VM.
4. Build and run (mount Docker socket so sandboxes can launch):
```bash
docker build -t data-pipeline .
docker run -d \
  -p 8501:8501 \
  -e VULTR_INFERENCE_API_KEY=your_key \
  -v /var/run/docker.sock:/var/run/docker.sock \
  data-pipeline
```
5. Open `http://YOUR_VM_IP:8501`

## Architecture Mapping to Hackathon Rules
- **Vultr VM**: Hosts the Streamlit app (central control plane)
- **Vultr Serverless Inference**: All LLM strategy generation
- **Docker sandboxes**: Process isolation, resource limits, lifecycle (auto-remove), secret hygiene
- **Containment proof**: Visible in UI + forced demo button

## Demo Video Checklist
- Show strategy generation
- Show multiple strategies executing
- Show metrics dashboard
- Click “Force Containment Demo” and show the sandbox killing the infinite loop
- Highlight blast radius = zero

## License
MIT
