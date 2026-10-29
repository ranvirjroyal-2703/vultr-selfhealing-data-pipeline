"""
Self-Healing + Cost-Aware Data Pipeline Agent
Uses Vultr Serverless Inference for planning and strategy generation.
"""

import os
import json
from typing import List, Dict, Any
from openai import OpenAI
from sandbox_runner import SandboxRunner, SandboxResult


class DataPipelineAgent:
    def __init__(self):
        self.client = OpenAI(
            base_url="https://api.vultrinference.com/v1",
            api_key=os.getenv("VULTR_INFERENCE_API_KEY"),
        )
        self.sandbox = SandboxRunner(memory_limit="256m", cpu_limit="0.5", timeout_sec=12)

    def _call_llm(self, system: str, user: str, model: str = "llama-3.1-70b-instruct") -> str:
        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
            max_tokens=2000,
        )
        return response.choices[0].message.content.strip()

    def propose_strategies(self, data_sample: str, goal: str) -> List[Dict[str, str]]:
        """Ask the model for multiple distinct cleaning strategies."""
        system = (
            "You are an expert data engineer. Propose 3 different Python strategies "
            "to clean the given data according to the goal. Each strategy must be "
            "complete, runnable code that reads from a pandas DataFrame named `df` "
            "and writes the result back to `df`. Return valid JSON only."
        )
        user = f"Goal: {goal}\n\nData sample:\n{data_sample}\n\nReturn JSON array of objects with keys: name, description, code"
        raw = self._call_llm(system, user)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return [{"name": "fallback", "description": "basic clean", "code": "print(df.head())"}]

    def execute_strategy(self, code: str, data_csv: str) -> SandboxResult:
        """Wrap strategy code with data loading and run it in the sandbox."""
        full_code = f'''
import pandas as pd
from io import StringIO

data = """{data_csv}"""
df = pd.read_csv(StringIO(data))

{code}

print("ROWS:", len(df))
print("COLUMNS:", list(df.columns))
print(df.head(3).to_csv(index=False))
'''
        return self.sandbox.run(full_code)

    def select_best(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Pick the best strategy based on success, speed, and cleanliness."""
        successful = [r for r in results if r["result"].success]
        if not successful:
            return results[0] if results else {}
        # Prefer fastest successful run
        return min(successful, key=lambda r: r["result"].duration_sec)
