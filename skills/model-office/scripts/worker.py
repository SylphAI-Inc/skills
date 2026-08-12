"""
Worker: executes one subtask against its assigned real model, emitting
status events (queued -> thinking -> tool_call -> done/error) so the
browser can animate the corresponding pixel avatar in real time.
"""
import asyncio
import os
import time

import httpx
from anthropic import Anthropic
from openai import OpenAI

SERVER = "http://127.0.0.1:8787"

_anthropic = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
_openai = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
_perplexity_key = os.environ.get("PERPLEXITY_API_KEY", "")


async def post_event(event: dict):
    async with httpx.AsyncClient(timeout=5) as client:
        try:
            await client.post(f"{SERVER}/api/events", json=event)
        except Exception as e:
            print(f"[worker] warn: failed to post event: {e}")


async def _status(job_id: str, worker_id: str, status: str, text: str = ""):
    await post_event({
        "type": "workerStatus",
        "job_id": job_id,
        "worker_id": worker_id,
        "payload": {"status": status, "text": text},
    })


def _call_claude(prompt: str) -> str:
    resp = _anthropic.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text.strip()


def _call_gpt(prompt: str) -> str:
    resp = _openai.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content.strip()


def _call_sonar(prompt: str) -> str:
    resp = httpx.post(
        "https://api.perplexity.ai/chat/completions",
        headers={"Authorization": f"Bearer {_perplexity_key}"},
        json={
            "model": "sonar",
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


_CALLERS = {"claude": _call_claude, "gpt": _call_gpt, "sonar": _call_sonar}


async def run_subtask(subtask: dict) -> dict:
    job_id = subtask["job_id"]
    worker_id = subtask["worker"]
    prompt = subtask["prompt"]

    await _status(job_id, worker_id, "queued")
    await asyncio.sleep(0.4)  # let the browser show the ticket move to desk
    await _status(job_id, worker_id, "thinking", "working on: " + subtask["title"])

    caller = _CALLERS.get(worker_id)
    start = time.time()
    try:
        result = await asyncio.to_thread(caller, prompt)
        elapsed = round(time.time() - start, 1)
        await _status(job_id, worker_id, "done", f"done in {elapsed}s")
        await post_event({
            "type": "jobDone",
            "job_id": job_id,
            "worker_id": worker_id,
            "payload": {"result": result, "elapsed": elapsed},
        })
        return {"job_id": job_id, "worker": worker_id, "result": result, "elapsed": elapsed}
    except Exception as e:
        await _status(job_id, worker_id, "error", str(e))
        return {"job_id": job_id, "worker": worker_id, "error": str(e)}


async def run_all(subtasks: list[dict]) -> list[dict]:
    """Run subtasks concurrently -- different workers can work at once,
    mirroring the pixel-office idea of multiple avatars busy simultaneously."""
    return await asyncio.gather(*(run_subtask(s) for s in subtasks))
