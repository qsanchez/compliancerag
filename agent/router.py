from pathlib import Path
from typing import Literal

import litellm
from langsmith import traceable

from config import get_settings

_PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load_prompt(name: str) -> str:
    return (_PROMPTS_DIR / name).read_text(encoding="utf-8")


@traceable(name="router", run_type="chain")
def classify(question: str) -> Literal["rag", "analytics"]:
    settings = get_settings()
    response = litellm.completion(
        model=settings.litellm_model,
        messages=[
            {"role": "system", "content": _load_prompt("router_system.txt")},
            {"role": "user", "content": question},
        ],
        max_tokens=5,
        temperature=0.0,
    )
    raw = (response.choices[0].message.content or "").strip().lower()
    return "analytics" if "analytics" in raw else "rag"
