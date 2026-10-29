"""
Streamlit UI for the Self-Healing Data Pipeline.
Deploy this on a Vultr VM.
"""

import streamlit as st
import pandas as pd
from io import StringIO
from agent import DataPipelineAgent

st.set_page_config(page_title="Self-Healing Data Pipeline", layout="wide")
st.title("Self-Healing + Cost-Aware Data Pipeline")
st.caption("Vultr Agent Rush — Blast Radius Zero | Sandboxed multi-strategy cleaning")

uploaded = st.file_uploader("Upload messy CSV", type=["csv"])
goal = st.text_input("Cleaning goal", value="Remove duplicates, fix data types, drop empty rows, and make columns analysis-ready")

if st.button("Run Pipeline", type="primary") and uploaded is not None:
    raw = uploaded.getvalue().decode("utf-8")
    sample = "\n".join(raw.splitlines()[:8])

    agent = DataPipelineAgent()

    with st.spinner("Proposing strategies..."):
        strategies = agent.propose_strategies(sample, goal)

    st.subheader("Proposed Strategies")
    for s in strategies:
        with st.expander(s.get("name", "Strategy")):
            st.write(s.get("description", ""))
            st.code(s.get("code", ""), language="python")

    results = []
    progress = st.progress(0)
    for i, strat in enumerate(strategies):
        with st.spinner(f"Executing strategy {i+1} in sandbox..."):
            result = agent.execute_strategy(strat.get("code", ""), raw)
            results.append({"strategy": strat, "result": result})
        progress.progress((i + 1) / len(strategies))

    st.subheader("Execution Results")
    for r in results:
        res = r["result"]
        status = "✅ Success" if res.success else "❌ Failed / Contained"
        st.write(f"**{r['strategy'].get('name')}** — {status} ({res.duration_sec}s)")
        if res.timed_out or res.killed_by_limit:
            st.error("Containment triggered: sandbox killed the process (blast radius = zero)")
        if res.stdout:
            st.code(res.stdout[:1000])
        if res.stderr:
            st.code(res.stderr[:500])

    best = agent.select_best(results)
    if best:
        st.success(f"Best strategy selected: {best['strategy'].get('name')}")
        st.json({
            "duration": best["result"].duration_sec,
            "success": best["result"].success,
            "contained": best["result"].killed_by_limit or best["result"].timed_out,
        })
