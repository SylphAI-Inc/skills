# Model Office

Visualize multi-model job routing as a live, blocky Lego/Minecraft-style
pixel office in your browser. Type one task, watch it get decomposed and
routed to whichever model (Claude / GPT / Sonar) best fits each subtask,
and see worker avatars slide between a "working area" desk and a "waiting
area" lounge as their status changes — inspired by
[pixel-agents](https://github.com/pixel-agents-hq/pixel-agents), built for
capability-based multi-model routing.

See [SKILL.md](./SKILL.md) for full details, architecture, and setup.

## Quickstart

```bash
cd scripts
pip install -q -r requirements.txt
python3 run.py "Plan a product launch, write the announcement, and research competitor pricing"
```

Opens `http://127.0.0.1:8787` — a dashboard where you can also type new
tasks directly into the Dispatch box.
