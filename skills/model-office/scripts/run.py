"""
Orchestrator: starts the FastAPI server (if not running), opens the browser
to the pixel office, then dispatches the user's task and runs all workers.

Usage:
    python run.py "your task here"
"""
import asyncio
import subprocess
import sys
import time
import webbrowser

import httpx

SERVER = "http://127.0.0.1:8787"


def server_is_up() -> bool:
    try:
        httpx.get(SERVER, timeout=1)
        return True
    except Exception:
        return False


def start_server():
    print("[run] starting server...")
    subprocess.Popen(
        [sys.executable, "server.py"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(30):
        if server_is_up():
            return
        time.sleep(0.3)
    raise RuntimeError("server failed to start")


async def main():
    task = sys.argv[1] if len(sys.argv) > 1 else input("Enter a task: ")

    if not server_is_up():
        start_server()
    else:
        print("[run] server already running")

    webbrowser.open(SERVER)
    time.sleep(1.0)  # give the browser a moment to connect the websocket

    from dispatcher import dispatch
    from worker import run_all

    print(f"[run] dispatching task: {task}")
    subtasks = dispatch(task)
    print(f"[run] {len(subtasks)} subtasks assigned:")
    for s in subtasks:
        print(f"  - [{s['worker']}] {s['title']}")

    results = await run_all(subtasks)
    print("\n[run] all jobs complete:\n")
    for r in results:
        if "error" in r:
            print(f"=== {r['worker']} ({r['job_id']}) ERROR: {r['error']} ===\n")
        else:
            print(f"=== {r['worker']} ({r['job_id']}, {r['elapsed']}s) ===")
            print(r["result"])
            print()


if __name__ == "__main__":
    asyncio.run(main())
