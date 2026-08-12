"""
Dispatcher: decomposes a user task into subtasks and assigns each to the
best-fit "worker" based on capability, then emits events to the server
so the browser can visualize job flow before workers even start executing.

Workers (capability-based routing):
  - claude   -> Anthropic Claude: code, reasoning, structured analysis
  - gpt      -> OpenAI GPT: writing, creative, general summarization
  - sonar    -> Perplexity Sonar: research / fact-finding (native web search)
"""
import json
import os
import uuid

import httpx
from anthropic import Anthropic

SERVER = "http://127.0.0.1:8787"

WORKER_CAPABILITIES = {
    "claude": "Code generation, debugging, structured reasoning, step-by-step analysis, planning.",
    "gpt": "Creative writing, summarization, general Q&A, tone/style-sensitive text.",
    "sonar": "Research requiring up-to-date facts, citations, or web lookups.",
}

DECOMPOSE_SYSTEM = """You are a task router for a multi-model office.
Break the user's task into 2-4 concrete subtasks. For EACH subtask, assign the
single best worker id from this capability table:

claude: {claude}
gpt: {gpt}
sonar: {sonar}

Return ONLY valid JSON, no prose, in this exact shape:
{{"subtasks": [{{"title": "short title", "worker": "claude|gpt|sonar", "prompt": "full instructions for that worker", "reason": "one line why this worker fits"}}]}}
""".format(**WORKER_CAPABILITIES)


def post_event(event: dict):
    try:
        httpx.post(f"{SERVER}/api/events", json=event, timeout=5)
    except Exception as e:
        print(f"[dispatcher] warn: failed to post event: {e}")


def decompose(task: str) -> list[dict]:
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    resp = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        system=DECOMPOSE_SYSTEM,
        messages=[{"role": "user", "content": task}],
    )
    text = resp.content[0].text.strip()
    # strip potential markdown fences
    if text.startswith("```"):
        text = text.strip("`")
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.endswith("json"):
            text = text[:-4]
    data = json.loads(text)
    subtasks = data["subtasks"]
    for s in subtasks:
        s["job_id"] = str(uuid.uuid4())[:8]
    return subtasks


def dispatch(task: str) -> list[dict]:
    post_event({"type": "reset", "payload": {}})
    post_event({"type": "taskReceived", "payload": {"task": task}})
    subtasks = decompose(task)
    for s in subtasks:
        post_event({
            "type": "jobCreated",
            "job_id": s["job_id"],
            "payload": {"title": s["title"], "worker": s["worker"]},
        })
    for s in subtasks:
        post_event({
            "type": "jobAssigned",
            "job_id": s["job_id"],
            "worker_id": s["worker"],
            "payload": {"title": s["title"], "reason": s["reason"]},
        })
    return subtasks


if __name__ == "__main__":
    import sys

    task = sys.argv[1] if len(sys.argv) > 1 else "Plan a 3-day trip to Tokyo, write a fun blog intro, and research current visa rules for US citizens."
    result = dispatch(task)
    print(json.dumps(result, indent=2))
