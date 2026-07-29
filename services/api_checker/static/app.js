const $ = (selector) => document.querySelector(selector);
const modelList = $("#modelList");
const startButton = $("#startButton");
let selectedModel = "";
let algorithm = "quick";

const probeLabels = {
  models: "模型列表一致性",
  liveness: "基础聊天可用性",
  identity: "模型身份一致性",
  token_delta: "隐藏 Prompt 注入",
  echo_rewrite: "输出与命令改写",
  stream_integrity: "流式响应完整性",
  context_canary: "长上下文截断",
};

function toast(message) {
  const el = $("#toast");
  el.textContent = message;
  el.classList.add("show");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => el.classList.remove("show"), 3500);
}

function setBadge(text, state) {
  const badge = $("#resultBadge");
  badge.textContent = text;
  badge.className = `result-badge ${state}`;
}

async function loadModels() {
  try {
    const response = await fetch("/api/v1/relay/models");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const payload = await response.json();
    const models = payload.data?.models || [];
    $("#modelCount").textContent = `${models.length} 个指纹基准模型`;
    modelList.innerHTML = models.map((model, index) => `
      <button class="model-card ${index === 0 ? "active" : ""}" type="button"
              data-model="${escapeHtml(model.id)}" role="radio"
              aria-checked="${index === 0}">
        <strong>${escapeHtml(model.name)}</strong>
        <small>${escapeHtml(model.id)}</small><i>✓</i>
      </button>`).join("");
    selectedModel = models[0]?.id || "";
    $("#modelInput").value = selectedModel;
  } catch (error) {
    $("#modelCount").textContent = "模型列表读取失败";
    toast(`无法读取模型列表：${error.message}`);
  }
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, char => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[char]);
}

modelList.addEventListener("click", event => {
  const card = event.target.closest(".model-card");
  if (!card) return;
  modelList.querySelectorAll(".model-card").forEach(item => {
    item.classList.toggle("active", item === card);
    item.setAttribute("aria-checked", String(item === card));
  });
  selectedModel = card.dataset.model;
  $("#modelInput").value = selectedModel;
});

$("#modelInput").addEventListener("input", event => {
  selectedModel = event.target.value.trim();
  modelList.querySelectorAll(".model-card").forEach(item => {
    const selected = item.dataset.model === selectedModel;
    item.classList.toggle("active", selected);
    item.setAttribute("aria-checked", String(selected));
  });
});

document.querySelectorAll(".mode").forEach(button => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".mode").forEach(item => item.classList.remove("active"));
    button.classList.add("active");
    algorithm = button.dataset.mode;
  });
});

$("#toggleKey").addEventListener("click", () => {
  const input = $("#apiKey");
  const show = input.type === "password";
  input.type = show ? "text" : "password";
  $("#toggleKey").textContent = show ? "隐藏" : "显示";
});

function keyFingerprint(value) {
  let hash = 2166136261;
  for (let i = 0; i < value.length; i += 1) {
    hash ^= value.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}

function cacheKey(baseUrl, model, apiKey) {
  return `aig-result:${algorithm}:${baseUrl}:${model}:${keyFingerprint(apiKey)}`;
}

function showRunning() {
  $("#emptyState").classList.remove("hidden");
  $("#resultContent").classList.add("hidden");
  $("#emptyState h3").textContent = "正在执行安全探针";
  $("#emptyState p").textContent = algorithm === "full"
    ? "正在采集模型指纹，这可能需要几分钟…"
    : "正在检查模型、响应改写、流式完整性和上下文…";
  setBadge("检测进行中", "running");
  startButton.disabled = true;
  startButton.querySelector("span").textContent = "检测中…";
}

function finishButton() {
  startButton.disabled = false;
  startButton.querySelector("span").textContent = "开始检测";
}

function renderResult(result, cached = false) {
  const findings = result.detail?.findings || [];
  const partialErrors = result.partial_errors || {};
  const signature = result.detail?.signature;
  const hasSignature = Boolean(signature?.verdict);
  const signatureOk = !hasSignature || signature.verdict === "native";
  let score = Number(result.score || 0);
  if (hasSignature && !signatureOk) score = Math.min(score, Number(signature.score || 0));
  const safe = result.overall_verdict === "pass";
  const inconclusive = result.overall_verdict === "inconclusive";

  $("#emptyState").classList.add("hidden");
  $("#resultContent").classList.remove("hidden");
  $("#scoreValue").textContent = Math.round(score);
  $("#scoreRing").style.setProperty("--score", score);
  $("#scoreRing").style.setProperty("--ring-color",
    safe ? "var(--green)" : (inconclusive ? "var(--orange)" : "var(--red)"));
  $("#testedModel").textContent = selectedModel;
  $("#scoreCaption").textContent = cached ? "10 分钟缓存结果" : "本次综合检测评分";
  $("#resultSummary").textContent = result.summary || "检测完成";

  const items = findings.map(finding => ({
    name: probeLabels[finding.probe] || finding.probe || "审计发现",
    ok: false,
    meta: finding.title || finding.severity || "发现风险",
  }));
  if (!findings.length && !partialErrors.audit) {
    items.push({
      name: "黑盒审计",
      ok: true,
      meta: "未发现风险",
    });
  }
  Object.entries(partialErrors).forEach(([component, message]) => items.push({
    name: `${component} 子检查`,
    ok: false,
    meta: message || "检查未完成",
  }));
  if (hasSignature) {
    items.unshift({
      name: "Claude Thinking Signature",
      ok: signatureOk,
      meta: `${Math.round(signature.score || 0)} 分 · ${signature.verdict === "native" ? "原生签名" : "签名异常"}`,
    });
  }
  $("#checkList").innerHTML = items.map(item => `
    <div class="check-item">
      <span class="check-icon ${item.ok ? "ok" : "fail"}">${item.ok ? "✓" : "×"}</span>
      <div><div>${escapeHtml(item.name)}</div><div class="check-meta">${escapeHtml(item.meta)}</div></div>
      <span class="check-state ${item.ok ? "ok" : "fail"}">${item.ok ? "通过" : "异常"}</span>
    </div>`).join("");

  setBadge(
    safe ? "检测通过" : (inconclusive ? "检查不完整" : "发现异常"),
    safe ? "success" : "danger",
  );
}

function parseSseChunk(buffer, onEvent) {
  const blocks = buffer.split("\n\n");
  const remainder = blocks.pop();
  for (const block of blocks) {
    let event = "message";
    let data = "";
    for (const line of block.split("\n")) {
      if (line.startsWith("event:")) event = line.slice(6).trim();
      if (line.startsWith("data:")) data += line.slice(5).trim();
    }
    if (data) onEvent(event, JSON.parse(data));
  }
  return remainder;
}

async function runDetection() {
  const baseUrl = $("#baseUrl").value.trim().replace(/\/+$/, "");
  const apiKey = $("#apiKey").value.trim();
  if (!/^https?:\/\//.test(baseUrl)) return toast("请输入以 http:// 或 https:// 开头的接口地址");
  if (!apiKey) return toast("请输入 API Key");
  if (!selectedModel) return toast("请选择目标模型");

  const key = cacheKey(baseUrl, selectedModel, apiKey);
  if ($("#useCache").checked) {
    try {
      const cached = JSON.parse(sessionStorage.getItem(key));
      if (cached && Date.now() - cached.time < 600000) {
        renderResult(cached.result, true);
        return;
      }
    } catch (_) { sessionStorage.removeItem(key); }
  }

  showRunning();
  try {
    const response = await fetch("/api/v1/relay/check/stream", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        algorithm,
        base_url: baseUrl,
        api_key: apiKey,
        model: selectedModel,
        iterations: 200,
        no_think: true,
      }),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let finalResult = null;
    while (true) {
      const {value, done} = await reader.read();
      buffer += decoder.decode(value || new Uint8Array(), {stream: !done});
      buffer = parseSseChunk(buffer, (event, payload) => {
        if (event === "progress") {
          const progress = payload.data || {};
          const completedRate = Number(progress.completed_rate || 0);
          $("#emptyState p").textContent = `指纹采样进度 ${Math.round(completedRate * 100)}%`;
        } else if (event === "result") {
          finalResult = payload.data;
          renderResult(finalResult);
        } else if (event === "error") {
          throw new Error(payload.message || "检测失败");
        }
      });
      if (done) break;
    }
    if (!finalResult) throw new Error("连接结束，但未收到检测结果");
    sessionStorage.setItem(key, JSON.stringify({time: Date.now(), result: finalResult}));
  } catch (error) {
    $("#emptyState").classList.remove("hidden");
    $("#resultContent").classList.add("hidden");
    $("#emptyState h3").textContent = "检测未完成";
    $("#emptyState p").textContent = error.message;
    setBadge("检测失败", "danger");
    toast(error.message);
  } finally {
    finishButton();
  }
}

startButton.addEventListener("click", runDetection);
loadModels();
