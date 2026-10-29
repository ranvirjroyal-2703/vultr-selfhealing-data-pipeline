"""
Self-Healing + Cost-Aware Data Pipeline Agent
Improved strategy generation, robust JSON parsing, and parallel-ready execution.
"""

import os
import json
import re
from typing import List, Dict, Any
from openai import OpenAI
from sandbox_runner import SandboxRunner, SandboxResult


class DataPipelineAgent:
    def __init__(self):
        self.client = OpenAI(
            base_url=os.getenv("VULTR_INFERENCE_BASE_URL", "https://api.vultrinference.com/v1"),
            api_key=os.getenv("VULTR_INFERENCE_API_KEY"),
        )
        self.sandbox = SandboxRunner()

    def _call_llm(self, system: str, user: str, model: str = "llama-3.1-70b-instruct") -> str:
        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.3,
            max_tokens=2500,
        )
        return response.choices[0].message.content.strip()

    def _extract_json(self, text: str) -> Any:
        """Robust JSON extraction from LLM output."""
        # Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        # Extract from markdown code block
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass
        # Last resort: find first [ or {
        for start_char, end_char in [("[", "]"), ("{", "}")]:
            start = text.find(start_char)
            end = text.rfind(end_char)
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(text[start:end + 1])
                except json.JSONDecodeError:
                    continue
        return []

    def propose_strategies(self, data_sample: str, goal: str) -> List[Dict[str, str]]:
        system = """You are an expert data engineer specializing in robust data cleaning.
Propose exactly 3 distinct Python strategies to achieve the goal.
Each strategy must:
- Be complete runnable code
- Assume a pandas DataFrame named `df` already exists
- Modify `df` in place or reassign it
- Be safe and avoid infinite loops or destructive system calls

Return ONLY a JSON array of objects with keys: "name", "description", "code".
No other text."""
        user = f"Goal: {goal}\n\nData sample (first rows):\n{data_sample}"
        raw = self._call_llm(system, user)
        strategies = self._extract_json(raw)
        if not isinstance(strategies, list) or len(strategies) == 0:
            strategies = [{
                "name": "basic_clean",
                "description": "Drop duplicates and empty rows",
                "code": "df = df.drop_duplicates().dropna(how='all')"
            }]
        return strategies[:3]

    def execute_strategy(self, code: str, data_csv: str) -> SandboxResult:
        full_code = f'''
import pandas as pd
from io import StringIO

data = """{data_csv}"""
df = pd.read_csv(StringIO(data))

{code}

print("ROWS:", len(df))
print("COLUMNS:", list(df.columns))
print("---CLEANED---")
print(df.head(5).to_csv(index=False))
'''
        return self.sandbox.run(full_code)

    def select_best(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        successful = [r for r in results if r["result"].success and not r["result"].timed_out]
        if not successful:
            # Prefer least bad
            return min(results, key=lambda r: (not r["result"].success, r["result"].duration_sec)) if results else {}
        # Score: success first, then fastest, then lowest stderr length
        return min(
            successful,
            key=lambda r: (r["result"].duration_sec, len(r["result"].stderr))
        )
