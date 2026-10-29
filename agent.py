"""Self-healing, cost-aware data cleaning agent."""

import base64
import json
import os
import re
from typing import Any

from openai import OpenAI

from sandbox_runner import SandboxResult, SandboxRunner
from scoring import run_cost


class DataPipelineAgent:
    def __init__(self) -> None:
        self.client = OpenAI(
            base_url=os.getenv("VULTR_INFERENCE_BASE_URL", "https://api.vultrinference.com/v1"),
            api_key=os.getenv("VULTR_INFERENCE_API_KEY"),
        )
        self.model = os.getenv("VULTR_INFERENCE_MODEL", "llama-3.1-70b-instruct")
        self.sandbox = SandboxRunner()

    def _call_llm(self, system: str, user: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
            max_tokens=2200,
        )
        return response.choices[0].message.content.strip()

    def _extract_json(self, text: str) -> Any:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass
        for start_char, end_char in (("[", "]"), ("{", "}")):
            start = text.find(start_char)
            end = text.rfind(end_char)
            if start != -1 and end > start:
                try:
                    return json.loads(text[start : end + 1])
                except json.JSONDecodeError:
                    continue
        return []

    def propose_strategies(self, data_sample: str, goal: str) -> list[dict[str, str]]:
        system = (
            "You are an expert data engineer. Propose exactly 3 distinct pandas strategies. "
            "Each must be complete code that assumes a DataFrame named df already exists "
            "and reassigns df. Do not import os, subprocess, or open files. "
            "Return ONLY a JSON array of objects with keys name, description, code."
        )
        raw = self._call_llm(system, f"Goal: {goal}\n\nData sample:\n{data_sample}")
        strategies = self._extract_json(raw)
        if not isinstance(strategies, list) or not strategies:
            strategies = [{
                "name": "basic_clean",
                "description": "Drop duplicates and fully empty rows",
                "code": "df = df.drop_duplicates().dropna(how='all')",
            }]
        cleaned = []
        for item in strategies[:3]:
            if isinstance(item, dict) and item.get("code"):
                cleaned.append({
                    "name": str(item.get("name") or "strategy"),
                    "description": str(item.get("description") or ""),
                    "code": str(item["code"]),
                })
        return cleaned or strategies[:1]

    def heal(self, code: str, error: str, goal: str) -> str:
        """Repair code using the real sandbox error. Returns code only."""
        system = (
            "You repair pandas cleaning code. The DataFrame is named df. "
            "Return ONLY the repaired Python code. No markdown, no explanation. "
            "Do not import os or subprocess."
        )
        user = f"Goal: {goal}\n\nFailed code:\n{code}\n\nSandbox error:\n{error[:1200]}"
        repaired = self._call_llm(system, user)
        repaired = re.sub(r"^```(?:python)?\s*", "", repaired)
        repaired = re.sub(r"\s*```$", "", repaired)
        return repaired.strip()

    def execute_strategy(self, code: str, data_csv: str) -> SandboxResult:
        payload = base64.b64encode(data_csv.encode("utf-8")).decode("ascii")
        full_code = f'''
import base64
import pandas as pd
from io import StringIO

raw = base64.b64decode("{payload}").decode("utf-8")
df = pd.read_csv(StringIO(raw))

{code}

print("ROWS:", len(df))
print("COLUMNS:", list(df.columns))
print("---CLEANED---")
print(df.head(8).to_csv(index=False))
'''
        return self.sandbox.run(full_code)

    def run_with_healing(self, strategies: list[dict[str, str]], data_csv: str, goal: str) -> list[dict[str, Any]]:
        """Run each strategy. On failure, repair once from the real stderr and rerun."""
        attempts: list[dict[str, Any]] = []
        memory_limit = self.sandbox.memory_limit
        for strat in strategies:
            code = strat["code"]
            first = self.execute_strategy(code, data_csv)
            attempts.append(self._pack(strat, code, first, round_n=1, memory_limit=memory_limit))
            if first.success and not first.timed_out:
                continue
            error = first.stderr or first.stdout or "unknown failure"
            repaired = self.heal(code, error, goal)
            if not repaired or repaired == code:
                continue
            second = self.execute_strategy(repaired, data_csv)
            attempts.append(self._pack(
                {**strat, "name": strat["name"] + " (healed)"},
                repaired,
                second,
                round_n=2,
                memory_limit=memory_limit,
                parent=strat["name"],
            ))
        return attempts

    def _pack(self, strat, code, result, round_n, memory_limit, parent=None) -> dict[str, Any]:
        return {
            "strategy": strat,
            "code": code,
            "result": result,
            "round": round_n,
            "parent": parent,
            "memory_limit": memory_limit,
            "cost": run_cost(result, memory_limit),
        }

    def rank(self, attempts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return sorted(attempts, key=lambda a: (not a["result"].success, a["cost"], a["round"]))

    def select_best(self, attempts: list[dict[str, Any]]) -> dict[str, Any]:
        ranked = self.rank(attempts)
        winners = [a for a in ranked if a["result"].success and not a["result"].timed_out]
        return winners[0] if winners else (ranked[0] if ranked else {})
