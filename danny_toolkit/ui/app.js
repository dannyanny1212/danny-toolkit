/**
 * OMEGA Command Center — Sovereign UI Logic
 * Handles auth, telemetry polling, file ingest, and RAG chat.
 */

// ─── STATE ──────────────────────────────────────────
let API_KEY = localStorage.getItem("omega_api_key") || "";
const BASE = window.location.origin;
const POLL_INTERVAL = 5000;   // health poll: 5s
const JOB_POLL_MS   = 1000;  // job status poll: 1s

const activeJobs = new Map(); // job_id -> {status, bestand, chunks, el}
let healthTimer = null;

// ─── AUTH ───────────────────────────────────────────

async function authenticate() {
    const input = document.getElementById("api-key-input");
    const key = input.value.trim();
    if (!key) return;

    try {
        const resp = await fetch(`${BASE}/api/v1/health`, {
            headers: { "X-API-Key": key }
        });
        if (resp.ok) {
            API_KEY = key;
            localStorage.setItem("omega_api_key", key);
            document.getElementById("auth-gate").classList.add("hidden");
            document.getElementById("dashboard").classList.remove("hidden");
            startTelemetry();
        } else {
            showAuthError();
        }
    } catch {
        showAuthError();
    }
}

function showAuthError() {
    const err = document.getElementById("auth-error");
    err.classList.remove("hidden");
    setTimeout(() => err.classList.add("hidden"), 3000);
}

// Auto-auth if key is stored
window.addEventListener("DOMContentLoaded", () => {
    if (API_KEY) {
        authenticate_stored();
    }
});

async function authenticate_stored() {
    try {
        const resp = await fetch(`${BASE}/api/v1/health`, {
            headers: { "X-API-Key": API_KEY }
        });
        if (resp.ok) {
            document.getElementById("auth-gate").classList.add("hidden");
            document.getElementById("dashboard").classList.remove("hidden");
            startTelemetry();
        }
    } catch { /* show login */ }
}

// ─── WEBSOCKET TELEMETRIE (v6.19.0) ─────────────────
let ws = null;
let wsReconnectTimer = null;

function startWebSocket() {
    const wsUrl = `${BASE.replace("http", "ws")}/ws/events`;
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        console.log("[WS] Connected");
        const evtLog = document.getElementById("event-log");
        if (evtLog) {
            const el = document.createElement("div");
            el.className = "text-sovereign-green text-xs mb-1";
            el.textContent = `[${new Date().toLocaleTimeString()}] WebSocket LIVE`;
            evtLog.prepend(el);
        }
    };

    ws.onmessage = (evt) => {
        try {
            const data = JSON.parse(evt.data);
            if (data.type === "event") {
                appendEvent(data);
            }
        } catch { /* ignore parse errors */ }
    };

    ws.onclose = () => {
        console.log("[WS] Disconnected — reconnect in 5s");
        ws = null;
        wsReconnectTimer = setTimeout(startWebSocket, 5000);
    };

    ws.onerror = () => {
        console.log("[WS] Error — closing");
        ws?.close();
    };
}

function appendEvent(data) {
    const evtLog = document.getElementById("event-log");
    if (!evtLog) return;
    const el = document.createElement("div");
    el.className = "text-xs mb-1 border-l-2 border-sovereign-cyan pl-2";
    el.innerHTML = `<span class="text-sovereign-yellow">${data.timestamp}</span> `
        + `<span class="text-sovereign-cyan">${data.event_type}</span> `
        + `<span class="text-neutral-400">${data.bron}: ${data.summary.substring(0, 80)}</span>`;
    evtLog.prepend(el);
    // Hou log beheersbaar
    while (evtLog.children.length > 50) evtLog.removeChild(evtLog.lastChild);
}

// ─── TELEMETRY ──────────────────────────────────────

function startTelemetry() {
    pollHealth();
    healthTimer = setInterval(pollHealth, POLL_INTERVAL);
    startSynapseMonitor();
    startWebSocket();
}

async function pollHealth() {
    try {
        const resp = await apiFetch("/api/v1/health");
        if (!resp.ok) throw new Error("health failed");
        const data = await resp.json();
        updateServerStatus(data);
    } catch {
        setOffline();
    }

    // Parallel: fetch metrics, agents, db stats
    try {
        const [metricsResp, agentsResp] = await Promise.all([
            apiFetch("/api/v1/metrics").catch(() => null),
            apiFetch("/api/v1/agents").catch(() => null),
        ]);
        if (metricsResp?.ok) {
            const m = await metricsResp.json();
            updateMetrics(m);
        }
        if (agentsResp?.ok) {
            const agents = await agentsResp.json();
            updateAgents(agents);
        }
    } catch { /* non-critical */ }
}

function updateServerStatus(data) {
    const dot = document.getElementById("status-dot");
    const text = document.getElementById("status-text");
    dot.className = "w-2 h-2 rounded-full bg-sovereign-green status-pulse";
    text.textContent = "ONLINE";
    text.className = "text-sovereign-green text-sm";

    document.getElementById("sys-status").textContent = data.status?.toUpperCase() || "ONLINE";
    document.getElementById("sys-status").className = "text-sm font-bold text-sovereign-green";

    const uptime = data.uptime_seconds || 0;
    const h = Math.floor(uptime / 3600);
    const m = Math.floor((uptime % 3600) / 60);
    const s = Math.floor(uptime % 60);
    document.getElementById("sys-uptime").textContent = `${h}h ${m}m ${s}s`;
    document.getElementById("header-uptime").textContent = `uptime ${h}h${m}m`;
}

function updateMetrics(m) {
    if (m.memory_mb !== undefined) {
        document.getElementById("sys-ram").textContent = `${m.memory_mb} MB`;
    }
    if (m.cpu_percent !== undefined) {
        document.getElementById("sys-cpu").textContent = `${m.cpu_percent}%`;
    }
    if (m.db_chunks !== undefined) {
        document.getElementById("db-chunks").textContent = m.db_chunks.toLocaleString();
    }

    // Groq cores visualization
    updateGroqCores();
}

function updateGroqCores() {
    const roles = [
        { name: "User", key: "GROQ_API_KEY_USER" },
        { name: "Verify", key: "GROQ_API_KEY_VERIFY" },
        { name: "Research", key: "GROQ_API_KEY_RESEARCH" },
        { name: "Walker", key: "GROQ_API_KEY_WALKER" },
        { name: "Forge", key: "GROQ_API_KEY_FORGE" },
        { name: "Overnight", key: "GROQ_API_KEY_OVERNIGHT" },
        { name: "Knowledge", key: "GROQ_API_KEY_KNOWLEDGE" },
        { name: "Reserve 1", key: "GROQ_API_KEY_RESERVE_1" },
        { name: "Reserve 2", key: "GROQ_API_KEY_RESERVE_2" },
        { name: "Reserve 3", key: "GROQ_API_KEY_RESERVE_3" },
        { name: "Fallback", key: "GROQ_API_KEY_FALLBACK" },
    ];
    const container = document.getElementById("groq-cores");
    container.innerHTML = roles.map(r =>
        `<div class="flex items-center gap-2 text-xs py-0.5">
            <span class="core-dot active"></span>
            <span class="text-gray-400">${r.name}</span>
        </div>`
    ).join("");
}

function updateAgents(agents) {
    const container = document.getElementById("agent-list");
    if (!agents || agents.length === 0) {
        container.innerHTML = '<div class="text-xs text-gray-600">Geen agents actief</div>';
        return;
    }
    container.innerHTML = agents.map(a => {
        const status = (a.status || "").toUpperCase();
        const isPaused = status === "PAUSED";
        const statusColor = isPaused ? "text-sovereign-red" :
                           status === "ACTIVE" ? "text-sovereign-green glow-green" :
                           status === "COOLDOWN" ? "text-sovereign-amber" : "text-gray-500";
        const toggleLabel = isPaused ? "&#9654;" : "&#10074;&#10074;";
        const toggleTitle = isPaused ? "Hervat agent" : "Pauzeer agent";
        // Synaptic Power badge: SP = weight * 100 (percentage display)
        const sw = a.synaptic_weight;
        let swBadge = "";
        if (sw != null) {
            const sp = Math.round(sw * 100);
            const isElite = sp >= 150;
            const swColor = isElite ? "text-yellow-300 glow-gold" :
                           sp >= 110 ? "text-sovereign-green" :
                           sp >= 90 ? "text-sovereign-cyan" :
                           sp >= 70 ? "text-sovereign-amber" : "text-sovereign-red";
            swBadge = `<span class="${swColor} w-14 text-right text-xs font-mono font-bold" title="Synaptic Power (${sw.toFixed(3)})">SP:${sp}</span>`;
        } else {
            swBadge = `<span class="text-gray-700 w-14 text-right text-xs">—</span>`;
        }
        return `<div class="agent-row">
            <span class="text-gray-300 flex-1">${a.name}</span>
            ${swBadge}
            <span class="${statusColor} w-16 text-center">${status}</span>
            <span class="text-gray-500 w-14 text-right">${a.tasks_completed}</span>
            <button onclick="toggleAgent('${a.name}', ${!isPaused})"
                    class="ml-2 px-1.5 py-0.5 rounded text-xs border transition-colors
                           ${isPaused
                               ? 'border-sovereign-green text-sovereign-green hover:bg-green-900/20'
                               : 'border-sovereign-border text-gray-500 hover:border-sovereign-amber hover:text-sovereign-amber'}"
                    title="${toggleTitle}">
                ${toggleLabel}
            </button>
        </div>`;
    }).join("");
}

async function toggleAgent(name, paused) {
    try {
        const resp = await apiFetch("/api/v1/agents/toggle", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ agent: name, paused }),
        });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            console.error("Toggle failed:", resp.status, err);
            return;
        }
        // Direct agents herpollen voor onmiddellijke visuele feedback
        const agentsResp = await apiFetch("/api/v1/agents");
        if (agentsResp.ok) {
            const agents = await agentsResp.json();
            updateAgents(agents);
        }
    } catch (err) {
        console.error("Toggle error:", err);
    }
}

function setOffline() {
    const dot = document.getElementById("status-dot");
    const text = document.getElementById("status-text");
    dot.className = "w-2 h-2 rounded-full bg-sovereign-red status-pulse";
    text.textContent = "OFFLINE";
    text.className = "text-sovereign-red text-sm";
    document.getElementById("sys-status").textContent = "OFFLINE";
    document.getElementById("sys-status").className = "text-sm font-bold text-sovereign-red";
}

// ─── FILE INGEST ────────────────────────────────────

function handleDrop(event) {
    event.preventDefault();
    event.currentTarget.classList.remove("border-sovereign-accent", "bg-purple-900/10");
    const files = event.dataTransfer.files;
    handleFiles(files);
}

function handleFiles(files) {
    for (const file of files) {
        uploadFile(file);
    }
}

async function uploadFile(file) {
    const formData = new FormData();
    formData.append("bestand", file);

    // Tags meesturen als die zijn ingevuld
    const tagsInput = document.getElementById("ingest-tags");
    const tags = tagsInput ? tagsInput.value.trim() : "";
    if (tags) {
        formData.append("tags", tags);
    }

    try {
        const resp = await fetch(`${BASE}/api/v1/ingest/background`, {
            method: "POST",
            headers: { "X-API-Key": API_KEY },
            body: formData,
        });

        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            addJobToUI(file.name, "failed", err.detail || "Upload mislukt");
            return;
        }

        const data = await resp.json();
        const jobId = data.job_id;

        const jobEl = addJobToUI(file.name, "pending", jobId);
        activeJobs.set(jobId, { status: "pending", bestand: file.name, chunks: 0, el: jobEl });
        pollJobStatus(jobId);

    } catch (err) {
        addJobToUI(file.name, "failed", err.message);
    }
}

function addJobToUI(filename, status, info) {
    const container = document.getElementById("job-list");
    // Remove placeholder
    if (container.querySelector(".text-center")) {
        container.innerHTML = "";
    }

    const el = document.createElement("div");
    el.className = "bg-sovereign-bg rounded p-3 space-y-2";
    el.innerHTML = `
        <div class="flex justify-between items-center">
            <span class="text-xs text-gray-300 truncate max-w-[180px]" title="${filename}">${filename}</span>
            <span class="job-status text-xs font-bold ${statusColor(status)}">${status.toUpperCase()}</span>
        </div>
        <div class="job-progress"><div class="job-progress-fill ${status}"></div></div>
        <div class="text-xs text-gray-600 job-info">${info}</div>
    `;
    container.prepend(el);
    updateJobCounter();
    return el;
}

function statusColor(status) {
    switch (status) {
        case "completed": return "text-sovereign-green";
        case "failed": return "text-sovereign-red";
        case "running": return "text-sovereign-accent";
        default: return "text-sovereign-amber";
    }
}

async function pollJobStatus(jobId) {
    const job = activeJobs.get(jobId);
    if (!job) return;

    try {
        const resp = await apiFetch(`/api/v1/ingest/background/${jobId}`);
        if (!resp.ok) return;
        const data = await resp.json();

        job.status = data.status;
        job.chunks = data.chunks || 0;

        // Update UI
        const statusEl = job.el.querySelector(".job-status");
        const progressEl = job.el.querySelector(".job-progress-fill");
        const infoEl = job.el.querySelector(".job-info");

        statusEl.textContent = data.status.toUpperCase();
        statusEl.className = `job-status text-xs font-bold ${statusColor(data.status)}`;
        progressEl.className = `job-progress-fill ${data.status}`;

        if (data.status === "completed") {
            infoEl.textContent = `${data.chunks} chunks ingested`;
            updateJobCounter();
            // Refresh DB count
            pollHealth();
            return;
        } else if (data.status === "failed") {
            infoEl.textContent = data.error || "Ingest mislukt";
            updateJobCounter();
            return;
        } else {
            infoEl.textContent = data.status === "running" ? "Embedding chunks..." : "In wachtrij...";
        }
    } catch { /* retry */ }

    // Keep polling
    setTimeout(() => pollJobStatus(jobId), JOB_POLL_MS);
}

function updateJobCounter() {
    const total = activeJobs.size;
    const completed = [...activeJobs.values()].filter(j => j.status === "completed").length;
    const failed = [...activeJobs.values()].filter(j => j.status === "failed").length;
    document.getElementById("job-counter").textContent =
        `${completed}/${total} done` + (failed > 0 ? `, ${failed} failed` : "");
}

// ─── RAG CHAT ───────────────────────────────────────

let _queryInFlight = false;

async function sendQuery() {
    const input = document.getElementById("chat-input");
    const message = input.value.trim();
    if (!message || _queryInFlight) return;
    input.value = "";

    addChatMessage(message, "user");

    // Show thinking indicator
    const thinkingEl = addThinkingIndicator();
    _queryInFlight = true;
    const t0 = performance.now();

    // Elapsed timer — update every second
    const timerHandle = setInterval(() => {
        const elapsed = ((performance.now() - t0) / 1000).toFixed(0);
        const label = thinkingEl.querySelector(".thinking-time");
        if (label) label.textContent = `${elapsed}s`;
    }, 1000);

    try {
        // No timeout on the fetch — SwarmEngine queries can take 60s+
        const resp = await apiFetch("/api/v1/query", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message, stream: false }),
        });

        clearInterval(timerHandle);
        thinkingEl.remove();

        if (!resp.ok) {
            let detail = `HTTP ${resp.status}`;
            try {
                const err = await resp.json();
                detail = err.detail || `HTTP ${resp.status}: ${resp.statusText}`;
            } catch { /* no json body */ }
            addChatMessage(detail, "error");
            return;
        }

        let data;
        try {
            data = await resp.json();
        } catch (parseErr) {
            addChatMessage(`Response parse error: ${parseErr.message}`, "error");
            return;
        }

        const payloads = data.payloads || [];
        if (payloads.length === 0) {
            addChatMessage("Geen resultaat van het netwerk.", "omega");
            return;
        }

        // Render each agent payload as a separate structured block
        for (const payload of payloads) {
            const text = (payload.display_text || payload.content || "").trim();
            if (!text) continue;
            addAgentPayload(payload.agent || "Omega", text, payload.metadata);
        }

        // Summary meta line
        const elapsed = data.execution_time
            ? data.execution_time.toFixed(1) + "s"
            : ((performance.now() - t0) / 1000).toFixed(1) + "s";
        const errCount = data.error_count || 0;
        let meta = `${payloads.length} agent${payloads.length !== 1 ? "s" : ""} | ${elapsed}`;
        if (data.trace_id) meta += ` | trace:${data.trace_id.slice(0, 8)}`;
        if (errCount > 0) meta += ` | ${errCount} errors`;
        addChatMeta(meta);

    } catch (err) {
        clearInterval(timerHandle);
        thinkingEl.remove();
        // Differentiate network errors from other failures
        const isTimeout = err.name === "AbortError" || err.message.includes("timeout");
        const isNetwork = err.name === "TypeError" || err.message.includes("Failed to fetch");
        let detail = err.message;
        if (isTimeout) detail = "Request timeout — de server reageert niet";
        else if (isNetwork) detail = "Netwerk onbereikbaar — is de server nog online?";
        addChatMessage(`${detail}`, "error");
    } finally {
        _queryInFlight = false;
    }
}

function addThinkingIndicator() {
    const container = document.getElementById("chat-messages");
    const placeholder = container.querySelector(".text-center");
    if (placeholder) placeholder.remove();

    const el = document.createElement("div");
    el.className = "chat-omega p-3 mr-8 thinking-indicator";
    el.innerHTML = `
        <div class="text-xs text-sovereign-glow mb-1">&Omega; Omega</div>
        <div class="flex items-center gap-2 text-sm text-gray-400">
            <span class="thinking-dots">Analyzing<span>.</span><span>.</span><span>.</span></span>
            <span class="thinking-time text-xs text-gray-600">0s</span>
        </div>
    `;
    container.appendChild(el);
    container.scrollTop = container.scrollHeight;
    return el;
}

function addAgentPayload(agent, text, metadata) {
    const container = document.getElementById("chat-messages");
    const el = document.createElement("div");
    el.className = "chat-omega p-3 mr-8";

    // Agent badge color based on name
    const agentColors = {
        "Echo": "text-sovereign-green",
        "Strategist": "text-sovereign-cyan",
        "#@*VirtualTwin": "text-sovereign-amber",
        "Spark": "text-yellow-400",
        "Memex": "text-blue-400",
        "Iolaax": "text-purple-400",
        "Cipher": "text-pink-400",
    };
    const color = agentColors[agent] || "text-sovereign-glow";
    const execTime = metadata?.execution_time
        ? ` (${metadata.execution_time.toFixed(1)}s)` : "";

    el.innerHTML = `
        <div class="flex items-center gap-2 mb-1">
            <span class="text-xs ${color} font-bold">${escapeHtml(agent)}</span>
            <span class="text-xs text-gray-600">${execTime}</span>
        </div>
        <div class="text-sm text-gray-200 whitespace-pre-wrap">${escapeHtml(text)}</div>
    `;
    container.appendChild(el);
    container.scrollTop = container.scrollHeight;
}

function addChatMessage(text, type) {
    const container = document.getElementById("chat-messages");
    const placeholder = container.querySelector(".text-center");
    if (placeholder) placeholder.remove();

    const el = document.createElement("div");
    if (type === "user") {
        el.className = "chat-user p-3 ml-8";
        el.innerHTML = `<div class="text-xs text-gray-500 mb-1">Danny</div>
                        <div class="text-sm text-gray-200">${escapeHtml(text)}</div>`;
    } else if (type === "omega") {
        el.className = "chat-omega p-3 mr-8";
        el.innerHTML = `<div class="text-xs text-sovereign-glow mb-1">&Omega; Omega</div>
                        <div class="text-sm text-gray-200 whitespace-pre-wrap">${escapeHtml(text)}</div>`;
    } else {
        el.className = "bg-red-900/20 border border-red-800/30 rounded p-2 mx-4 text-xs text-sovereign-red";
        el.textContent = text;
    }
    container.appendChild(el);
    container.scrollTop = container.scrollHeight;
}

function addChatMeta(text) {
    const container = document.getElementById("chat-messages");
    const el = document.createElement("div");
    el.className = "text-xs text-gray-600 text-center py-1";
    el.textContent = text;
    container.appendChild(el);
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

// ─── SYNAPTIC LEADERBOARD ────────────────────────────

const SYNAPSE_POLL_MS = 30000; // 30s refresh
let synapseTimer = null;

function startSynapseMonitor() {
    pollSynapseLeaderboard();
    synapseTimer = setInterval(pollSynapseLeaderboard, SYNAPSE_POLL_MS);
}

async function pollSynapseLeaderboard() {
    try {
        const resp = await apiFetch("/api/v1/synapse/weights");
        if (!resp.ok) return;
        const data = await resp.json();
        renderLeaderboard(data);
    } catch { /* non-critical */ }
}

function renderLeaderboard(data) {
    const pathways = data.pathways || {};
    const container = document.getElementById("synapse-leaderboard");
    if (!container) return;

    // Compute per-agent averages
    const agentMap = {};
    for (const [cat, agents] of Object.entries(pathways)) {
        for (const [name, info] of Object.entries(agents)) {
            if (!agentMap[name]) agentMap[name] = { biases: [], fires: 0, succ: 0, fail: 0 };
            if (info.effective_bias != null) agentMap[name].biases.push(info.effective_bias);
            agentMap[name].fires += info.fires || 0;
            agentMap[name].succ += info.successes || 0;
            agentMap[name].fail += info.fails || 0;
        }
    }

    const ranked = Object.entries(agentMap)
        .map(([name, d]) => ({
            name,
            sp: d.biases.length ? d.biases.reduce((a, b) => a + b, 0) / d.biases.length : 0,
            fires: d.fires,
            succ: d.succ,
            rate: d.fires > 0 ? (d.succ / d.fires * 100) : 0,
        }))
        .sort((a, b) => b.sp - a.sp);

    if (ranked.length === 0) {
        container.innerHTML = '<div class="text-xs text-gray-600">No pathway data</div>';
        return;
    }

    // Top 3 Alphas + weakest Underperformer
    const top3 = ranked.slice(0, 3);
    const weakest = ranked[ranked.length - 1];

    // Build HTML table
    let html = `<table class="w-full text-xs border-collapse">
        <thead>
            <tr class="text-gray-600 border-b border-sovereign-border">
                <th class="text-left py-1 pl-1">Rank</th>
                <th class="text-left py-1">Agent</th>
                <th class="text-right py-1">SP</th>
                <th class="text-right py-1 pr-1">Power</th>
                <th class="text-right py-1 pr-1">Fires</th>
                <th class="text-right py-1 pr-1">Rate</th>
            </tr>
        </thead>
        <tbody>`;

    // Render Alpha rows (top 3)
    top3.forEach((a, i) => {
        const spVal = Math.round(a.sp * 100);
        const pct = Math.min(Math.max(a.sp / 1.3, 0), 1) * 100;
        const isAlpha = i === 0;
        const rank = isAlpha ? "👑" : `#${i + 1}`;
        const rowClass = isAlpha ? "border border-yellow-800/40 bg-yellow-900/5" : "";
        const textColor = isAlpha ? "text-yellow-300 glow-gold" :
                         spVal >= 110 ? "text-sovereign-green" : "text-sovereign-cyan";
        const label = isAlpha ? "ALPHA" : "";
        html += `<tr class="${rowClass}">
            <td class="py-1.5 pl-1 ${textColor} font-bold">${rank}</td>
            <td class="py-1.5 ${textColor} font-bold">${escapeHtml(a.name)} ${label ? `<span class="text-yellow-500/60 text-[10px]">${label}</span>` : ""}</td>
            <td class="py-1.5 text-right font-mono ${textColor} font-bold">${spVal}</td>
            <td class="py-1.5 pr-1 w-16">
                <div class="w-full h-1.5 bg-gray-800 rounded overflow-hidden">
                    <div class="${isAlpha ? 'bg-yellow-400' : 'bg-sovereign-green'} h-full rounded transition-all duration-700" style="width:${pct.toFixed(1)}%"></div>
                </div>
            </td>
            <td class="py-1.5 text-right text-gray-500 pr-1">${a.fires}</td>
            <td class="py-1.5 text-right text-gray-500 pr-1">${a.rate.toFixed(0)}%</td>
        </tr>`;
    });

    // Separator + Underperformer
    if (weakest && !top3.includes(weakest)) {
        const spVal = Math.round(weakest.sp * 100);
        const pct = Math.min(Math.max(weakest.sp / 1.3, 0), 1) * 100;
        html += `<tr class="border-t border-sovereign-border/50"><td colspan="6" class="py-0.5"></td></tr>
        <tr class="border border-red-900/30 bg-red-900/5">
            <td class="py-1.5 pl-1 text-sovereign-red font-bold">📉</td>
            <td class="py-1.5 text-sovereign-red font-bold">${escapeHtml(weakest.name)} <span class="text-red-500/60 text-[10px]">ATROPHY</span></td>
            <td class="py-1.5 text-right font-mono text-sovereign-red font-bold">${spVal}</td>
            <td class="py-1.5 pr-1 w-16">
                <div class="w-full h-1.5 bg-gray-800 rounded overflow-hidden">
                    <div class="bg-sovereign-red h-full rounded transition-all duration-700" style="width:${pct.toFixed(1)}%"></div>
                </div>
            </td>
            <td class="py-1.5 text-right text-gray-500 pr-1">${weakest.fires}</td>
            <td class="py-1.5 text-right text-gray-500 pr-1">${weakest.rate.toFixed(0)}%</td>
        </tr>`;
    }

    html += `</tbody></table>`;

    // Phoenix Boost button for weakest agent
    if (weakest && !top3.includes(weakest)) {
        html += `<button onclick="boostAgent('${escapeHtml(weakest.name)}')"
            class="mt-2 w-full text-xs py-1.5 rounded border border-sovereign-amber text-sovereign-amber
                   hover:bg-amber-900/20 transition-colors font-bold"
            title="Operation Phoenix: 3 triviale succes-taken om SP te herstellen">
            &#x1F525; PHOENIX BOOST: ${escapeHtml(weakest.name)}
        </button>`;
    }

    container.innerHTML = html;

    // Summary stats
    const swarmAvg = ranked.reduce((s, a) => s + a.sp, 0) / ranked.length;
    const totalFires = ranked.reduce((s, a) => s + a.fires, 0);
    document.getElementById("synapse-avg").textContent = `SP:${Math.round(swarmAvg * 100)}`;
    document.getElementById("synapse-fires").textContent = totalFires.toLocaleString();

    // Pulse indicator
    const pulse = document.getElementById("synapse-pulse");
    if (pulse) {
        pulse.classList.add("bg-sovereign-green");
        pulse.classList.remove("bg-gray-600");
    }
}

async function boostAgent(agentName) {
    const btn = event.target;
    btn.disabled = true;
    btn.textContent = "⏳ Phoenix activating...";
    try {
        const resp = await apiFetch("/api/v1/phoenix/boost", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ agent: agentName }),
        });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            btn.textContent = `❌ ${err.detail || "Boost failed"}`;
            return;
        }
        const data = await resp.json();
        btn.textContent = `✅ SP ${data.old_sp} → ${data.new_sp}`;
        btn.className = btn.className.replace("border-sovereign-amber", "border-sovereign-green")
                                     .replace("text-sovereign-amber", "text-sovereign-green");
        // Refresh leaderboard after boost
        setTimeout(pollSynapseLeaderboard, 1000);
    } catch (err) {
        btn.textContent = "❌ Network error";
    }
}

// ─── UTILS ──────────────────────────────────────────

function apiFetch(path, options = {}) {
    const headers = { "X-API-Key": API_KEY, ...(options.headers || {}) };
    return fetch(`${BASE}${path}`, { ...options, headers });
}
