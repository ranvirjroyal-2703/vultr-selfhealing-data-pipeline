"""
Streamlit UI — Self-Healing + Cost-Aware Data Pipeline
Includes parallel-style results view, metrics dashboard, and forced containment demo.
"""

import streamlit as st
import pandas as pd
from agent import DataPipelineAgent
from sandbox_runner import SandboxRunner

st.set_page_config(page_title="Self-Healing Data Pipeline", layout="wide")
st.title("Self-Healing + Cost-Aware Data Pipeline")
st.caption("Vultr Agent Rush — Blast Radius Zero | Multi-strategy sandboxed cleaning")

# Sidebar controls
with st.sidebar:
    st.header("Sandbox Limits")
    memory = st.selectbox("Memory limit", ["128m", "256m", "512m"], index=1)
    timeout = st.slider("Timeout (seconds)", 5, 30, 12)
    st.info("All strategies run with these hard limits. Containment is enforced by the sandbox.")

uploaded = st.file_uploader("Upload messy CSV", type=["csv"])
goal = st.text_area("Cleaning goal", value="Remove duplicates, standardize column names, fix obvious type issues, and drop completely empty rows.", height=80)

col1, col2 = st.columns(2)
run_pipeline = col1.button("Run Pipeline", type="primary", use_container_width=True)
run_containment = col2.button("Force Containment Demo", use_container_width=True)

if run_containment:
    st.subheader("Containment Demo")
    st.write("Running a deliberately dangerous snippet inside the sandbox...")
    dangerous = '''
import time
print("Starting infinite loop...")
while True:
    time.sleep(0.1)
'''
    runner = SandboxRunner(memory_limit=memory, timeout_sec=8)
    result = runner.run(dangerous)
    if result.timed_out or result.killed_by_limit:
        st.success("Blast radius = zero. Sandbox killed the infinite loop.")
        st.json({
            "timed_out": result.timed_out,
            "killed_by_limit": result.killed_by_limit,
            "duration_sec": result.duration_sec,
            "stderr_snippet": result.stderr[:300]
        })
    else:
        st.warning("Containment did not trigger as expected.")

if run_pipeline and uploaded is not None:
    raw = uploaded.getvalue().decode("utf-8", errors="replace")
    sample = "\n".join(raw.splitlines()[:10])

    agent = DataPipelineAgent()
    agent.sandbox.memory_limit = memory
    agent.sandbox.timeout_sec = timeout

    with st.spinner("Generating strategies with Vultr Inference..."):
        strategies = agent.propose_strategies(sample, goal)

    st.subheader("Proposed Strategies")
    for s in strategies:
        with st.expander(s.get("name", "Unnamed"), expanded=False):
            st.write(s.get("description", ""))
            st.code(s.get("code", ""), language="python")

    # Execute (sequential for reliability in hackathon demo; can be parallelized with threads)
    results = []
    progress = st.progress(0)
    status_placeholder = st.empty()

    for i, strat in enumerate(strategies):
        status_placeholder.info(f"Executing strategy {i+1}/{len(strategies)} in sandbox...")
        result = agent.execute_strategy(strat.get("code", ""), raw)
        results.append({"strategy": strat, "result": result})
        progress.progress((i + 1) / max(len(strategies), 1))

    status_placeholder.empty()

    # Metrics dashboard
    st.subheader("Metrics Dashboard")
    metrics = []
    for r in results:
        res = r["result"]
        metrics.append({
            "Strategy": r["strategy"].get("name"),
            "Success": res.success,
            "Duration (s)": res.duration_sec,
            "Contained": res.timed_out or res.killed_by_limit,
            "Return code": res.returncode,
        })
    st.dataframe(pd.DataFrame(metrics), use_container_width=True)

    st.subheader("Detailed Results")
    for r in results:
        res = r["result"]
        name = r["strategy"].get("name", "Strategy")
        if res.success:
            st.success(f"{name} — Success ({res.duration_sec}s)")
        elif res.timed_out or res.killed_by_limit:
            st.error(f"{name} — Contained by sandbox ({res.duration_sec}s)")
        else:
            st.warning(f"{name} — Failed ({res.duration_sec}s)")

        if res.stdout:
            with st.expander("Output"):
                st.code(res.stdout[:1500])
        if res.stderr:
            with st.expander("Errors / Containment log"):
                st.code(res.stderr[:800])

    best = agent.select_best(results)
    if best:
        st.success(f"Selected best strategy: **{best['strategy'].get('name')}**")
        st.metric("Best duration", f"{best['result'].duration_sec}s")
