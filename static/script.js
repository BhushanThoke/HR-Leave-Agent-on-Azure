const messagesEl = document.getElementById("messages");
const formEl = document.getElementById("chat-form");
const inputEl = document.getElementById("chat-input");
const sendBtn = document.getElementById("send-btn");
const statusEl = document.getElementById("status");

// Persist a session id per browser tab so the agent keeps context
// across messages within the same visit.
const SESSION_KEY = "hr_leave_session_id";
let sessionId = sessionStorage.getItem(SESSION_KEY);
if (!sessionId) {
  sessionId = crypto.randomUUID();
  sessionStorage.setItem(SESSION_KEY, sessionId);
}

function addMessage(role, text, { pending = false } = {}) {
  const wrap = document.createElement("div");
  wrap.className = `msg ${role}`;

  const label = document.createElement("div");
  label.className = "msg-label";
  label.textContent = role === "user" ? "You" : "Leave Desk";

  const bubble = document.createElement("div");
  bubble.className = "msg-bubble" + (pending ? " pending" : "");
  bubble.textContent = text;

  wrap.appendChild(label);
  wrap.appendChild(bubble);
  messagesEl.appendChild(wrap);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return bubble;
}

async function sendMessage(message) {
  statusEl.textContent = "";
  addMessage("user", message);
  const pendingBubble = addMessage("agent", "Thinking…", { pending: true });
  sendBtn.disabled = true;

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, session_id: sessionId }),
    });

    const data = await res.json();

    if (!res.ok) {
      pendingBubble.parentElement.remove();
      statusEl.textContent = data.error || "Something went wrong. Please try again.";
      return;
    }

    if (data.session_id) {
      sessionId = data.session_id;
      sessionStorage.setItem(SESSION_KEY, sessionId);
    }

    pendingBubble.textContent = data.reply;
    pendingBubble.classList.remove("pending");
  } catch (err) {
    pendingBubble.parentElement.remove();
    statusEl.textContent = "Network error — please check your connection and try again.";
  } finally {
    sendBtn.disabled = false;
    inputEl.focus();
  }
}

formEl.addEventListener("submit", (e) => {
  e.preventDefault();
  const message = inputEl.value.trim();
  if (!message) return;
  inputEl.value = "";
  sendMessage(message);
});
