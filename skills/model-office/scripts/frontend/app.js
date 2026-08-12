// Model Office - blocky Lego/Minecraft-style pixel canvas engine
const canvas = document.getElementById("office");
const ctx = canvas.getContext("2d");
ctx.imageSmoothingEnabled = false;

const WORKERS = {
  claude: { name: "Claude", sprite: "sprites/claude.png", x: 160, color: "#ff9f6b" },
  gpt:    { name: "GPT",    sprite: "sprites/gpt.png",    x: 450, color: "#7fe6b0" },
  sonar:  { name: "Sonar",  sprite: "sprites/sonar.png",  x: 740, color: "#8fb8ff" },
};

// Two zones: upper WORK area (desks, active job) and lower WAIT area (lounge, idle/done)
const ZONE_DIVIDER_Y = 300;
const WORK_Y = 175;   // avatar anchor y while working
const WAIT_Y = 430;   // avatar anchor y while idle/waiting
const QUEUE_Y = 60;

// load sprites
for (const w of Object.values(WORKERS)) {
  const img = new Image();
  img.src = w.sprite;
  w.img = img;
  w.status = "idle";      // idle | queued | thinking | done | error
  w.text = "";
  w.y = WAIT_Y;           // current animated y position
  w.bobPhase = Math.random() * Math.PI * 2;
}

function targetYFor(status) {
  return status === "thinking" ? WORK_Y : WAIT_Y;
}

// jobs currently visible as tickets (in queue or flying to a desk)
let jobs = {}; // job_id -> {title, worker, x, y, targetX, targetY, state}

function addLog(html) {
  const log = document.getElementById("log");
  const div = document.createElement("div");
  div.className = "logLine";
  div.innerHTML = html;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
}

function tagClass(workerId) {
  return "tag tag-" + workerId;
}

function resetAll() {
  jobs = {};
  for (const w of Object.values(WORKERS)) {
    w.status = "idle";
    w.text = "";
    w.y = WAIT_Y;
  }
  document.getElementById("log").innerHTML = "";
}

function handleEvent(evt) {
  switch (evt.type) {
    case "reset":
      resetAll();
      break;
    case "taskReceived":
      addLog(`<span class="tag">[TASK]</span> ${evt.payload.task}`);
      break;
    case "jobCreated": {
      const w = WORKERS[evt.payload.worker];
      jobs[evt.job_id] = {
        title: evt.payload.title,
        worker: evt.payload.worker,
        x: 60 + Object.keys(jobs).length * 90,
        y: QUEUE_Y,
        targetX: w ? w.x : 60,
        targetY: WORK_Y,
        state: "queue",
      };
      addLog(`<span class="${tagClass(evt.payload.worker)}">[QUEUED]</span> ${evt.payload.title} &rarr; ${WORKERS[evt.payload.worker]?.name || evt.payload.worker}`);
      break;
    }
    case "jobAssigned": {
      addLog(`<span class="${tagClass(evt.worker_id)}">[ASSIGNED]</span> ${evt.payload.title} <i>(${evt.payload.reason})</i>`);
      const job = jobs[evt.job_id];
      if (job) job.state = "flying";
      break;
    }
    case "workerStatus": {
      const w = WORKERS[evt.worker_id];
      if (w) {
        w.status = evt.payload.status;
        w.text = evt.payload.text || "";
      }
      const job = jobs[evt.job_id];
      if (job && evt.payload.status === "thinking") job.state = "at_desk";
      if (evt.payload.status !== "queued") {
        addLog(`<span class="${tagClass(evt.worker_id)}">[${evt.payload.status.toUpperCase()}]</span> ${WORKERS[evt.worker_id]?.name || evt.worker_id} ${evt.payload.text}`);
      }
      break;
    }
    case "jobDone": {
      const job = jobs[evt.job_id];
      if (job) job.state = "done";
      const preview = (evt.payload.result || "").slice(0, 220).replace(/</g, "&lt;");
      addLog(`<span class="${tagClass(evt.worker_id)}">[RESULT]</span> ${preview}${evt.payload.result.length > 220 ? "..." : ""}`);
      setTimeout(() => { delete jobs[evt.job_id]; }, 2500);
      if (WORKERS[evt.worker_id]) {
        setTimeout(() => {
          if (WORKERS[evt.worker_id].status === "done") {
            WORKERS[evt.worker_id].status = "idle";
            WORKERS[evt.worker_id].text = "";
          }
        }, 3000);
      }
      break;
    }
  }
}

// ---- WebSocket ----
function connectWS() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${location.host}/ws`);
  ws.onmessage = (msg) => {
    try { handleEvent(JSON.parse(msg.data)); } catch (e) { console.error(e); }
  };
  ws.onclose = () => setTimeout(connectWS, 1000);
}
connectWS();

// ---- Task submission ----
const taskInput = document.getElementById("taskInput");
const taskBtn = document.getElementById("taskBtn");

async function submitTask() {
  const task = taskInput.value.trim();
  if (!task) return;
  taskBtn.disabled = true;
  taskBtn.textContent = "Working...";
  try {
    await fetch("/api/task", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ task }),
    });
  } finally {
    setTimeout(() => {
      taskBtn.disabled = false;
      taskBtn.textContent = "Dispatch";
    }, 2000);
  }
}
taskBtn.addEventListener("click", submitTask);
taskInput.addEventListener("keydown", (e) => { if (e.key === "Enter") submitTask(); });

// ---- Render loop ----
const STATUS_COLORS = {
  idle: "#8a8a8a",
  queued: "#ffd500",
  thinking: "#ff4136",
  done: "#2ecc71",
  error: "#ff0000",
};

// ---- Lego-brick helpers ----
function legoBrick(x, y, w, h, color, studRows = 1, studCols) {
  // base brick body with thick black outline (Lego/blocky look)
  ctx.fillStyle = color;
  ctx.fillRect(x, y, w, h);
  ctx.strokeStyle = "#000";
  ctx.lineWidth = 3;
  ctx.strokeRect(x, y, w, h);
  // studs on top
  const cols = studCols || Math.max(2, Math.round(w / 22));
  const studR = Math.min(6, w / (cols * 3));
  const spacingX = w / cols;
  for (let r = 0; r < studRows; r++) {
    for (let c = 0; c < cols; c++) {
      const cx = x + spacingX * (c + 0.5);
      const cy = y - studR + r * (studR * 1.2);
      ctx.beginPath();
      ctx.arc(cx, cy, studR, 0, Math.PI * 2);
      ctx.fillStyle = shade(color, -10);
      ctx.fill();
      ctx.strokeStyle = "#000";
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }
  }
}

function shade(hex, percent) {
  const n = parseInt(hex.slice(1), 16);
  let r = (n >> 16) + percent, g = ((n >> 8) & 0xff) + percent, b = (n & 0xff) + percent;
  r = Math.max(0, Math.min(255, r));
  g = Math.max(0, Math.min(255, g));
  b = Math.max(0, Math.min(255, b));
  return `rgb(${r},${g},${b})`;
}

function drawDesk(w) {
  // blocky lego "computer desk" in the WORK zone
  legoBrick(w.x - 55, WORK_Y + 55, 110, 24, "#5a4632", 1, 5); // desk top
  ctx.fillStyle = "#3a2a1a";
  ctx.fillRect(w.x - 45, WORK_Y + 79, 14, 34);
  ctx.fillRect(w.x + 31, WORK_Y + 79, 14, 34);
  ctx.strokeStyle = "#000";
  ctx.lineWidth = 2;
  ctx.strokeRect(w.x - 45, WORK_Y + 79, 14, 34);
  ctx.strokeRect(w.x + 31, WORK_Y + 79, 14, 34);
  // little monitor block
  legoBrick(w.x - 16, WORK_Y + 30, 32, 24, "#2c2c2c", 0);
  ctx.fillStyle = "#6be0ff";
  ctx.fillRect(w.x - 12, WORK_Y + 34, 24, 16);
}

function drawBench(w) {
  // blocky lego "lounge bench" in the WAIT zone
  legoBrick(w.x - 55, WAIT_Y + 55, 110, 20, "#8a5cf6", 1, 5);
  ctx.fillStyle = "#5a3ac2";
  ctx.fillRect(w.x - 45, WAIT_Y + 75, 12, 20);
  ctx.fillRect(w.x + 33, WAIT_Y + 75, 12, 20);
  ctx.strokeStyle = "#000";
  ctx.lineWidth = 2;
  ctx.strokeRect(w.x - 45, WAIT_Y + 75, 12, 20);
  ctx.strokeRect(w.x + 33, WAIT_Y + 75, 12, 20);
}

function drawAvatar(w, t) {
  // smoothly move between WORK_Y and WAIT_Y based on status
  w.targetY = targetYFor(w.status);
  w.y += (w.targetY - w.y) * 0.06;

  const inWork = w.y < ZONE_DIVIDER_Y;
  const bob = Math.sin(t / 300 + w.bobPhase) * (w.status === "thinking" ? 5 : 2);
  const y = w.y + bob;

  if (inWork) drawDesk(w); else drawBench(w);

  if (w.img.complete && w.img.naturalWidth > 0) {
    ctx.drawImage(w.img, w.x - 48, y - 90, 96, 96);
  } else {
    ctx.fillStyle = w.color;
    ctx.fillRect(w.x - 40, y - 80, 80, 80);
  }

  // status light (lego stud-like badge)
  ctx.beginPath();
  ctx.arc(w.x + 45, y - 85, 7, 0, Math.PI * 2);
  ctx.fillStyle = STATUS_COLORS[w.status] || "#8a8a8a";
  ctx.fill();
  ctx.strokeStyle = "#000";
  ctx.lineWidth = 2;
  ctx.stroke();
  if (w.status === "thinking") {
    ctx.beginPath();
    ctx.arc(w.x + 45, y - 85, 7 + 4 * Math.abs(Math.sin(t / 200)), 0, Math.PI * 2);
    ctx.strokeStyle = STATUS_COLORS.thinking;
    ctx.stroke();
  }

  // name plate (blocky tag)
  ctx.font = "bold 13px monospace";
  ctx.fillStyle = "#000";
  ctx.textAlign = "center";
  ctx.fillText(w.name, w.x, y + 22);
  ctx.font = "10px monospace";
  ctx.fillStyle = "#333";
  ctx.fillText(w.status.toUpperCase(), w.x, y + 36);

  // speech bubble
  if (w.text && (w.status === "thinking" || w.status === "done" || w.status === "error")) {
    const label = w.text.length > 34 ? w.text.slice(0, 34) + "..." : w.text;
    ctx.font = "10px monospace";
    const width = Math.max(60, ctx.measureText(label).width + 16);
    const bx = w.x - width / 2;
    const by = y - 128;
    ctx.fillStyle = "#fff";
    ctx.strokeStyle = "#000";
    ctx.lineWidth = 2;
    roundRect(ctx, bx, by, width, 24, 4);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = "#222";
    ctx.textAlign = "center";
    ctx.fillText(label, w.x, by + 16);
  }
}

function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

function drawJobTicket(job) {
  if (job.state === "flying" || job.state === "queue") {
    if (job.state === "flying") {
      job.x += (job.targetX - job.x) * 0.08;
      job.y += (job.targetY - 40 - job.y) * 0.08;
    }
    ctx.fillStyle = "#ffd500";
    ctx.strokeStyle = "#000";
    ctx.lineWidth = 2;
    roundRect(ctx, job.x - 35, job.y - 12, 70, 24, 3);
    ctx.fill();
    ctx.stroke();
    ctx.font = "9px monospace";
    ctx.fillStyle = "#3a2a00";
    ctx.textAlign = "center";
    const label = job.title.length > 16 ? job.title.slice(0, 16) + "..." : job.title;
    ctx.fillText(label, job.x, job.y + 3);
  }
}

// ---- Office background: blocky Lego/Minecraft style, two zones ----
function drawFloor() {
  const tile = 40;

  // WORK zone (top): grey "office floor" lego baseplate tiles
  ctx.fillStyle = "#c9c9c9";
  ctx.fillRect(0, 0, canvas.width, ZONE_DIVIDER_Y);
  for (let x = 0; x < canvas.width; x += tile) {
    for (let y = 0; y < ZONE_DIVIDER_Y; y += tile) {
      ctx.strokeStyle = "#a8a8a8";
      ctx.lineWidth = 1;
      ctx.strokeRect(x, y, tile, tile);
      ctx.beginPath();
      ctx.arc(x + tile / 2, y + tile / 2, 3, 0, Math.PI * 2);
      ctx.fillStyle = "#b8b8b8";
      ctx.fill();
    }
  }

  // WAIT zone (bottom): green "grass baseplate" lego/minecraft tiles
  ctx.fillStyle = "#4caf50";
  ctx.fillRect(0, ZONE_DIVIDER_Y, canvas.width, canvas.height - ZONE_DIVIDER_Y);
  for (let x = 0; x < canvas.width; x += tile) {
    for (let y = ZONE_DIVIDER_Y; y < canvas.height; y += tile) {
      ctx.strokeStyle = "#3d8b40";
      ctx.lineWidth = 1;
      ctx.strokeRect(x, y, tile, tile);
      ctx.beginPath();
      ctx.arc(x + tile / 2, y + tile / 2, 3, 0, Math.PI * 2);
      ctx.fillStyle = "#5cbf60";
      ctx.fill();
    }
  }

  // zone divider wall (thick brick strip)
  legoBrick(0, ZONE_DIVIDER_Y - 14, canvas.width, 14, "#d64545", 1, Math.round(canvas.width / 24));

  // zone labels
  ctx.font = "bold 14px monospace";
  ctx.textAlign = "left";
  ctx.fillStyle = "#333";
  ctx.fillText("\u{1F527} WORKING AREA", 16, 24);
  ctx.fillStyle = "#fff";
  ctx.fillText("\u{1F6CB} WAITING AREA", 16, ZONE_DIVIDER_Y + 24);
}

function frame(t) {
  drawFloor();
  for (const w of Object.values(WORKERS)) drawAvatar(w, t);
  for (const job of Object.values(jobs)) drawJobTicket(job);
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);
