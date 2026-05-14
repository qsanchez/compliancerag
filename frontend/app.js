(function () {
  const C = window.CONFIG;
  let accessToken = null;
  const chatHistory = [];

  // ── Auth ──────────────────────────────────────────────────────────────────

  function parseHash() {
    const params = new URLSearchParams(window.location.hash.slice(1));
    return params.get("access_token");
  }

  function tokenExpired(token) {
    try {
      const payload = JSON.parse(atob(token.split(".")[1]));
      return Date.now() / 1000 > payload.exp;
    } catch {
      return true;
    }
  }

  function redirectToLogin() {
    const url =
      C.COGNITO_LOGIN_URL +
      "?response_type=token" +
      "&client_id=" + C.COGNITO_CLIENT_ID +
      "&redirect_uri=" + encodeURIComponent(C.REDIRECT_URI) +
      "&scope=openid+email+profile";
    window.location.href = url;
  }

  function logout() {
    sessionStorage.removeItem("access_token");
    redirectToLogin();
  }

  function initAuth() {
    const hashToken = parseHash();
    if (hashToken) {
      sessionStorage.setItem("access_token", hashToken);
      window.history.replaceState(null, "", window.location.pathname);
      return hashToken;
    }
    const stored = sessionStorage.getItem("access_token");
    if (stored && !tokenExpired(stored)) return stored;
    return null;
  }

  // ── API ───────────────────────────────────────────────────────────────────

  async function chat(question) {
    const res = await fetch(C.API_URL.replace(/\/$/, "") + "/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: "Bearer " + accessToken,
      },
      body: JSON.stringify({ question, history: chatHistory.slice(-10) }),
    });

    if (res.status === 401) {
      sessionStorage.removeItem("access_token");
      redirectToLogin();
      return null;
    }

    if (!res.ok) throw new Error("API error " + res.status);
    return res.json();
  }

  // ── Rendering ─────────────────────────────────────────────────────────────

  const messagesEl = document.getElementById("messages");

  function appendUserBubble(text) {
    const el = document.createElement("div");
    el.className = "message user";
    el.innerHTML = `<div class="bubble">${escHtml(text)}</div>`;
    messagesEl.appendChild(el);
    scrollBottom();
    return el;
  }

  function appendThinking() {
    const el = document.createElement("div");
    el.className = "message assistant";
    el.innerHTML = `<div class="thinking"><span></span><span></span><span></span></div>`;
    messagesEl.appendChild(el);
    scrollBottom();
    return el;
  }

  function renderAssistantMessage(data) {
    const badge = data.route
      ? `<div class="route-badge ${data.route}">${data.route}</div>`
      : "";

    const citations =
      data.citations && data.citations.length
        ? `<div class="citations">${data.citations
            .map((c) => `<span class="citation-tag">${escHtml(c)}</span>`)
            .join("")}</div>`
        : "";

    const chart = data.chart_b64
      ? `<img class="chart-img" src="data:image/png;base64,${data.chart_b64}" alt="Chart">`
      : "";

    const el = document.createElement("div");
    el.className = "message assistant";
    el.innerHTML = `
      <div class="bubble">
        ${badge}
        ${escHtml(data.answer)}
        ${citations}
        ${chart}
      </div>`;
    return el;
  }

  function escHtml(str) {
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function scrollBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  // ── Send flow ─────────────────────────────────────────────────────────────

  const input = document.getElementById("question-input");
  const sendBtn = document.getElementById("send-btn");

  async function send() {
    const question = input.value.trim();
    if (!question) return;

    input.value = "";
    input.style.height = "auto";
    sendBtn.disabled = true;

    appendUserBubble(question);
    const thinking = appendThinking();

    try {
      const data = await chat(question);
      if (!data) return;

      thinking.replaceWith(renderAssistantMessage(data));
      chatHistory.push({ role: "user", content: question });
      chatHistory.push({ role: "assistant", content: data.answer });
    } catch (err) {
      thinking.replaceWith((() => {
        const el = document.createElement("div");
        el.className = "message assistant";
        el.innerHTML = `<div class="bubble" style="color:#dc2626">Error: ${escHtml(err.message)}</div>`;
        return el;
      })());
    } finally {
      sendBtn.disabled = false;
      scrollBottom();
    }
  }

  sendBtn.addEventListener("click", send);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
  });
  input.addEventListener("input", () => {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 140) + "px";
  });

  // ── Suggested prompts ─────────────────────────────────────────────────────

  const PROMPTS = [
    "What does Article 32 of GDPR require?",
    "What are the NIS2 obligations for cloud providers?",
    "What are the DORA requirements for incident reporting?",
    "What is the trend of GDPR fines in Spain over the last 3 years?",
    "Which companies received the largest GDPR fines?",
    "What are the main differences between GDPR and NIS2?",
  ];

  const promptsEl = document.getElementById("suggested-prompts");
  PROMPTS.forEach((p) => {
    const btn = document.createElement("button");
    btn.className = "prompt-chip";
    btn.textContent = p;
    btn.addEventListener("click", () => {
      input.value = p;
      send();
    });
    promptsEl.appendChild(btn);
  });

  // ── Boot ──────────────────────────────────────────────────────────────────

  accessToken = initAuth();
  if (!accessToken) {
    redirectToLogin();
    return;
  }

  document.getElementById("logout-btn").addEventListener("click", logout);
  input.focus();
})();
