# October close cleaner

**Vultr Agent Rush — Blast Radius Zero**

Finance has one messy October export. The agent proposes cleans, runs each inside a Docker sandbox, and when the first guess uses columns that do not exist, it repairs the code from the real stderr and runs it again. Survivors are ranked by cost. The same sandbox is then shown killing an infinite loop.

## What the demo shows, in order
1. A planted bad strategy fails with a real `KeyError`.
2. Vultr Inference rewrites that code from the stderr. The second sandbox run is on screen next to the first.
3. A cost table picks the cheapest successful clean.
4. An infinite loop is killed by the sandbox while the app stays up.

One button does all four: **Run judge demo**. Click-path: [DEMO.md](DEMO.md).

## Run locally
```bash
pip install -r requirements.txt
docker build -t data-pipeline-sandbox -f sandbox/Dockerfile sandbox
export VULTR_INFERENCE_API_KEY=your_key
streamlit run app.py
```

## Deploy on a Vultr VM
Install Docker, claim the $200 credits, clone the repo, then:

```bash
./deploy.sh YOUR_VULTR_INFERENCE_API_KEY
```

That builds the sandbox image and the app, and prints the public URL.

## What runs where
- Vultr VM: the Streamlit app
- Vultr Serverless Inference: strategy ideas and the heal step
- `data-pipeline-sandbox` container: untrusted code, no network, memory and CPU caps, non-root, removed after each run

MIT License
