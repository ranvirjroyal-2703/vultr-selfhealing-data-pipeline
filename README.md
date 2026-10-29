# Self-Healing + Cost-Aware Data Pipeline

**Vultr Agent Rush Hackathon — Blast Radius Zero**

Autonomous data cleaning agent that proposes multiple strategies, executes them inside hard-limited Docker sandboxes, repairs failures from the real stderr, and ranks survivors by cost.

## Key features
- Multi-strategy generation via Vultr Serverless Inference
- Isolated Docker sandboxes (memory, CPU, timeout, no network, non-root)
- Self-healing: a failed run is repaired once from the sandbox error and executed again
- Explicit cost: `seconds × (memory_mb / 256)`. Failures are penalized. Lowest successful cost wins
- Sample dataset at `data/messy_orders.csv` and a fixed click-path in `DEMO.md`
- One-click containment demo (infinite loop killed by the sandbox)

## Local run
```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export VULTR_INFERENCE_API_KEY=your_key
streamlit run app.py
```

## Vultr deployment
1. Create a Vultr Compute Instance (Ubuntu) and install Docker.
2. Claim the $200 hackathon credits at kickoff.
3. Clone this repo on the VM.
4. Build and run (mount the Docker socket so sandboxes can launch):
```bash
docker build -t data-pipeline .
docker run -d \
  -p 8501:8501 \
  -e VULTR_INFERENCE_API_KEY=your_key \
  -v /var/run/docker.sock:/var/run/docker.sock \
  data-pipeline
```
5. Open `http://YOUR_VM_IP:8501`

## Architecture
- **Vultr VM**: hosts the Streamlit app
- **Vultr Serverless Inference**: strategy generation and the heal step
- **Docker sandboxes**: isolation, resource limits, auto-remove, no secrets inside the sandbox
- **Containment proof**: forced demo button, required on camera

Record the video by following [DEMO.md](DEMO.md).

## License
MIT
