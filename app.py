"""Streamlit UI for the self-healing data pipeline."""

import os

import pandas as pd
import streamlit as st

from agent import DataPipelineAgent
from sandbox_runner import SandboxRunner

SAMPLE_PATH = os.path.join(os.path.dirname(__file__), "data", "messy_orders.csv")

st.set_page_config(page_title="Self-Healing Data Pipeline", layout="wide")
st.title("Self-Healing + Cost-Aware Data Pipeline")
st.caption("Vultr Agent Rush — Blast Radius Zero. Failed strategies are repaired from real sandbox errors, then re-ranked by cost.")

with st.sidebar:
    st.header("Sandbox limits")
    memory = st.selectbox("Memory limit", ["128m", "256m", "512m"], index=1)
    timeout = st.slider("Timeout (seconds)", 5, 30, 12)
    st.caption("Cost = seconds × (memory / 256MB). Failures are penalized. Lower cost wins.")

if "csv_text" not in st.session_state:
    st.session_state.csv_text = ""

col_a, col_b = st.columns(2)
if col_a.button("Load sample dataset", use_container_width=True):
    with open(SAMPLE_PATH, encoding="utf-8") as handle:
        st.session_state.csv_text = handle.read()
uploaded = col_b.file_uploader("Or upload a CSV", type=["csv"])
if uploaded is not None:
    st.session_state.csv_text = uploaded.getvalue().decode("utf-8", errors="replace")

goal = st.text_area(
    "Cleaning goal",
    value="Drop duplicate orders, remove empty rows, strip names, coerce amount to numeric, and normalize status and dates.",
    height=70,
)

raw = st.session_state.csv_text
if raw:
    st.subheader("Input preview")
    st.dataframe(pd.read_csv(pd.io.common.StringIO(raw)), use_container_width=True)

run_col, contain_col = st.columns(2)
run_pipeline = run_col.button("Run pipeline", type="primary", use_container_width=True)
run_containment = contain_col.button("Force containment demo", use_container_width=True)

if run_containment:
    st.subheader("Containment demo")
    runner = SandboxRunner(memory_limit=memory, timeout_sec=8)
    result = runner.run("import time\nprint('loop started')\nwhile True:\n    time.sleep(0.1)\n")
    if result.timed_out or result.killed_by_limit:
        st.success("Blast radius = zero. The sandbox killed the infinite loop.")
    else:
        st.warning("Containment did not trigger. Is Docker running?")
    st.json({
        "timed_out": result.timed_out,
        "killed_by_limit": result.killed_by_limit,
        "duration_sec": result.duration_sec,
        "stderr": result.stderr[:400],
    })

if run_pipeline:
    if not raw:
        st.error("Load the sample dataset or upload a CSV first.")
    elif not os.getenv("VULTR_INFERENCE_API_KEY"):
        st.error("Set VULTR_INFERENCE_API_KEY before running the pipeline.")
    else:
        sample = "\n".join(raw.splitlines()[:12])
        agent = DataPipelineAgent()
        agent.sandbox.memory_limit = memory
        agent.sandbox.timeout_sec = timeout

        with st.spinner("Proposing strategies..."):
            strategies = agent.propose_strategies(sample, goal)

        st.subheader("Proposed strategies")
        for strat in strategies:
            with st.expander(strat["name"]):
                st.write(strat["description"])
                st.code(strat["code"], language="python")

        with st.spinner("Executing in sandboxes and healing failures..."):
            attempts = agent.run_with_healing(strategies, raw, goal)

        ranked = agent.rank(attempts)
        st.subheader("Cost ranking")
        st.dataframe(pd.DataFrame([
            {
                "Rank": i + 1,
                "Strategy": item["strategy"]["name"],
                "Round": item["round"],
                "Success": item["result"].success,
                "Duration (s)": item["result"].duration_sec,
                "Memory": item["memory_limit"],
                "Contained": bool(item["result"].timed_out or item["result"].killed_by_limit),
                "Cost": item["cost"],
            }
            for i, item in enumerate(ranked)
        ]), use_container_width=True)

        st.subheader("Attempts")
        for item in attempts:
            res = item["result"]
            label = f"{item['strategy']['name']} — round {item['round']} — cost {item['cost']}"
            if res.success and not res.timed_out:
                st.success(label)
            elif res.timed_out or res.killed_by_limit:
                st.error(label + " — contained")
            else:
                st.warning(label + " — failed, error sent to healer" if item["round"] == 1 else label)
            if item["round"] == 2:
                st.caption(f"Healed from {item['parent']} using the sandbox stderr.")
                st.code(item["code"], language="python")
            if res.stdout:
                with st.expander(f"Output — {item['strategy']['name']}"):
                    st.code(res.stdout[:1500])
            if res.stderr:
                with st.expander(f"Stderr — {item['strategy']['name']}"):
                    st.code(res.stderr[:800])

        best = agent.select_best(attempts)
        if best:
            st.subheader("Recommendation")
            st.success(
                f"Use {best['strategy']['name']} (round {best['round']}). "
                f"Cost {best['cost']} at {best['memory_limit']}, {best['result'].duration_sec}s."
            )
