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

// ─── AUTH (Hardware Auto-Auth) ──────────────────────

window.addEventListener("DOMContentLoaded", () => {
    hardwareAuth();
});

async function hardwareAuth() {
    // Fetch Silicon Seal from localhost-only hardware endpoint
    try {
        const resp = await fetch(`${BASE}/api/v1/seal/local`);
        if (resp.ok) {
            const data = await resp.json();
            if (data.seal) {
                API_KEY = data.seal;
                const gate = document.getElementById("auth-gate");
                const dash = document.getElementById("dashboard");
                if (gate) { gate.classList.add("hidden"); gate.style.display = "none"; }
                if (dash) { dash.classList.remove("hidden"); dash.style.display = "flex"; }
                startTelemetry();
                return;
            }
        }
    } catch { /* fall through */ }

    // Hardware auth failed — show error, but still show dashboard
    const err = document.getElementById("auth-error");
    if (err) { err.classList.remove("hidden"); err.style.display = "block"; }
    // Fallback: try to show dashboard anyway after 2s
    setTimeout(() => {
        const gate = document.getElementById("auth-gate");
        const dash = document.getElementById("dashboard");
        if (gate) { gate.classList.add("hidden"); gate.style.display = "none"; }
        if (dash) { dash.classList.remove("hidden"); dash.style.display = "flex"; }
        startTelemetry();
    }, 2000);
}

// ─── WEBSOCKET TELEMETRIE (v6.19.0) ─────────────────
let ws = null;
let wsReconnectTimer = null;

function startWebSocket() {
    const wsUrl = `${BASE.replace("http", "ws")}/ws/events?seal=${encodeURIComponent(API_KEY)}`;
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        console.log("[WS] Connected");
        const wsDot = document.getElementById("ws-status");
        if (wsDot) { wsDot.className = "w-1.5 h-1.5 rounded-full bg-sovereign-green status-pulse ml-auto"; }
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
        const wsDot = document.getElementById("ws-status");
        if (wsDot) { wsDot.className = "w-1.5 h-1.5 rounded-full bg-sovereign-red status-pulse ml-auto"; }
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
    el.innerHTML = `<span class="text-sovereign-amber">${data.timestamp}</span> `
        + `<span class="text-sovereign-cyan">${data.event_type}</span> `
        + `<span class="text-neutral-400">${data.bron}: ${data.summary.substring(0, 80)}</span>`;
    evtLog.prepend(el);
    // Hou log beheersbaar
    while (evtLog.children.length > 50) evtLog.removeChild(evtLog.lastChild);
}

// ─── TAB SWITCHING ──────────────────────────────────

let activeTab = "overview";
const TAB_POLL_MS = 10000; // secondary tabs: 10s
let tabPollTimer = null;

document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".tab-btn").forEach(btn => {
        btn.addEventListener("click", () => switchTab(btn.dataset.tab));
    });
});

function switchTab(tab) {
    if (tab === activeTab) return;
    activeTab = tab;

    // Update button styles
    document.querySelectorAll(".tab-btn").forEach(b => {
        b.classList.toggle("active", b.dataset.tab === tab);
    });

    // Show/hide tab content
    document.querySelectorAll(".tab-content").forEach(el => {
        el.classList.toggle("hidden", el.id !== `tab-${tab}`);
        el.classList.toggle("active", el.id === `tab-${tab}`);
    });

    // Poll the active tab immediately
    if (tab === "observatory") pollObservatory();
    if (tab === "memory") pollMemory();
    if (tab === "security") pollSecurity();
    if (tab === "brain") pollBrain();
    if (tab === "swarm") pollSwarm();
    if (tab === "apps") pollApps();
    if (tab === "knowledge") pollKnowledge();
    if (tab === "daemon") pollDaemon();
}

// ─── TELEMETRY ──────────────────────────────────────

function startTelemetry() {
    pollHealth();
    healthTimer = setInterval(pollHealth, POLL_INTERVAL);
    startSynapseMonitor();
    startWebSocket();
    // Secondary tab polling (observatory/memory/security)
    tabPollTimer = setInterval(() => {
        if (activeTab === "observatory") pollObservatory();
        if (activeTab === "memory") pollMemory();
        if (activeTab === "security") pollSecurity();
        if (activeTab === "brain") pollBrain();
        if (activeTab === "swarm") pollSwarm();
        if (activeTab === "apps") pollApps();
        if (activeTab === "knowledge") pollKnowledge();
        if (activeTab === "daemon") pollDaemon();
    }, TAB_POLL_MS);
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

    // Parallel: fetch metrics, agents, GPU, blackbox, ouroboros, errors
    try {
        const [metricsResp, agentsResp, gpuResp, bbResp, ouroResp, errResp] = await Promise.all([
            apiFetch("/api/v1/metrics").catch(() => null),
            apiFetch("/api/v1/agents").catch(() => null),
            apiFetch("/api/v1/gpu/status").catch(() => null),
            apiFetch("/api/v1/blackbox/stats").catch(() => null),
            apiFetch("/api/v1/ouroboros/status").catch(() => null),
            apiFetch("/api/v1/errors/recent").catch(() => null),
        ]);
        if (metricsResp?.ok) {
            const m = await metricsResp.json();
            updateMetrics(m);
        }
        if (agentsResp?.ok) {
            const agents = await agentsResp.json();
            updateAgents(agents);
            // Header agent count
            const hdr = document.getElementById("hdr-agents");
            if (hdr) hdr.textContent = `${agents.length} agents`;
        }
        if (gpuResp?.ok) {
            const gpu = await gpuResp.json();
            updateGPU(gpu);
        }
        if (bbResp?.ok) {
            const bb = await bbResp.json();
            updateBlackBox(bb);
        }
        if (ouroResp?.ok) {
            const ouro = await ouroResp.json();
            updateOuroboros(ouro);
        }
        if (errResp?.ok) {
            const errs = await errResp.json();
            renderRecentErrors(errs);
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

    // Sovereign Monitor: circuit breakers + governor stats
    updateCircuitBreakers(data.circuit_breakers || {});
    const secWs = document.getElementById("sec-ws");
    if (secWs) secWs.textContent = `${data.active_ws_clients || 0}/3`;

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
        const hdr = document.getElementById("hdr-ram");
        if (hdr) hdr.textContent = `${m.memory_mb} MB`;
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

// ─── CIRCUIT BREAKERS ────────────────────────────────

function updateCircuitBreakers(breakers) {
    const container = document.getElementById("circuit-breakers");
    if (!container) return;
    const entries = Object.entries(breakers);
    if (entries.length === 0) {
        container.innerHTML = '<div class="text-xs text-gray-600">Geen breakers actief</div>';
        return;
    }
    container.innerHTML = entries.map(([name, info]) => {
        const state = (info.state || "closed").toLowerCase();
        const color = state === "closed" ? "text-sovereign-green" :
                     state === "half_open" ? "text-sovereign-amber" : "text-sovereign-red";
        const dotColor = state === "closed" ? "bg-sovereign-green" :
                        state === "half_open" ? "bg-sovereign-amber" : "bg-sovereign-red";
        const label = state === "closed" ? "OK" : state.toUpperCase();
        return `<div class="flex items-center justify-between text-xs py-0.5">
            <span class="flex items-center gap-1.5">
                <span class="w-1.5 h-1.5 rounded-full ${dotColor}"></span>
                <span class="text-gray-400">${escapeHtml(name)}</span>
            </span>
            <span class="${color} font-bold">${label}</span>
        </div>`;
    }).join("");
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
            headers: { "X-Silicon-Seal": API_KEY },
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
    const headers = { "X-Silicon-Seal": API_KEY, ...(options.headers || {}) };
    return fetch(`${BASE}${path}`, { ...options, headers });
}

// ─── GPU STATUS ─────────────────────────────────────

function updateGPU(gpu) {
    const setEl = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };

    if (gpu.vram_used_mb !== undefined && gpu.vram_total_mb !== undefined) {
        setEl("gpu-vram", `${gpu.vram_used_mb}/${gpu.vram_total_mb} MB`);
    }
    if (gpu.temperature !== undefined) {
        setEl("gpu-temp", `${gpu.temperature}°C`);
        setEl("hdr-gpu-temp", `GPU ${gpu.temperature}°C`);
    }
    if (gpu.power_draw !== undefined) {
        setEl("gpu-power", `${gpu.power_draw}W`);
    }
    if (gpu.clock_mhz !== undefined) {
        setEl("gpu-clock", `${gpu.clock_mhz} MHz`);
    }
}

// ─── BLACKBOX IMMUNE MEMORY ─────────────────────────

function updateBlackBox(bb) {
    const setEl = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
    setEl("bb-failures", bb.total_failures ?? "--");
    setEl("bb-antibodies", bb.antibody_count ?? bb.total_antibodies ?? "--");
}

// ─── OBSERVATORY TAB ────────────────────────────────

async function pollObservatory() {
    const [lbResp, costResp, failResp, phantomResp, tribResp, shieldResp, regResp, auctResp, shardResp] = await Promise.all([
        apiFetch("/api/v1/observatory/leaderboard").catch(() => null),
        apiFetch("/api/v1/observatory/costs").catch(() => null),
        apiFetch("/api/v1/observatory/failures").catch(() => null),
        apiFetch("/api/v1/phantom/accuracy").catch(() => null),
        apiFetch("/api/v1/tribunal/stats").catch(() => null),
        apiFetch("/api/v1/schild/stats").catch(() => null),
        apiFetch("/api/v1/models/registry").catch(() => null),
        apiFetch("/api/v1/observatory/auctions").catch(() => null),
        apiFetch("/api/v1/shards/stats").catch(() => null),
    ]);

    if (lbResp?.ok) renderModelLeaderboard(await lbResp.json());
    if (costResp?.ok) renderCostAnalysis(await costResp.json());
    if (failResp?.ok) renderFailureAnalysis(await failResp.json());
    if (phantomResp?.ok) renderPhantomStats(await phantomResp.json());
    if (tribResp?.ok) {
        const t = await tribResp.json();
        const setEl = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
        setEl("trib-accepted", t.accepted ?? t.total_accepted ?? "--");
        setEl("trib-failed", t.failed ?? t.total_failed ?? "--");
    }
    if (shieldResp?.ok) {
        const s = await shieldResp.json();
        const setEl = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
        setEl("shield-blocked", s.blocked ?? s.total_blocked ?? "--");
        setEl("shield-passed", s.passed ?? s.total_passed ?? "--");
    }
    if (regResp?.ok) renderModelRegistry(await regResp.json());
    if (auctResp?.ok) renderAuctionLogs(await auctResp.json());
    if (shardResp?.ok) renderShardStats(await shardResp.json());
}

function renderModelLeaderboard(data) {
    const container = document.getElementById("model-leaderboard");
    if (!container) return;
    const models = data.leaderboard || data.models || data || [];
    if (!Array.isArray(models) || models.length === 0) {
        container.innerHTML = '<div class="text-xs text-gray-600">No model data available</div>';
        return;
    }
    let html = `<table class="w-full text-xs border-collapse">
        <thead><tr class="text-gray-600 border-b border-sovereign-border">
            <th class="text-left py-1">Model</th>
            <th class="text-right py-1">Calls</th>
            <th class="text-right py-1">Avg Latency</th>
            <th class="text-right py-1">Tokens</th>
            <th class="text-right py-1">Success %</th>
        </tr></thead><tbody>`;
    for (const m of models) {
        const name = m.model || m.name || "unknown";
        const calls = m.total_calls ?? m.calls ?? 0;
        const latency = m.avg_latency != null ? `${(m.avg_latency * 1000).toFixed(0)}ms` : "--";
        const tokens = m.total_tokens ?? m.tokens ?? 0;
        const rate = m.success_rate != null ? `${(m.success_rate * 100).toFixed(1)}%` : "--";
        html += `<tr class="border-b border-sovereign-border/30 hover:bg-sovereign-bg">
            <td class="py-1.5 text-gray-300">${escapeHtml(name)}</td>
            <td class="py-1.5 text-right text-gray-400">${calls.toLocaleString()}</td>
            <td class="py-1.5 text-right text-sovereign-cyan">${latency}</td>
            <td class="py-1.5 text-right text-gray-400">${tokens.toLocaleString()}</td>
            <td class="py-1.5 text-right text-sovereign-green font-bold">${rate}</td>
        </tr>`;
    }
    html += `</tbody></table>`;
    container.innerHTML = html;
}

function renderCostAnalysis(data) {
    const container = document.getElementById("cost-analysis");
    if (!container) return;
    const costs = data.costs || data.breakdown || data || {};
    if (typeof costs === "object" && !Array.isArray(costs)) {
        let html = "";
        for (const [provider, info] of Object.entries(costs)) {
            const val = typeof info === "number" ? info : (info.total_cost ?? info.tokens ?? 0);
            html += `<div class="flex justify-between items-center text-xs py-1">
                <span class="text-gray-400">${escapeHtml(provider)}</span>
                <span class="text-sovereign-amber font-bold">${typeof val === "number" ? val.toLocaleString() : val}</span>
            </div>`;
        }
        container.innerHTML = html || '<div class="text-xs text-gray-600">No cost data</div>';
    } else {
        container.innerHTML = `<pre class="text-xs text-gray-400 overflow-x-auto">${escapeHtml(JSON.stringify(data, null, 2))}</pre>`;
    }
}

function renderFailureAnalysis(data) {
    const container = document.getElementById("failure-analysis");
    if (!container) return;
    const failures = data.failures || data.recent || data || [];
    if (Array.isArray(failures) && failures.length > 0) {
        container.innerHTML = failures.slice(0, 10).map(f => {
            const ts = f.timestamp || f.time || "";
            const msg = f.error || f.message || f.detail || JSON.stringify(f);
            return `<div class="text-xs border-l-2 border-sovereign-red pl-2 py-1">
                <span class="text-gray-600">${escapeHtml(ts)}</span>
                <span class="text-gray-400 ml-1">${escapeHtml(String(msg).substring(0, 100))}</span>
            </div>`;
        }).join("");
    } else {
        container.innerHTML = '<div class="text-xs text-sovereign-green">No failures recorded</div>';
    }
}

function renderPhantomStats(data) {
    const container = document.getElementById("phantom-stats");
    if (!container) return;
    const accuracy = data.accuracy ?? data.hit_rate ?? null;
    const predictions = data.total_predictions ?? data.total ?? 0;
    const hits = data.hits ?? data.correct ?? 0;
    let html = `<div class="grid grid-cols-2 gap-2">
        <div class="stat-box p-2"><div class="stat-label">Predictions</div><div class="stat-value">${predictions}</div></div>
        <div class="stat-box p-2"><div class="stat-label">Hits</div><div class="stat-value text-sovereign-green">${hits}</div></div>
    </div>`;
    if (accuracy != null) {
        const pct = (accuracy * 100).toFixed(1);
        html += `<div class="stat-box p-3 text-center mt-2">
            <div class="stat-label">Accuracy</div>
            <div class="text-2xl font-bold ${accuracy > 0.7 ? 'text-sovereign-green' : accuracy > 0.4 ? 'text-sovereign-amber' : 'text-sovereign-red'}">${pct}%</div>
        </div>`;
    }
    container.innerHTML = html;
}

// ─── MEMORY TAB ─────────────────────────────────────

async function pollMemory() {
    const [memResp, busResp, alertResp, traceResp] = await Promise.all([
        apiFetch("/api/v1/memory/recent").catch(() => null),
        apiFetch("/api/v1/bus/stats").catch(() => null),
        apiFetch("/api/v1/alerts/history").catch(() => null),
        apiFetch("/api/v1/traces").catch(() => null),
    ]);

    if (memResp?.ok) renderCorticalEvents(await memResp.json());
    if (busResp?.ok) renderBusStats(await busResp.json());
    if (alertResp?.ok) renderAlertHistory(await alertResp.json());
    if (traceResp?.ok) renderTraces(await traceResp.json());
}

function renderCorticalEvents(data) {
    const container = document.getElementById("cortical-events");
    if (!container) return;
    const events = data.events || data.recent || data || [];
    if (!Array.isArray(events) || events.length === 0) {
        container.innerHTML = '<div class="text-xs text-gray-600">No recent events</div>';
        return;
    }
    container.innerHTML = events.slice(0, 50).map(e => {
        const ts = e.timestamp || e.time || "";
        const type = e.event_type || e.type || "unknown";
        const summary = e.summary || e.data || "";
        return `<div class="cortical-event">
            <div class="event-time">${escapeHtml(ts)}</div>
            <div class="event-type">${escapeHtml(type)}</div>
            <div class="event-summary">${escapeHtml(String(summary).substring(0, 200))}</div>
        </div>`;
    }).join("");
}

function renderBusStats(data) {
    const setEl = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
    setEl("bus-subs", data.subscribers ?? data.total_subscribers ?? "--");
    setEl("bus-published", data.published ?? data.events_published ?? "--");
    setEl("bus-delivered", data.delivered ?? data.events_delivered ?? "--");
    setEl("bus-errors", data.errors ?? data.delivery_errors ?? "0");
}

function renderAlertHistory(data) {
    const container = document.getElementById("alert-history");
    if (!container) return;
    const alerts = data.alerts || data.history || data || [];
    if (!Array.isArray(alerts) || alerts.length === 0) {
        container.innerHTML = '<div class="text-xs text-gray-600">No recent alerts</div>';
        return;
    }
    container.innerHTML = alerts.slice(0, 20).map(a => {
        const ts = a.timestamp || a.time || "";
        const msg = a.message || a.summary || "";
        const level = (a.level || a.severity || "info").toLowerCase();
        const color = level === "critical" ? "border-sovereign-red" :
                     level === "warning" ? "border-sovereign-amber" : "border-sovereign-cyan";
        return `<div class="text-xs border-l-2 ${color} pl-2 py-1">
            <span class="text-gray-600">${escapeHtml(ts)}</span>
            <span class="text-gray-400 ml-1">${escapeHtml(String(msg).substring(0, 120))}</span>
        </div>`;
    }).join("");
}

// ─── SECURITY TAB ───────────────────────────────────

async function pollSecurity() {
    const [auditResp, rateResp, deepResp, taxResp, busResp] = await Promise.all([
        apiFetch("/api/v1/config/audit").catch(() => null),
        apiFetch("/api/v1/governor/rate-limits").catch(() => null),
        apiFetch("/api/v1/health/deep").catch(() => null),
        apiFetch("/api/v1/errors/taxonomy").catch(() => null),
        apiFetch("/api/v1/bus/stats").catch(() => null),
    ]);

    if (auditResp?.ok) renderConfigAudit(await auditResp.json());
    if (rateResp?.ok) renderRateLimits(await rateResp.json());
    if (deepResp?.ok) renderDeepHealth(await deepResp.json());
    if (taxResp?.ok) renderErrorTaxonomy(await taxResp.json());
    if (busResp?.ok) renderOmegaBusStats(await busResp.json());
}

function renderOmegaBusStats(d) {
    const set = (id, val, cls) => {
        const el = document.getElementById(id);
        if (!el) return;
        el.textContent = val;
        if (cls) el.className = `text-xs font-bold ${cls}`;
    };
    set("bus-seal-armed", d.omega_seal_armed ? "ARMED" : "DISARMED",
        d.omega_seal_armed ? "text-sovereign-green" : "text-sovereign-red");
    set("bus-hardware-bound", d.hardware_bound ? "SILICON SEAL" : "SOFTWARE-ONLY",
        d.hardware_bound ? "text-sovereign-green" : "text-sovereign-amber");
    set("bus-c2-verified", d.c2_verified ? "VERIFIED" : "UNVERIFIED",
        d.c2_verified ? "text-sovereign-green" : "text-sovereign-red");
    set("bus-events-pub", d.events_gepubliceerd ?? 0, "text-sovereign-accent");
    set("bus-seals-ok", d.seals_verified ?? 0, "text-sovereign-green");
    set("bus-seals-fail", d.seals_rejected ?? 0,
        (d.seals_rejected ?? 0) > 0 ? "text-sovereign-red" : "text-sovereign-green");
    set("bus-chains", d.active_chains ?? 0, "text-sovereign-accent");
    set("bus-chains-blocked", d.chains_blocked ?? 0,
        (d.chains_blocked ?? 0) > 0 ? "text-sovereign-amber" : "text-sovereign-green");
}

async function pollConfigAudit() {
    try {
        const resp = await apiFetch("/api/v1/config/audit");
        if (!resp.ok) return;
        const data = await resp.json();
        renderConfigAudit(data);
    } catch { /* non-critical */ }
}

function renderConfigAudit(data) {
    const container = document.getElementById("config-audit");
    if (!container) return;
    const checks = data.checks || data.results || data.audit || [];
    if (Array.isArray(checks) && checks.length > 0) {
        container.innerHTML = checks.map(c => {
            const ok = c.passed ?? c.ok ?? true;
            const cls = ok ? "audit-ok" : (c.severity === "warning" ? "audit-warn" : "audit-fail");
            const icon = ok ? "✓" : "✗";
            const color = ok ? "text-sovereign-green" : "text-sovereign-red";
            return `<div class="bg-sovereign-bg rounded p-2 ${cls}">
                <div class="flex items-center gap-2 text-xs">
                    <span class="${color} font-bold">${icon}</span>
                    <span class="text-gray-300">${escapeHtml(c.name || c.check || "check")}</span>
                </div>
                ${c.detail ? `<div class="text-xs text-gray-600 mt-1 pl-4">${escapeHtml(c.detail)}</div>` : ""}
            </div>`;
        }).join("");
    } else if (typeof data === "object") {
        let html = "";
        for (const [key, val] of Object.entries(data)) {
            if (key === "status") continue;
            const isOk = val === true || val === "ok" || val === "passed";
            const cls = isOk ? "audit-ok" : "audit-warn";
            html += `<div class="bg-sovereign-bg rounded p-2 ${cls}">
                <div class="flex justify-between text-xs">
                    <span class="text-gray-300">${escapeHtml(key)}</span>
                    <span class="${isOk ? 'text-sovereign-green' : 'text-sovereign-amber'} font-bold">${escapeHtml(String(val))}</span>
                </div>
            </div>`;
        }
        container.innerHTML = html || '<div class="text-xs text-gray-600">No audit data</div>';
    }
}

// ─── OVERVIEW: OUROBOROS + ERRORS ───────────────────

function updateOuroboros(data) {
    const setEl = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
    const status = data.status || data.state || "unknown";
    setEl("ouro-status", status.toUpperCase());
    const statusEl = document.getElementById("ouro-status");
    if (statusEl) {
        statusEl.className = `stat-value ${status === "healthy" || status === "running" ? "text-sovereign-green" : "text-sovereign-amber"}`;
    }
    setEl("ouro-cycles", data.total_cycles ?? data.cycles ?? "--");
}

function renderRecentErrors(data) {
    const container = document.getElementById("recent-errors");
    if (!container) return;
    const errors = Array.isArray(data) ? data : (data.errors || data.recent || []);
    if (errors.length === 0) {
        container.innerHTML = '<div class="text-xs text-sovereign-green">No recent errors</div>';
        return;
    }
    container.innerHTML = errors.slice(0, 5).map(e => {
        const msg = e.message || e.error || e.detail || JSON.stringify(e);
        const ts = e.timestamp || e.time || "";
        return `<div class="text-xs border-l-2 border-sovereign-red pl-2 py-0.5">
            <span class="text-gray-600">${escapeHtml(ts)}</span>
            <span class="text-gray-400 ml-1">${escapeHtml(String(msg).substring(0, 80))}</span>
        </div>`;
    }).join("");
}

// ─── OBSERVATORY: REGISTRY + AUCTIONS + SHARDS ─────

function renderModelRegistry(data) {
    const container = document.getElementById("model-registry");
    if (!container) return;
    const models = data.models || data || [];
    if (!Array.isArray(models) || models.length === 0) {
        container.innerHTML = '<div class="text-xs text-gray-600">No models registered</div>';
        return;
    }
    container.innerHTML = models.map(m => {
        const name = m.model || m.name || "unknown";
        const provider = m.provider || "?";
        const status = (m.status || "unknown").toLowerCase();
        const dotColor = status === "available" || status === "online" ? "bg-sovereign-green" :
                        status === "offline" ? "bg-sovereign-red" : "bg-sovereign-amber";
        return `<div class="flex items-center justify-between text-xs py-1 border-b border-sovereign-border/30">
            <span class="flex items-center gap-1.5">
                <span class="w-1.5 h-1.5 rounded-full ${dotColor}"></span>
                <span class="text-gray-300">${escapeHtml(name)}</span>
            </span>
            <span class="text-gray-500">${escapeHtml(provider)}</span>
        </div>`;
    }).join("");
}

function renderAuctionLogs(data) {
    const container = document.getElementById("auction-logs");
    if (!container) return;
    const auctions = Array.isArray(data) ? data : (data.auctions || data.logs || []);
    if (auctions.length === 0) {
        container.innerHTML = '<div class="text-xs text-gray-600">No auction data</div>';
        return;
    }
    container.innerHTML = auctions.slice(0, 20).map(a => {
        const winner = a.winner || a.model || "?";
        const task = a.task_type || a.task || "";
        const ts = a.timestamp || "";
        const bid = a.bid ?? a.score ?? "";
        return `<div class="text-xs border-l-2 border-sovereign-amber pl-2 py-0.5">
            <div class="flex justify-between">
                <span class="text-sovereign-cyan font-bold">${escapeHtml(winner)}</span>
                <span class="text-gray-600">${escapeHtml(ts)}</span>
            </div>
            <span class="text-gray-500">${escapeHtml(task)}${bid ? ` — bid: ${bid}` : ""}</span>
        </div>`;
    }).join("");
}

function renderShardStats(data) {
    const container = document.getElementById("shard-stats");
    if (!container) return;
    const shards = Array.isArray(data) ? data : (data.shards || []);
    if (shards.length === 0) {
        container.innerHTML = '<div class="text-xs text-gray-600">No shard data</div>';
        return;
    }
    container.innerHTML = shards.map(s => {
        const name = s.name || s.collection || "unknown";
        const count = s.count ?? s.documents ?? 0;
        const size = s.size_mb != null ? `${s.size_mb.toFixed(1)} MB` : "";
        return `<div class="stat-box p-2">
            <div class="flex justify-between items-center">
                <span class="stat-label">${escapeHtml(name)}</span>
                <span class="text-sm font-bold text-sovereign-glow">${count.toLocaleString()}</span>
            </div>
            ${size ? `<div class="text-xs text-gray-600 mt-1">${size}</div>` : ""}
        </div>`;
    }).join("");
}

// ─── MEMORY: TRACES + KNOWLEDGE SEARCH ──────────────

function renderTraces(data) {
    const container = document.getElementById("trace-list");
    if (!container) return;
    const traces = Array.isArray(data) ? data : (data.traces || []);
    if (traces.length === 0) {
        container.innerHTML = '<div class="text-xs text-gray-600">No traces recorded</div>';
        return;
    }
    container.innerHTML = traces.slice(0, 30).map(t => {
        const id = t.trace_id || t.id || "?";
        const ts = t.timestamp || t.start_time || "";
        const dur = t.duration_ms != null ? `${t.duration_ms}ms` : (t.duration != null ? `${(t.duration * 1000).toFixed(0)}ms` : "");
        const status = (t.status || "").toLowerCase();
        const color = status === "ok" || status === "success" ? "border-sovereign-green" :
                     status === "error" || status === "failed" ? "border-sovereign-red" : "border-sovereign-cyan";
        return `<div class="text-xs border-l-2 ${color} pl-2 py-1">
            <div class="flex justify-between">
                <span class="text-sovereign-cyan font-mono">${escapeHtml(id.substring(0, 12))}</span>
                <span class="text-gray-500">${escapeHtml(dur)}</span>
            </div>
            <span class="text-gray-600">${escapeHtml(ts)}</span>
        </div>`;
    }).join("");
}

async function searchKnowledge() {
    const input = document.getElementById("knowledge-input");
    const query = input.value.trim();
    if (!query) return;
    const container = document.getElementById("knowledge-results");
    container.innerHTML = '<div class="text-xs text-gray-500">Searching...</div>';

    try {
        const resp = await apiFetch(`/api/v1/knowledge/search?q=${encodeURIComponent(query)}&top_k=10`);
        if (!resp.ok) {
            container.innerHTML = '<div class="text-xs text-sovereign-red">Search failed</div>';
            return;
        }
        const data = await resp.json();
        const results = data.results || data.matches || data || [];
        if (!Array.isArray(results) || results.length === 0) {
            container.innerHTML = '<div class="text-xs text-gray-600">Geen resultaten gevonden</div>';
            return;
        }
        container.innerHTML = results.map(r => {
            const title = r.title || r.id || "document";
            const snippet = r.text || r.content || r.snippet || "";
            const score = r.score != null ? `${(r.score * 100).toFixed(1)}%` : "";
            return `<div class="bg-sovereign-bg rounded p-2 border-l-2 border-sovereign-green">
                <div class="flex justify-between text-xs">
                    <span class="text-sovereign-green font-bold">${escapeHtml(title)}</span>
                    ${score ? `<span class="text-gray-500">${score}</span>` : ""}
                </div>
                <div class="text-xs text-gray-400 mt-1">${escapeHtml(snippet.substring(0, 200))}</div>
            </div>`;
        }).join("");
    } catch {
        container.innerHTML = '<div class="text-xs text-sovereign-red">Network error</div>';
    }
}

// ─── SECURITY: RATE LIMITS + DEEP HEALTH + TAXONOMY ─

function renderRateLimits(data) {
    const container = document.getElementById("rate-limits");
    if (!container) return;
    const limits = data.limits || data.agents || data || {};
    if (typeof limits === "object" && !Array.isArray(limits)) {
        let html = "";
        for (const [agent, info] of Object.entries(limits)) {
            const used = info.used ?? info.tokens_used ?? 0;
            const max = info.max ?? info.limit ?? info.budget ?? 0;
            const pct = max > 0 ? (used / max * 100) : 0;
            const color = pct > 90 ? "bg-sovereign-red" : pct > 60 ? "bg-sovereign-amber" : "bg-sovereign-green";
            html += `<div class="text-xs py-1">
                <div class="flex justify-between mb-0.5">
                    <span class="text-gray-300">${escapeHtml(agent)}</span>
                    <span class="text-gray-500">${used.toLocaleString()} / ${max.toLocaleString()}</span>
                </div>
                <div class="w-full h-1.5 bg-gray-800 rounded overflow-hidden">
                    <div class="${color} h-full rounded transition-all" style="width:${Math.min(pct, 100).toFixed(1)}%"></div>
                </div>
            </div>`;
        }
        container.innerHTML = html || '<div class="text-xs text-gray-600">No rate limit data</div>';
    } else if (Array.isArray(limits)) {
        container.innerHTML = limits.map(l => {
            const name = l.agent || l.name || "?";
            const used = l.used ?? l.tokens_used ?? 0;
            const max = l.limit ?? l.budget ?? 0;
            return `<div class="flex justify-between text-xs py-0.5">
                <span class="text-gray-300">${escapeHtml(name)}</span>
                <span class="text-gray-500">${used} / ${max}</span>
            </div>`;
        }).join("");
    }
}

function renderDeepHealth(data) {
    const container = document.getElementById("deep-health");
    if (!container) return;
    const subsystems = data.subsystems || data.checks || data.systems || {};
    let html = "";

    if (typeof subsystems === "object" && !Array.isArray(subsystems)) {
        for (const [name, info] of Object.entries(subsystems)) {
            const ok = info === true || info === "ok" || info?.status === "ok" || info?.healthy === true;
            const icon = ok ? "✓" : "✗";
            const color = ok ? "text-sovereign-green" : "text-sovereign-red";
            const detail = typeof info === "object" ? (info.detail || info.message || "") : "";
            html += `<div class="flex items-center gap-2 text-xs py-0.5">
                <span class="${color} font-bold">${icon}</span>
                <span class="text-gray-300 flex-1">${escapeHtml(name)}</span>
                ${detail ? `<span class="text-gray-600 truncate max-w-[120px]">${escapeHtml(detail)}</span>` : ""}
            </div>`;
        }
    }

    // Also render top-level status fields
    for (const key of ["status", "version", "uptime_seconds", "pid"]) {
        if (data[key] !== undefined && key !== "subsystems") {
            html += `<div class="flex justify-between text-xs py-0.5">
                <span class="text-gray-500">${escapeHtml(key)}</span>
                <span class="text-gray-300">${escapeHtml(String(data[key]))}</span>
            </div>`;
        }
    }

    container.innerHTML = html || '<div class="text-xs text-gray-600">No deep health data</div>';
}

function renderErrorTaxonomy(data) {
    const container = document.getElementById("error-taxonomy");
    if (!container) return;
    const errors = Array.isArray(data) ? data : (data.taxonomy || data.errors || []);
    if (errors.length === 0) {
        container.innerHTML = '<div class="text-xs text-sovereign-green">No error patterns defined</div>';
        return;
    }
    container.innerHTML = errors.map(e => {
        const code = e.code || e.id || "?";
        const name = e.name || e.label || "";
        const severity = (e.severity || "info").toLowerCase();
        const count = e.count ?? e.occurrences ?? 0;
        const color = severity === "critical" ? "text-sovereign-red" :
                     severity === "warning" ? "text-sovereign-amber" : "text-gray-400";
        return `<div class="flex items-center justify-between text-xs py-0.5 border-b border-sovereign-border/20">
            <span class="flex items-center gap-1.5">
                <span class="${color} font-bold">${escapeHtml(code)}</span>
                <span class="text-gray-400">${escapeHtml(name)}</span>
            </span>
            <span class="text-gray-500">${count}</span>
        </div>`;
    }).join("");
}


// ═══════════════════════════════════════════════════════
//  TAB: OMEGA BRAIN
// ═══════════════════════════════════════════════════════

async function pollBrain() {
    try {
        const [agentsResp, singResp, cortexResp, twinResp] = await Promise.all([
            apiFetch("/api/v1/brain/agents/detail").catch(() => null),
            apiFetch("/api/v1/brain/singularity/state").catch(() => null),
            apiFetch("/api/v1/brain/cortex/graph").catch(() => null),
            apiFetch("/api/v1/brain/virtual-twin/status").catch(() => null),
        ]);
        if (agentsResp?.ok) renderBrainAgents(await agentsResp.json());
        if (singResp?.ok) renderConsciousness(await singResp.json());
        if (cortexResp?.ok) renderCortexGraph(await cortexResp.json());
        if (twinResp?.ok) renderVirtualTwin(await twinResp.json());
    } catch { /* non-critical */ }
}

function renderBrainAgents(data) {
    const grid = document.getElementById("brain-agent-grid");
    if (!grid || !data.agents) return;
    grid.innerHTML = data.agents.map(a => {
        const isActive = a.status === "ACTIVE" || a.status === "active";
        const glow = isActive ? "agent-card-active" : "agent-card-idle";
        const weight = a.synaptic_weight !== undefined ? a.synaptic_weight : 0;
        const weightPct = Math.min(100, Math.max(0, weight * 100));
        return `<div class="agent-card ${glow}">
            <div class="flex justify-between items-center mb-1">
                <span class="text-xs font-bold text-gray-200">${a.name}</span>
                <span class="agent-badge" style="background:${isActive ? '#22c55e20' : '#37415120'};color:${isActive ? '#22c55e' : '#6b7280'}">${a.status}</span>
            </div>
            <div class="text-xs text-gray-500 mb-1">${a.tier || ''} · ${a.role || ''}</div>
            <div class="flex justify-between text-xs mb-1">
                <span class="text-gray-500">SP: ${weight.toFixed(3)}</span>
                <span class="text-gray-500">Tasks: ${a.tasks_completed || 0}</span>
            </div>
            <div class="w-full bg-sovereign-bg rounded-full h-1.5">
                <div class="h-1.5 rounded-full bg-sovereign-accent" style="width:${weightPct}%"></div>
            </div>
        </div>`;
    }).join("");
}

const CONSCIOUSNESS_GLOWS = {
    SLAAP: "mode-slaap", WAAK: "mode-waak", DROOM: "mode-droom",
    FOCUS: "mode-focus", TRANSCEND: "mode-transcend"
};

function renderConsciousness(data) {
    const el = document.getElementById("consciousness-mode");
    if (el) {
        el.textContent = data.modus || "--";
        el.className = `text-3xl font-bold mb-2 ${CONSCIOUSNESS_GLOWS[data.modus] || "text-sovereign-glow"}`;
    }
    setText("consciousness-score", data.bewustzijn_score?.toFixed(2) || "--");
    setText("consciousness-dreams", data.dromen_count || 0);
    setText("consciousness-insights", data.inzichten_count || 0);
    if (data.modus_sinds) {
        const d = new Date(data.modus_sinds * 1000);
        setText("consciousness-since", d.toLocaleTimeString());
    }
}

function renderCortexGraph(data) {
    setText("cortex-nodes", data.nodes ?? "--");
    setText("cortex-edges", data.edges ?? "--");
    setText("cortex-density", data.density?.toFixed(4) ?? "--");
    setText("cortex-components", data.components ?? "--");
}

function renderVirtualTwin(data) {
    const statusEl = document.getElementById("twin-status");
    if (statusEl) {
        statusEl.textContent = data.twin_available ? "ONLINE" : "OFFLINE";
        statusEl.className = `stat-value ${data.twin_available ? "text-sovereign-green" : "text-sovereign-red"}`;
    }
    const zoneEl = document.getElementById("twin-zone");
    if (zoneEl) {
        const zone = data.shadow_zone || "unknown";
        const zoneColors = { RED: "text-sovereign-red", YELLOW: "text-sovereign-amber", GREEN: "text-sovereign-green" };
        zoneEl.textContent = zone.toUpperCase();
        zoneEl.className = `stat-value ${zoneColors[zone.toUpperCase()] || "text-gray-400"}`;
    }
    setText("twin-rules", data.rules_count ?? "--");
}

async function submitBrainGoal() {
    const input = document.getElementById("brain-goal-input");
    if (!input?.value.trim()) return;
    const resultDiv = document.getElementById("brain-goal-result");
    if (resultDiv) resultDiv.innerHTML = '<div class="text-xs text-sovereign-amber">Decomposing...</div>';
    try {
        const resp = await apiFetch("/api/v1/swarm/goal", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ goal: input.value.trim(), use_models: false }),
        });
        if (resp.ok) {
            const data = await resp.json();
            if (resultDiv) {
                resultDiv.innerHTML = data.taken.map(t =>
                    `<div class="cortical-event"><div class="event-type">${t.toegewezen_agent}</div><div class="event-summary">${t.beschrijving}</div><div class="text-xs text-gray-600">${t.status}</div></div>`
                ).join("") + `<div class="text-xs text-sovereign-green mt-2">${data.synthese || ''}</div>`;
            }
        }
    } catch { if (resultDiv) resultDiv.innerHTML = '<div class="text-xs text-sovereign-red">Goal execution mislukt</div>'; }
    input.value = "";
}

async function searchCortex() {
    const input = document.getElementById("cortex-search-input");
    if (!input?.value.trim()) return;
    const results = document.getElementById("cortex-search-results");
    try {
        const resp = await apiFetch("/api/v1/brain/cortex/query", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query: input.value.trim(), top_k: 5 }),
        });
        if (resp.ok) {
            const data = await resp.json();
            if (results) {
                const items = data.results || [];
                results.innerHTML = items.length
                    ? items.map(r => `<div class="text-xs p-2 bg-sovereign-bg rounded border-l-2 border-sovereign-cyan">${JSON.stringify(r).substring(0, 200)}</div>`).join("")
                    : '<div class="text-xs text-gray-600">Geen resultaten</div>';
            }
        }
    } catch { if (results) results.innerHTML = '<div class="text-xs text-sovereign-red">Query mislukt</div>'; }
}

// ═══════════════════════════════════════════════════════
//  TAB: SWARM COMMANDER
// ═══════════════════════════════════════════════════════

let swarmHistory = [];

async function pollSwarm() {
    try {
        const resp = await apiFetch("/api/v1/swarm/active");
        if (resp?.ok) {
            const data = await resp.json();
            // Active tasks are shown in task breakdown if any
        }
    } catch { /* non-critical */ }
}

async function submitSwarmGoal() {
    const input = document.getElementById("swarm-goal-input");
    if (!input?.value.trim()) return;
    const goal = input.value.trim();
    const useModels = document.getElementById("swarm-use-models")?.checked || false;

    // Show progress
    const progress = document.getElementById("swarm-progress");
    if (progress) { progress.classList.remove("hidden"); setSwarmStage("decompose"); }
    const tasksDiv = document.getElementById("swarm-tasks");
    const payloadsDiv = document.getElementById("swarm-payloads");
    if (tasksDiv) tasksDiv.innerHTML = '<div class="text-xs text-sovereign-amber">Decomposing goal...</div>';
    if (payloadsDiv) payloadsDiv.innerHTML = '<div class="text-xs text-gray-600">Wachten...</div>';

    try {
        setSwarmStage("auction");
        const resp = await apiFetch("/api/v1/swarm/goal", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ goal, use_models: useModels }),
        });
        if (resp.ok) {
            const data = await resp.json();
            setSwarmStage("execute");
            // Render tasks
            if (tasksDiv) {
                tasksDiv.innerHTML = data.taken.map(t => `
                    <div class="cortical-event">
                        <div class="flex justify-between">
                            <span class="event-type">${t.toegewezen_agent || "?"}</span>
                            <span class="text-xs ${t.status === 'voltooid' ? 'text-sovereign-green' : 'text-sovereign-amber'}">${t.status}</span>
                        </div>
                        <div class="event-summary">${t.beschrijving}</div>
                        ${t.resultaat_preview ? `<div class="text-xs text-gray-500 mt-1">${t.resultaat_preview.substring(0, 150)}</div>` : ""}
                    </div>
                `).join("") || '<div class="text-xs text-gray-600">Geen taken</div>';
            }
            // Render synthesis
            setSwarmStage("synthesize");
            if (payloadsDiv) {
                payloadsDiv.innerHTML = data.synthese
                    ? `<div class="agent-payload"><div class="text-sm text-gray-200">${data.synthese}</div><div class="text-xs text-gray-500 mt-1">${data.execution_time?.toFixed(2) || "?"}s · trace: ${data.trace_id || "?"}</div></div>`
                    : '<div class="text-xs text-gray-600">Geen synthese</div>';
            }
            // Add to history
            swarmHistory.unshift({ goal, status: data.status, time: data.execution_time, trace: data.trace_id, tasks: data.taken?.length || 0 });
            if (swarmHistory.length > 10) swarmHistory.pop();
            renderSwarmHistory();
        }
    } catch (e) {
        if (tasksDiv) tasksDiv.innerHTML = '<div class="text-xs text-sovereign-red">Execution mislukt</div>';
    }
    input.value = "";
    setTimeout(() => { if (progress) progress.classList.add("hidden"); }, 3000);
}

function setSwarmStage(active) {
    document.querySelectorAll(".swarm-stage").forEach(el => {
        el.classList.toggle("active", el.dataset.stage === active);
    });
}

function renderSwarmHistory() {
    const div = document.getElementById("swarm-history");
    if (!div) return;
    div.innerHTML = swarmHistory.map(h => `
        <div class="cortical-event">
            <div class="flex justify-between">
                <span class="event-summary">${h.goal.substring(0, 80)}</span>
                <span class="text-xs ${h.status === 'completed' ? 'text-sovereign-green' : 'text-sovereign-amber'}">${h.status}</span>
            </div>
            <div class="text-xs text-gray-600">${h.tasks} tasks · ${h.time?.toFixed(2) || "?"}s</div>
        </div>
    `).join("") || '<div class="text-xs text-gray-600">Geen eerdere goals</div>';
}

// ═══════════════════════════════════════════════════════
//  TAB: APPS HUB
// ═══════════════════════════════════════════════════════

let allApps = [];
let currentAppFilter = "all";
let selectedApp = null;
let selectedAction = null;

const CATEGORY_EMOJIS = {
    productiviteit: "\u{1F4CB}", ai: "\u{1F9E0}", gezondheid: "\u{2764}\u{FE0F}",
    financien: "\u{1F4B0}", creatief: "\u{1F3A8}", leren: "\u{1F4DA}",
    lifestyle: "\u{2B50}", systeem: "\u{2699}\u{FE0F}"
};

async function pollApps() {
    if (allApps.length > 0) return; // Only load once
    try {
        const resp = await apiFetch("/api/v1/apps/registry");
        if (resp?.ok) {
            allApps = await resp.json();
            renderAppGrid();
        }
    } catch { /* non-critical */ }
}

function filterApps(cat) {
    currentAppFilter = cat;
    document.querySelectorAll(".app-cat-btn").forEach(b => {
        b.classList.toggle("active", b.dataset.cat === cat);
    });
    renderAppGrid();
}

function renderAppGrid() {
    const grid = document.getElementById("app-grid");
    if (!grid) return;
    const filtered = currentAppFilter === "all" ? allApps : allApps.filter(a => a.categorie === currentAppFilter);
    grid.innerHTML = filtered.map(app => {
        const emoji = CATEGORY_EMOJIS[app.categorie] || "\u{1F4E6}";
        return `<div class="app-card" onclick="openAppModal('${app.id}')">
            <div class="text-2xl mb-2">${emoji}</div>
            <div class="text-xs font-bold text-gray-200 mb-1">${app.naam}</div>
            <div class="app-cat-badge">${app.categorie}</div>
            <div class="text-xs text-gray-500 mt-1 line-clamp-2">${app.beschrijving.substring(0, 60)}</div>
        </div>`;
    }).join("") || '<div class="text-xs text-gray-600 col-span-full text-center py-8">Geen apps in deze categorie</div>';
}

async function openAppModal(appId) {
    selectedApp = allApps.find(a => a.id === appId);
    if (!selectedApp) return;
    selectedAction = null;
    document.getElementById("app-modal-title").textContent = `${CATEGORY_EMOJIS[selectedApp.categorie] || ""} ${selectedApp.naam}`;
    document.getElementById("app-modal-desc").textContent = selectedApp.beschrijving;
    // Action buttons
    const actionsDiv = document.getElementById("app-modal-actions");
    actionsDiv.innerHTML = selectedApp.acties.map(a =>
        `<button class="app-action-btn" onclick="selectAppAction('${a.naam}')">${a.naam}</button>`
    ).join("");
    // Clear
    document.getElementById("app-modal-params").innerHTML = "";
    document.getElementById("app-modal-execute").classList.add("hidden");
    document.getElementById("app-modal-result").classList.add("hidden");
    // Load state
    try {
        const stateResp = await apiFetch(`/api/v1/apps/${appId}/state`);
        if (stateResp?.ok) {
            const stateData = await stateResp.json();
            const stateDiv = document.getElementById("app-modal-state");
            const stateText = document.getElementById("app-modal-state-text");
            if (stateData.state) {
                stateText.textContent = JSON.stringify(stateData.state, null, 2);
                stateDiv.classList.remove("hidden");
            } else {
                stateDiv.classList.add("hidden");
            }
        }
    } catch { /* no state */ }
    document.getElementById("app-modal-overlay").classList.remove("hidden");
}

function closeAppModal() {
    document.getElementById("app-modal-overlay").classList.add("hidden");
    selectedApp = null;
    selectedAction = null;
}

function selectAppAction(actionName) {
    if (!selectedApp) return;
    selectedAction = selectedApp.acties.find(a => a.naam === actionName);
    if (!selectedAction) return;
    // Highlight active button
    document.querySelectorAll(".app-action-btn").forEach(b => {
        b.classList.toggle("active", b.textContent === actionName);
    });
    // Generate parameter form
    const paramsDiv = document.getElementById("app-modal-params");
    const params = selectedAction.parameters || {};
    const keys = Object.keys(params);
    if (keys.length === 0) {
        paramsDiv.innerHTML = '<div class="text-xs text-gray-500">Geen parameters nodig</div>';
    } else {
        paramsDiv.innerHTML = keys.map(k => {
            const p = params[k];
            const type = p.type || "string";
            if (p.enum) {
                return `<div><label class="text-xs text-gray-500">${k}</label><select id="param-${k}" class="w-full bg-sovereign-bg border border-sovereign-border rounded px-3 py-1.5 text-xs text-gray-300">${p.enum.map(v => `<option value="${v}">${v}</option>`).join("")}</select></div>`;
            }
            return `<div><label class="text-xs text-gray-500">${k} (${type})</label><input id="param-${k}" type="${type === 'integer' || type === 'number' ? 'number' : 'text'}" placeholder="${p.description || k}" class="w-full bg-sovereign-bg border border-sovereign-border rounded px-3 py-1.5 text-xs text-gray-300 focus:border-sovereign-accent focus:outline-none"></div>`;
        }).join("");
    }
    document.getElementById("app-modal-execute").classList.remove("hidden");
    document.getElementById("app-modal-result").classList.add("hidden");
}

async function executeAppAction() {
    if (!selectedApp || !selectedAction) return;
    const params = {};
    for (const k of Object.keys(selectedAction.parameters || {})) {
        const el = document.getElementById(`param-${k}`);
        if (el) {
            const p = selectedAction.parameters[k];
            let val = el.value;
            if (p.type === "integer") val = parseInt(val) || 0;
            else if (p.type === "number") val = parseFloat(val) || 0;
            if (val !== "" && val !== 0) params[k] = val;
        }
    }
    const resultDiv = document.getElementById("app-modal-result");
    const resultText = document.getElementById("app-modal-result-text");
    resultDiv.classList.remove("hidden");
    resultText.textContent = "Executing...";
    try {
        const resp = await apiFetch(`/api/v1/apps/${selectedApp.id}/action`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action: selectedAction.naam, params }),
        });
        if (resp.ok) {
            const data = await resp.json();
            resultText.textContent = JSON.stringify(data.result, null, 2);
        } else {
            const err = await resp.json().catch(() => ({}));
            resultText.textContent = `Error: ${err.detail || resp.status}`;
        }
    } catch (e) {
        resultText.textContent = `Error: ${e.message}`;
    }
}

// ═══════════════════════════════════════════════════════
//  TAB: KNOWLEDGE FORGE
// ═══════════════════════════════════════════════════════

async function pollKnowledge() {
    try {
        const [shardsResp, pruneResp] = await Promise.all([
            apiFetch("/api/v1/knowledge/documents").catch(() => null),
            apiFetch("/api/v1/pruning/stats").catch(() => null),
        ]);
        if (shardsResp?.ok) renderKnowledgeShards(await shardsResp.json());
        if (pruneResp?.ok) renderPruningStats(await pruneResp.json());
    } catch { /* non-critical */ }
}

function renderKnowledgeShards(data) {
    const div = document.getElementById("kg-shards");
    if (!div || !data.collections) return;
    div.innerHTML = data.collections.map(c => `
        <div class="stat-box p-2">
            <div class="flex justify-between">
                <span class="text-xs font-bold text-gray-300">${c.name}</span>
                <span class="text-xs font-bold text-sovereign-cyan">${c.count.toLocaleString()}</span>
            </div>
        </div>
    `).join("") || '<div class="text-xs text-gray-600">Geen collecties</div>';
}

function renderPruningStats(data) {
    setText("kg-prune-tracked", data.totaal_gevolgd || 0);
    setText("kg-prune-entropy", data.entropy_drempel?.toFixed(2) || "--");
    setText("kg-prune-redundancy", data.redundantie_drempel?.toFixed(2) || "--");
    setText("kg-prune-decay", data.verval_dagen || "--");
}

async function searchKnowledgeForge() {
    const input = document.getElementById("kg-search-input");
    if (!input?.value.trim()) return;
    const query = input.value.trim();
    const includeWeb = document.getElementById("kg-include-web")?.checked || false;
    const results = document.getElementById("kg-search-results");
    if (results) results.innerHTML = `<div class="text-xs text-sovereign-amber">Searching${includeWeb ? " (lokaal + web)" : ""}...</div>`;

    if (includeWeb) {
        // Hybrid search: lokaal + online
        try {
            const resp = await apiFetch("/api/v1/knowledge/hybrid-search", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ query, n_results: 10, include_web: true }),
            });
            if (resp.ok) {
                const data = await resp.json();
                const docs = data.gecombineerd || [];
                if (results) {
                    results.innerHTML = docs.map(d => {
                        const score = d.score ?? 0;
                        const scorePct = Math.round(score * 100);
                        const text = d.tekst || "";
                        const highlighted = highlightSearch(text.substring(0, 400), query);
                        const isWeb = d.type === "web";
                        const borderColor = isWeb ? "border-sovereign-cyan" : "border-sovereign-accent";
                        const badge = isWeb
                            ? `<span class="text-xs px-1.5 py-0.5 rounded bg-sovereign-cyan/20 text-sovereign-cyan">WEB</span>`
                            : `<span class="text-xs px-1.5 py-0.5 rounded bg-sovereign-accent/20 text-sovereign-glow">LOKAAL</span>`;
                        const urlLink = d.url ? `<a href="${d.url}" target="_blank" class="text-xs text-sovereign-cyan hover:underline ml-2">${d.url.substring(0, 50)}...</a>` : "";
                        return `<div class="bg-sovereign-bg rounded p-3 border-l-2 ${borderColor}">
                            <div class="flex justify-between items-center mb-1">
                                <div class="flex items-center gap-2">
                                    ${badge}
                                    <span class="text-xs font-bold text-gray-300">${d.bron || "?"}</span>
                                    ${urlLink}
                                </div>
                                <span class="text-xs text-sovereign-cyan">${scorePct}%</span>
                            </div>
                            <div class="w-full bg-sovereign-border rounded-full h-1 mb-2">
                                <div class="h-1 rounded-full ${isWeb ? "bg-sovereign-cyan" : "bg-sovereign-accent"}" style="width:${scorePct}%"></div>
                            </div>
                            <div class="text-xs text-gray-400">${highlighted}</div>
                        </div>`;
                    }).join("") || '<div class="text-xs text-gray-600 text-center py-4">Geen resultaten</div>';
                    // Show totals
                    const lokaalCount = (data.lokaal || []).length;
                    const webCount = (data.web || []).length;
                    const summary = `<div class="text-xs text-gray-500 mt-2 text-center">${lokaalCount} lokaal · ${webCount} web${data.web_error ? ` · ⚠ ${data.web_error}` : ""}</div>`;
                    results.innerHTML += summary;
                }
            }
        } catch { if (results) results.innerHTML = '<div class="text-xs text-sovereign-red">Hybrid search mislukt</div>'; }
    } else {
        // Alleen lokaal
        try {
            const resp = await apiFetch(`/api/v1/knowledge/search?query=${encodeURIComponent(query)}&n_results=10`);
            if (resp.ok) {
                const data = await resp.json();
                const docs = data.resultaten || data.documenten || data.results || [];
                if (results) {
                    results.innerHTML = docs.map(d => {
                        const score = d.score ?? d.relevance ?? 0;
                        const scorePct = Math.round(score * 100);
                        const text = d.tekst || d.text || d.content || "";
                        const highlighted = highlightSearch(text.substring(0, 400), query);
                        return `<div class="bg-sovereign-bg rounded p-3 border-l-2 border-sovereign-accent">
                            <div class="flex justify-between mb-1">
                                <span class="text-xs font-bold text-gray-300">${d.bron || d.source || d.id || "doc"}</span>
                                <span class="text-xs text-sovereign-cyan">${scorePct}%</span>
                            </div>
                            <div class="w-full bg-sovereign-border rounded-full h-1 mb-2">
                                <div class="h-1 rounded-full bg-sovereign-accent" style="width:${scorePct}%"></div>
                            </div>
                            <div class="text-xs text-gray-400">${highlighted}</div>
                        </div>`;
                    }).join("") || '<div class="text-xs text-gray-600 text-center py-4">Geen resultaten</div>';
                }
            }
        } catch { if (results) results.innerHTML = '<div class="text-xs text-sovereign-red">Search mislukt</div>'; }
    }
}

function highlightSearch(text, query) {
    if (!query) return text;
    const words = query.split(/\s+/).filter(w => w.length > 2);
    let result = text;
    for (const w of words) {
        const re = new RegExp(`(${w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, "gi");
        result = result.replace(re, '<span class="search-highlight">$1</span>');
    }
    return result;
}

async function startBulkAssimilate() {
    const path = document.getElementById("kg-bulk-path")?.value?.trim();
    const tags = document.getElementById("kg-bulk-tags")?.value?.trim() || "";
    if (!path) return;
    const statusDiv = document.getElementById("kg-bulk-status");
    if (statusDiv) statusDiv.textContent = "Starting assimilation...";
    try {
        const resp = await apiFetch("/api/v1/assimilate/bulk", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ directory: path, tags, extensions: [".py", ".md"], batch_size: 15 }),
        });
        if (resp.ok) {
            const data = await resp.json();
            if (statusDiv) statusDiv.innerHTML = `<span class="text-sovereign-green">Job ${data.job_id} gestart</span>`;
            // Poll job status
            pollBulkJob(data.job_id);
        }
    } catch { if (statusDiv) statusDiv.innerHTML = '<span class="text-sovereign-red">Assimilatie mislukt</span>'; }
}

async function pollBulkJob(jobId) {
    const statusDiv = document.getElementById("kg-bulk-status");
    const check = async () => {
        try {
            const resp = await apiFetch(`/api/v1/assimilate/bulk/${jobId}`);
            if (resp.ok) {
                const data = await resp.json();
                if (statusDiv) statusDiv.innerHTML = `<span class="text-sovereign-cyan">${data.status}</span> — ${data.ok || 0} OK, ${data.failed || 0} failed, ${data.chunks || 0} chunks`;
                if (data.status !== "completed" && data.status !== "error") {
                    setTimeout(check, 2000);
                }
            }
        } catch { /* stop polling */ }
    };
    setTimeout(check, 2000);
}

async function previewPrune() {
    try {
        const resp = await apiFetch("/api/v1/pruning/preview", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ entropy_threshold: 0.3, redundancy_threshold: 0.95 }),
        });
        if (resp.ok) {
            const data = await resp.json();
            alert(`Pruning Preview:\nTracked: ${data.current_stats?.totaal_gevolgd || 0}\nEntropy: ${data.entropy_threshold}\nRedundancy: ${data.redundancy_threshold}`);
        }
    } catch { alert("Preview mislukt"); }
}

async function executePrune() {
    if (!confirm("Pruning uitvoeren? Dit verwijdert chunks permanent.")) return;
    try {
        const resp = await apiFetch("/api/v1/pruning/run", { method: "POST" });
        if (resp.ok) {
            const data = await resp.json();
            alert(`Pruning voltooid: ${JSON.stringify(data)}`);
            pollKnowledge();
        }
    } catch { alert("Pruning mislukt"); }
}

// ═══════════════════════════════════════════════════════
//  TAB: DAEMON & DREAMS
// ═══════════════════════════════════════════════════════

const MOOD_EMOJIS = {
    ECSTATIC: "\u{1F929}", HAPPY: "\u{1F604}", CONTENT: "\u{1F60A}",
    NEUTRAL: "\u{1F610}", BORED: "\u{1F971}", TIRED: "\u{1F634}",
    SAD: "\u{1F622}", ANXIOUS: "\u{1F630}", SICK: "\u{1F922}"
};

const FORM_CLASSES = {
    FOCUS: "avatar-focus", CREATIVE: "avatar-creative",
    DREAMING: "avatar-dreaming", GUARDIAN: "avatar-guardian",
    GLITCH: "avatar-glitch", OVERHEATED: "avatar-overheated",
    ZOMBIE: "avatar-zombie"
};

async function pollDaemon() {
    try {
        // Use single /daemon/status call — contains limbic + metabolisme + sensorium
        const resp = await apiFetch("/api/v1/daemon/status");
        if (!resp?.ok) return;
        const d = resp.json ? await resp.json() : {};

        // Emotional state from limbic sub-object
        if (d.limbic) {
            const lState = d.limbic.state || {};
            const lScores = d.limbic.scores || {};
            renderEmotionalState({
                state: lState,
                mood: lState.mood,
                form: d.avatar_form || lState.form,
                energy: lState.energy,
                scores: { happiness: lState.happiness, stress: lState.stress, curiosity: lState.curiosity, pride: lState.pride, ...lScores },
            });
        }

        // Metabolism from metabolisme sub-object
        if (d.metabolisme) {
            renderMetabolism({
                state: d.metabolisme.state,
                nutrients: d.metabolisme.nutrients,
                hunger: d.metabolisme.hunger,
                total: d.metabolisme.total,
            });
        }

        // Coherence — use cached metrics instead of slow scan
        const metricsResp = await apiFetch("/api/v1/metrics").catch(() => null);
        if (metricsResp?.ok) {
            const m = await metricsResp.json();
            renderCoherence({ cpu_gem: m.cpu_percent || 0, gpu_gem: 0, correlatie: 0, verdict: "PASS" });
        }

        // Dreams + heartbeats (fast CorticalStack queries)
        const [dreamResp, hbResp] = await Promise.all([
            apiFetch("/api/v1/daemon/dreams").catch(() => null),
            apiFetch("/api/v1/daemon/heartbeat/history").catch(() => null),
        ]);
        if (dreamResp?.ok) renderDreams(await dreamResp.json());
        if (hbResp?.ok) renderHeartbeats(await hbResp.json());
    } catch { /* non-critical */ }
}

function renderEmotionalState(data) {
    const state = data.state || data;
    const mood = state.mood || data.mood || "NEUTRAL";
    const form = state.form || data.form || "FOCUS";
    const energy = state.energy || data.energy || "NORMAL";

    // Update avatar
    const avatar = document.getElementById("daemon-avatar");
    if (avatar) {
        avatar.className = `${FORM_CLASSES[form] || "avatar-focus"} w-24 h-24 mx-auto rounded-full flex items-center justify-center text-4xl mb-3`;
    }
    setText("daemon-mood-text", `${MOOD_EMOJIS[mood] || ""} ${mood}`);
    setText("daemon-form-text", `${form} · Energy: ${energy}`);

    // Emotion bars
    const emotionsDiv = document.getElementById("daemon-emotions");
    if (emotionsDiv) {
        const scores = data.scores || state;
        const dims = [
            { name: "Happiness", val: scores.happiness ?? 0.5, color: "#22c55e" },
            { name: "Stress", val: scores.stress ?? 0.3, color: "#ef4444" },
            { name: "Curiosity", val: scores.curiosity ?? 0.5, color: "#06b6d4" },
            { name: "Pride", val: scores.pride ?? 0.5, color: "#f59e0b" },
        ];
        emotionsDiv.innerHTML = dims.map(d => `
            <div>
                <div class="flex justify-between text-xs mb-0.5">
                    <span class="text-gray-400">${d.name}</span>
                    <span style="color:${d.color}">${(d.val * 100).toFixed(0)}%</span>
                </div>
                <div class="w-full bg-sovereign-bg rounded-full h-2">
                    <div class="h-2 rounded-full" style="width:${d.val * 100}%;background:${d.color}"></div>
                </div>
            </div>
        `).join("");
    }
}

function renderMetabolism(data) {
    const div = document.getElementById("daemon-metabolism");
    if (!div) return;
    const nutrients = data.nutrients || {};
    const items = [
        { name: "Protein", val: nutrients.protein ?? 50, color: "#ef4444" },
        { name: "Carbs", val: nutrients.carbs ?? 50, color: "#f59e0b" },
        { name: "Vitamins", val: nutrients.vitamins ?? 50, color: "#22c55e" },
        { name: "Water", val: nutrients.water ?? 50, color: "#06b6d4" },
        { name: "Fiber", val: nutrients.fiber ?? 50, color: "#a78bfa" },
    ];
    div.innerHTML = `<div class="text-xs text-center font-bold mb-2 ${data.state === 'THRIVING' ? 'text-sovereign-green' : 'text-gray-400'}">${data.state || '--'}</div>` +
        items.map(n => `
            <div>
                <div class="flex justify-between text-xs mb-0.5">
                    <span class="text-gray-400">${n.name}</span>
                    <span style="color:${n.color}">${n.val.toFixed(0)}</span>
                </div>
                <div class="w-full bg-sovereign-bg rounded-full h-1.5">
                    <div class="nutrient-bar h-1.5 rounded-full" style="width:${n.val}%;background:${n.color}"></div>
                </div>
            </div>
        `).join("");
}

function renderCoherence(data) {
    setText("coherence-cpu", data.cpu_gem !== undefined ? `${data.cpu_gem.toFixed(1)}%` : "--");
    setText("coherence-gpu", data.gpu_gem !== undefined ? `${data.gpu_gem.toFixed(1)}%` : "--");
    setText("coherence-corr", data.correlatie !== undefined ? data.correlatie.toFixed(3) : "--");
    const verdictEl = document.getElementById("coherence-verdict");
    if (verdictEl) {
        verdictEl.textContent = data.verdict || "--";
        const colors = { PASS: "text-sovereign-green", WAARSCHUWING: "text-sovereign-amber", ALARM: "text-sovereign-red" };
        verdictEl.className = `stat-value ${colors[data.verdict] || "text-gray-400"}`;
    }
}

function renderDreams(data) {
    const div = document.getElementById("daemon-dreams");
    if (!div) return;
    const dreams = data.dreams || [];
    div.innerHTML = dreams.length
        ? dreams.map(d => `<div class="cortical-event"><div class="event-type">${d.action || "dream"}</div><div class="event-summary">${d.summary || JSON.stringify(d).substring(0, 120)}</div></div>`).join("")
        : '<div class="text-xs text-gray-600">Geen dromen gevonden</div>';
}

function renderHeartbeats(data) {
    const div = document.getElementById("daemon-heartbeats");
    if (!div) return;
    const beats = data.heartbeats || [];
    div.innerHTML = beats.length
        ? beats.map(b => `<div class="text-xs border-l-2 border-sovereign-red pl-2 mb-1"><span class="text-gray-500">${b.timestamp || ""}</span> ${b.action || b.summary || ""}</div>`).join("")
        : '<div class="text-xs text-gray-600">Geen heartbeats</div>';
}

async function triggerDream() {
    if (!confirm("Manual REM dream cycle starten?")) return;
    const div = document.getElementById("daemon-dreams");
    if (div) div.innerHTML = '<div class="text-xs text-sovereign-amber">Dreaming...</div>';
    try {
        const resp = await apiFetch("/api/v1/daemon/dream/trigger", { method: "POST" });
        if (resp.ok) {
            const data = await resp.json();
            if (div) div.innerHTML = `<div class="text-xs text-sovereign-green">${data.message || "Dream cycle voltooid"}</div>`;
            setTimeout(() => pollDaemon(), 1000);
        }
    } catch { if (div) div.innerHTML = '<div class="text-xs text-sovereign-red">Dream trigger mislukt</div>'; }
}

// ═══════════════════════════════════════════════════════
//  UTILITY: setText helper
// ═══════════════════════════════════════════════════════

function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
}
