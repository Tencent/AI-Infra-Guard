const $ = (selector) => document.querySelector(selector);
const modelList = $("#modelList");
const startButton = $("#startButton");
let selectedModel = "";
let algorithm = "quick";
let configuredModels = [];
let loadedModelCount = null;
let lastRenderedResult = null;
let lastRenderedCached = false;
let language = (() => {
  try {
    return localStorage.getItem("aig-checker-language") === "en" ? "en" : "zh";
  } catch (_) {
    return "zh";
  }
})();

const translations = {
  zh: {
    pageTitle: "AIG 模型检测", metaDescription: "AI 模型真实性与 API 中转安全检测",
    heroTitle: "确认你调用的，<em>真是那个模型</em>",
    heroDescription: "结合模型指纹、协议特征与七项黑盒探针，检查 API 中转服务是否存在替换、改写或截断。",
    language: "语言", serviceReady: "本地检测服务已就绪", configureTarget: "配置检测目标",
    detectionMode: "检测模式", quickCheck: "快速检测", fullFingerprint: "完整指纹",
    configuredCredential: "使用 AIG 已配置密钥", manualApi: "手动填写 API 信息",
    configuredHint: "登录 AIG 后可直接选择模型配置，密钥不会发送到浏览器。",
    configuredActive: "将由 AIG 服务端安全注入已保存密钥。",
    configuredLoadFailed: "AIG 模型配置读取失败：{error}", apiAddress: "API 接口地址",
    showApiKey: "显示 API Key", hideApiKey: "隐藏 API Key", show: "显示", hide: "隐藏",
    targetModel: "目标模型 ID", modelPlaceholder: "可输入任意兼容模型，或从下方参考基准中选择",
    referenceBaselines: "参考指纹基准", loadingModels: "正在读取模型列表…",
    modelCount: "{count} 个指纹基准模型", modelLoadFailed: "模型列表读取失败",
    cannotLoadModels: "无法读取模型列表：{error}",
    targetModelAria: "目标模型", securityNotice: "HTTP 检测的 API Key 仅在任务内存中使用；导出的 QTest 配置只保存环境变量占位符。",
    reuseCache: "复用 10 分钟内检测结果", startCheck: "开始检测", checking: "检测中…",
    resultTitle: "检测结果", waiting: "等待检测", waitingTitle: "等待开始检测",
    waitingDescription: "选择模型并填写 API 信息，检测结果将在这里实时呈现。",
    scoreCaption: "综合检测评分", cachedScore: "10 分钟缓存结果", currentScore: "本次综合检测评分",
    conclusion: "检测结论", testInfo: "测试信息", completed: "检测完成",
    runningTitle: "正在执行安全探针", runningFull: "正在采集模型指纹，这可能需要几分钟…",
    runningQuick: "正在检查模型、响应改写、流式完整性和上下文…", running: "检测进行中",
    latency: "平均延迟", speed: "生成速度", inputTokens: "输入 Token",
    outputTokens: "输出 Token", cacheRead: "缓存读取",
    auditFinding: "审计发现", riskFound: "发现风险", integrity: "检测完整性",
    audit: "黑盒审计", incomplete: "部分检查未完成", noRisk: "未发现风险",
    passed: "通过", abnormal: "异常", checkPassed: "检测通过",
    checkIncomplete: "检查不完整", anomalyFound: "发现异常",
    invalidUrl: "请输入以 http:// 或 https:// 开头的接口地址", apiKeyRequired: "请输入 API Key",
    modelRequired: "请选择目标模型", fingerprintProgress: "指纹采样进度 {progress}%",
    failed: "检测失败", failedTitle: "检测未完成", noResult: "连接结束，但未收到检测结果",
    summaryPass: "未发现明显风险", summaryRisk: "检测发现异常", summaryInconclusive: "检测结果不完整",
    probes: {
      models: "模型列表一致性", liveness: "基础聊天可用性", identity: "模型身份一致性",
      token_delta: "隐藏 Prompt 注入", echo_rewrite: "输出与命令改写",
      stream_integrity: "流式响应完整性", context_canary: "长上下文截断",
    },
  },
  en: {
    pageTitle: "AIG Model Inspector", metaDescription: "AI model authenticity and API relay security inspection",
    heroTitle: "Verify that you are calling <em>the model you expect</em>",
    heroDescription: "Combine model fingerprints, protocol signals, and seven black-box probes to detect substitution, rewriting, or truncation by API relays.",
    language: "Language", serviceReady: "Local inspection service is ready", configureTarget: "Configure inspection target",
    detectionMode: "Inspection mode", quickCheck: "Quick check", fullFingerprint: "Full fingerprint",
    configuredCredential: "Use saved AIG credentials", manualApi: "Enter API details manually",
    configuredHint: "Sign in to AIG to select a saved model configuration. Keys are never sent to the browser.",
    configuredActive: "AIG will securely inject the saved key on the server.",
    configuredLoadFailed: "Could not load AIG model configurations: {error}", apiAddress: "API endpoint",
    showApiKey: "Show API Key", hideApiKey: "Hide API Key", show: "Show", hide: "Hide",
    targetModel: "Target model ID", modelPlaceholder: "Enter any compatible model or select a reference baseline below",
    referenceBaselines: "Reference fingerprint baselines", loadingModels: "Loading model list…",
    modelCount: "{count} fingerprint baseline models", modelLoadFailed: "Could not load model list",
    cannotLoadModels: "Could not load model list: {error}",
    targetModelAria: "Target model", securityNotice: "API keys used for HTTP checks stay in task memory; exported QTest configurations contain environment-variable placeholders only.",
    reuseCache: "Reuse results from the last 10 minutes", startCheck: "Start inspection", checking: "Inspecting…",
    resultTitle: "Inspection result", waiting: "Waiting", waitingTitle: "Ready to inspect",
    waitingDescription: "Select a model and enter the API details. Results will appear here in real time.",
    scoreCaption: "Overall inspection score", cachedScore: "Cached result from the last 10 minutes", currentScore: "Current inspection score",
    conclusion: "Conclusion", testInfo: "Test information", completed: "Inspection completed",
    runningTitle: "Running security probes", runningFull: "Collecting the model fingerprint. This may take a few minutes…",
    runningQuick: "Checking model identity, response rewriting, stream integrity, and context…", running: "Inspection in progress",
    latency: "Average latency", speed: "Generation speed", inputTokens: "Input tokens",
    outputTokens: "Output tokens", cacheRead: "Cache read",
    auditFinding: "Audit finding", riskFound: "Risk detected", integrity: "Inspection completeness",
    audit: "Black-box audit", incomplete: "Some checks did not complete", noRisk: "No risk detected",
    passed: "Passed", abnormal: "Issue", checkPassed: "Inspection passed",
    checkIncomplete: "Inspection incomplete", anomalyFound: "Issue detected",
    invalidUrl: "Enter an endpoint beginning with http:// or https://", apiKeyRequired: "Enter an API Key",
    modelRequired: "Select a target model", fingerprintProgress: "Fingerprint sampling {progress}%",
    failed: "Inspection failed", failedTitle: "Inspection did not complete", noResult: "The connection closed before an inspection result was received",
    summaryPass: "No obvious risk detected", summaryRisk: "The inspection detected an issue", summaryInconclusive: "The inspection result is incomplete",
    probes: {
      models: "Model list consistency", liveness: "Basic chat availability", identity: "Model identity consistency",
      token_delta: "Hidden prompt injection", echo_rewrite: "Output and command rewriting",
      stream_integrity: "Streaming response integrity", context_canary: "Long-context truncation",
    },
  },
};

function t(key, values = {}) {
  const raw = translations[language][key] ?? translations.zh[key] ?? key;
  return Object.entries(values).reduce(
    (text, [name, value]) => text.replaceAll(`{${name}}`, value),
    raw,
  );
}

function applyLanguage() {
  document.documentElement.lang = language === "en" ? "en" : "zh-CN";
  document.querySelectorAll("[data-i18n]").forEach(el => { el.textContent = t(el.dataset.i18n); });
  document.querySelectorAll("[data-i18n-html]").forEach(el => { el.innerHTML = t(el.dataset.i18nHtml); });
  document.querySelectorAll("[data-i18n-placeholder]").forEach(el => { el.placeholder = t(el.dataset.i18nPlaceholder); });
  document.querySelectorAll("[data-i18n-aria-label]").forEach(el => { el.setAttribute("aria-label", t(el.dataset.i18nAriaLabel)); });
  document.querySelectorAll("[data-i18n-content]").forEach(el => { el.setAttribute("content", t(el.dataset.i18nContent)); });
  document.querySelectorAll(".language").forEach(button => {
    button.classList.toggle("active", button.dataset.language === language);
    button.setAttribute("aria-pressed", String(button.dataset.language === language));
  });
  if (loadedModelCount !== null) $("#modelCount").textContent = t("modelCount", {count: loadedModelCount});
  const configured = configuredModels.find(item => item.model_id === $("#configuredModel").value);
  $("#configuredModelHint").textContent = t(configured ? "configuredActive" : "configuredHint");
  const keyVisible = $("#apiKey").type === "text";
  $("#toggleKey").textContent = t(keyVisible ? "hide" : "show");
  $("#toggleKey").setAttribute("aria-label", t(keyVisible ? "hideApiKey" : "showApiKey"));
  if (lastRenderedResult) {
    renderResult(lastRenderedResult, lastRenderedCached);
  } else if (startButton.disabled) {
    showRunning();
  }
}

document.querySelectorAll(".language").forEach(button => {
  button.addEventListener("click", () => {
    language = button.dataset.language;
    try { localStorage.setItem("aig-checker-language", language); } catch (_) {}
    applyLanguage();
  });
});

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
    loadedModelCount = models.length;
    $("#modelCount").textContent = t("modelCount", {count: models.length});
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
    $("#modelCount").textContent = t("modelLoadFailed");
    toast(t("cannotLoadModels", {error: error.message}));
  }
}

function findAigToken() {
  const jwtPattern = /^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$/;
  const visit = value => {
    if (typeof value === "string" && jwtPattern.test(value)) return value;
    if (value && typeof value === "object") {
      for (const nested of Object.values(value)) {
        const found = visit(nested);
        if (found) return found;
      }
    }
    return "";
  };
  for (const storage of [sessionStorage, localStorage]) {
    for (let index = 0; index < storage.length; index += 1) {
      const raw = storage.getItem(storage.key(index));
      const direct = visit(raw);
      if (direct) return direct;
      try {
        const nested = visit(JSON.parse(raw));
        if (nested) return nested;
      } catch (_) {}
    }
  }
  return "";
}

function aigAuthHeaders() {
  const token = findAigToken();
  return token ? {Authorization: `Bearer ${token}`} : {};
}

async function loadConfiguredModels() {
  const select = $("#configuredModel");
  try {
    const response = await fetch("/api/v1/api-checker/configured-models", {headers: aigAuthHeaders()});
    if (response.status === 401) return;
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const payload = await response.json();
    configuredModels = payload.data?.models || [];
    select.innerHTML += configuredModels.map(item =>
      `<option value="${escapeHtml(item.model_id)}">${escapeHtml(item.note ? `${item.name} · ${item.note}` : item.name)}</option>`
    ).join("");
  } catch (error) {
    $("#configuredModelHint").textContent = t("configuredLoadFailed", {error: error.message});
  }
}

$("#configuredModel").addEventListener("change", event => {
  const configured = configuredModels.find(item => item.model_id === event.target.value);
  const usingConfigured = Boolean(configured);
  $("#baseUrl").disabled = usingConfigured;
  $("#apiKey").disabled = usingConfigured;
  $("#toggleKey").disabled = usingConfigured;
  if (configured) {
    $("#baseUrl").value = configured.base_url;
    $("#apiKey").value = "";
    selectedModel = configured.name;
    $("#modelInput").value = configured.name;
    $("#configuredModelHint").textContent = t("configuredActive");
  } else {
    $("#configuredModelHint").textContent = t("configuredHint");
  }
});

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
  $("#toggleKey").textContent = t(show ? "hide" : "show");
  $("#toggleKey").setAttribute("aria-label", t(show ? "hideApiKey" : "showApiKey"));
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
  $("#emptyState h3").textContent = t("runningTitle");
  $("#emptyState p").textContent = algorithm === "full"
    ? t("runningFull")
    : t("runningQuick");
  setBadge(t("running"), "running");
  startButton.disabled = true;
  startButton.querySelector("span").textContent = t("checking");
}

function finishButton() {
  startButton.disabled = false;
  startButton.querySelector("span").textContent = t("startCheck");
}

function renderResult(result, cached = false) {
  lastRenderedResult = result;
  lastRenderedCached = cached;
  const findings = result.detail?.findings || [];
  const score = Number(result.score || 0);
  const safe = result.overall_verdict === "pass";
  const inconclusive = result.overall_verdict === "inconclusive";

  $("#emptyState").classList.add("hidden");
  $("#resultContent").classList.remove("hidden");
  $("#scoreValue").textContent = Math.round(score);
  $("#scoreRing").style.setProperty("--score", score);
  $("#scoreRing").style.setProperty("--ring-color",
    safe ? "var(--green)" : (inconclusive ? "var(--orange)" : "var(--red)"));
  $("#testedModel").textContent = selectedModel;
  $("#scoreCaption").textContent = t(cached ? "cachedScore" : "currentScore");
  $("#resultSummary").textContent = language === "zh"
    ? (result.summary || t("completed"))
    : t(safe ? "summaryPass" : (inconclusive ? "summaryInconclusive" : "summaryRisk"));
  const testInfo = result.detail?.test_info || {};
  const metric = (value, suffix = "") =>
    value === null || value === undefined ? "—" : `${value}${suffix}`;
  const metrics = [
    [t("latency"), metric(testInfo.latency_ms, " ms")],
    [t("speed"), metric(testInfo.tokens_per_second, " tokens/s")],
    [t("inputTokens"), metric(testInfo.input_tokens)],
    [t("outputTokens"), metric(testInfo.output_tokens)],
    [t("cacheRead"), metric(testInfo.cache_read_tokens)],
  ];
  $("#testInfo").innerHTML = metrics.map(([label, value]) => `
    <div class="metric-card">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
    </div>`).join("");

  const items = findings.map(finding => ({
    name: translations[language].probes[finding.probe] || finding.probe || t("auditFinding"),
    ok: false,
    meta: finding.title || finding.severity || t("riskFound"),
  }));
  if (!findings.length) {
    items.push({
      name: t(inconclusive ? "integrity" : "audit"),
      ok: !inconclusive,
      meta: t(inconclusive ? "incomplete" : "noRisk"),
    });
  }
  $("#checkList").innerHTML = items.map(item => `
    <div class="check-item">
      <span class="check-icon ${item.ok ? "ok" : "fail"}">${item.ok ? "✓" : "×"}</span>
      <div><div>${escapeHtml(item.name)}</div><div class="check-meta">${escapeHtml(item.meta)}</div></div>
      <span class="check-state ${item.ok ? "ok" : "fail"}">${t(item.ok ? "passed" : "abnormal")}</span>
    </div>`).join("");

  setBadge(
    t(safe ? "checkPassed" : (inconclusive ? "checkIncomplete" : "anomalyFound")),
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
  const configuredModelId = $("#configuredModel").value;
  if (!configuredModelId && !/^https?:\/\//.test(baseUrl)) return toast(t("invalidUrl"));
  if (!configuredModelId && !apiKey) return toast(t("apiKeyRequired"));
  if (!selectedModel) return toast(t("modelRequired"));

  const key = cacheKey(baseUrl, selectedModel, configuredModelId || apiKey);
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
    const response = await fetch(configuredModelId
      ? "/api/v1/api-checker/configured-check/stream"
      : "/api/v1/relay/check/stream", {
      method: "POST",
      headers: {"Content-Type": "application/json", ...(configuredModelId ? aigAuthHeaders() : {})},
      body: JSON.stringify(configuredModelId ? {
        configured_model_id: configuredModelId,
        algorithm,
        iterations: 200,
        no_think: true,
      } : {
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
          $("#emptyState p").textContent = t("fingerprintProgress", {progress: Math.round(completedRate * 100)});
        } else if (event === "result") {
          finalResult = payload.data;
          renderResult(finalResult);
        } else if (event === "error") {
          throw new Error(payload.message || t("failed"));
        }
      });
      if (done) break;
    }
    if (!finalResult) throw new Error(t("noResult"));
    sessionStorage.setItem(key, JSON.stringify({time: Date.now(), result: finalResult}));
  } catch (error) {
    $("#emptyState").classList.remove("hidden");
    $("#resultContent").classList.add("hidden");
    $("#emptyState h3").textContent = t("failedTitle");
    $("#emptyState p").textContent = error.message;
    setBadge(t("failed"), "danger");
    toast(error.message);
  } finally {
    finishButton();
  }
}

startButton.addEventListener("click", runDetection);
applyLanguage();
loadModels();
loadConfiguredModels();
