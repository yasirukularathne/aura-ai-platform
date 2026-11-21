const state = {
  apiUrl: sessionStorage.getItem("auraApiUrl") || "http://localhost:8000",
  apiKey: sessionStorage.getItem("auraApiKey") || "",
  conversationId: sessionStorage.getItem("auraConversationId") || "",
};

const $ = (id) => document.getElementById(id);
const apiUrl = () => $("api-url").value.trim().replace(/\/$/, "");
const headers = () => {
  const workspaceId = $("workspace-id")?.value.trim();
  return {
    "X-API-Key": $("api-key").value.trim(),
    ...(workspaceId ? { "X-Workspace-ID": workspaceId } : {}),
  };
};

function setStatus(element, text, good = null) {
  element.textContent = text;
  element.className = `status ${good === true ? "status-good" : good === false ? "status-bad" : "status-neutral"}`;
}

async function request(path, options = {}) {
  const response = await fetch(`${apiUrl()}${path}`, {
    ...options,
    headers: { ...headers(), ...(options.headers || {}) },
  });
  const body = response.headers.get("content-type")?.includes("json")
    ? await response.json()
    : await response.text();
  if (!response.ok) {
    throw new Error(typeof body === "string" ? body : body.detail || `Request failed (${response.status})`);
  }
  return body;
}

async function checkHealth() {
  try {
    await fetch(`${apiUrl()}/health/live`);
    setStatus($("api-status"), "API online", true);
  } catch (error) {
    setStatus($("api-status"), "API offline", false);
  }
}

async function uploadDocument() {
  const file = $("document-file").files[0];
  if (!file) return ($("upload-message").textContent = "Choose a supported document.");
  const form = new FormData();
  form.append("file", file);
  $("upload-document").disabled = true;
  try {
    const result = await request("/api/documents/upload", { method: "POST", body: form });
    $("job-id").value = result.job_id;
    $("upload-message").textContent = `Accepted ${result.filename}. Job: ${result.job_id}`;
    await refreshJob();
    await refreshDocuments();
  } catch (error) {
    $("upload-message").textContent = error.message;
  } finally {
    $("upload-document").disabled = false;
  }
}

async function refreshJob() {
  const jobId = $("job-id").value.trim();
  if (!jobId) return;
  try {
    const result = await request(`/api/documents/${encodeURIComponent(jobId)}`);
    setStatus($("job-status"), result.status, result.status === "completed" ? true : result.status === "failed" ? false : null);
    $("job-details").textContent = JSON.stringify(result, null, 2);
  } catch (error) {
    setStatus($("job-status"), "Unavailable", false);
    $("job-details").textContent = error.message;
  }
}

async function renderDocuments(documents) {
  const container = $("document-list");
  container.innerHTML = "";
  if (!documents.length) {
    container.innerHTML = '<p class="muted">No documents uploaded yet.</p>';
    return;
  }
  documents.forEach((document) => {
    const row = document.createElement("article");
    row.className = "document-row";

    const details = document.createElement("div");
    const name = document.createElement("strong");
    name.textContent = document.filename;
    const metadata = document.createElement("small");
    metadata.textContent = `${document.status} · ${new Date(document.created_at).toLocaleString()}`;
    details.append(name, metadata);

    const remove = document.createElement("button");
    remove.className = "secondary";
    remove.textContent = "Delete";
    remove.addEventListener("click", () => deleteDocument(document.job_id, remove));
    row.append(details, remove);
    container.append(row);
  });
}

async function refreshDocuments() {
  try {
    const result = await request("/api/documents");
    renderDocuments(Array.isArray(result.documents) ? result.documents : []);
  } catch (error) {
    $("document-list").textContent = error.message;
  }
}

async function deleteDocument(jobId, button) {
  if (!window.confirm("Delete this document and its indexed vectors?")) return;
  button.disabled = true;
  try {
    await request(`/api/documents/${encodeURIComponent(jobId)}`, { method: "DELETE" });
    if ($("job-id").value.trim() === jobId) {
      $("job-id").value = "";
      $("job-status").textContent = "No job selected";
      $("job-details").textContent = "No job loaded.";
    }
    await refreshDocuments();
  } catch (error) {
    button.disabled = false;
    $("upload-message").textContent = error.message;
  }
}

async function refreshMetrics() {
  try {
    $("metrics").textContent = await request("/metrics", { headers: {} });
  } catch (error) {
    $("metrics").textContent = error.message;
  }
}

function addChatMessage(role, text, citations = []) {
  const container = $("chat-messages");
  container.querySelector(".chat-empty")?.remove();
  const message = document.createElement("article");
  message.className = `chat-message ${role}`;

  const label = document.createElement("span");
  label.className = "chat-label";
  label.textContent = role === "user" ? "You" : "AURA";
  message.append(label);

  const content = document.createElement("div");
  content.textContent = text;
  message.append(content);

  if (citations.length) {
    const sourceList = document.createElement("div");
    sourceList.className = "citations";
    sourceList.textContent = `Sources: ${citations.map((citation) => {
      const documentName = citation.document || citation.source || "document";
      const page = citation.page === undefined ? "" : `, page ${citation.page}`;
      return `${documentName}${page}`;
    }).join(" · ")}`;
    message.append(sourceList);
  }
  container.append(message);
  container.scrollTop = container.scrollHeight;
}

function renderHistory(messages) {
  $("chat-messages").innerHTML = "";
  if (!messages.length) {
    $("chat-messages").innerHTML = '<p class="chat-empty">Ask a question about your indexed documents.</p>';
    return;
  }
  messages.forEach((message) => {
    let citations = [];
    try {
      citations = message.citations ? JSON.parse(message.citations) : [];
    } catch (error) {
      citations = [];
    }
    addChatMessage(message.role, message.content, citations);
  });
}

async function loadConversation() {
  if (!state.conversationId || !$("api-key").value.trim()) return;
  try {
    const result = await request(`/api/chat/conversations/${encodeURIComponent(state.conversationId)}`);
    renderHistory(result.messages);
  } catch (error) {
    state.conversationId = "";
    sessionStorage.removeItem("auraConversationId");
  }
}

function renderConversations(conversations) {
  const container = $("conversation-list");
  container.innerHTML = "";
  if (!conversations.length) {
    container.innerHTML = '<p class="muted">No conversations yet.</p>';
    return;
  }
  conversations.forEach((conversation) => {
    const row = document.createElement("article");
    row.className = "conversation-row";
    const select = document.createElement("button");
    select.className = "secondary conversation-select";
    select.textContent = conversation.title;
    select.addEventListener("click", async () => {
      state.conversationId = conversation.conversation_id;
      sessionStorage.setItem("auraConversationId", state.conversationId);
      await loadConversation();
    });
    const rename = document.createElement("button");
    rename.className = "secondary";
    rename.textContent = "Rename";
    rename.addEventListener("click", () => renameConversation(conversation));
    const remove = document.createElement("button");
    remove.className = "secondary";
    remove.textContent = "Delete";
    remove.addEventListener("click", () => deleteConversation(conversation.conversation_id));
    row.append(select, rename, remove);
    container.append(row);
  });
}

async function refreshConversations() {
  try {
    const result = await request("/api/chat/conversations");
    renderConversations(Array.isArray(result.conversations) ? result.conversations : []);
  } catch (error) {
    $("conversation-list").textContent = error.message;
  }
}

async function renameConversation(conversation) {
  const title = window.prompt("Conversation title", conversation.title);
  if (!title?.trim()) return;
  try {
    await request(`/api/chat/conversations/${encodeURIComponent(conversation.conversation_id)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: title.trim() }),
    });
    await refreshConversations();
  } catch (error) {
    $("chat-error").textContent = error.message;
  }
}

async function deleteConversation(conversationId) {
  if (!window.confirm("Delete this conversation and all its messages?")) return;
  try {
    await request(`/api/chat/conversations/${encodeURIComponent(conversationId)}`, { method: "DELETE" });
    if (state.conversationId === conversationId) clearChat();
    await refreshConversations();
  } catch (error) {
    $("chat-error").textContent = error.message;
  }
}

async function askQuestion(event) {
  event.preventDefault();
  const input = $("chat-question");
  const question = input.value.trim();
  if (!question) return;

  addChatMessage("user", question);
  input.value = "";
  $("send-question").disabled = true;
  $("chat-error").textContent = "";
  try {
    const result = await request("/api/chat/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        conversation_id: state.conversationId || null,
      }),
    });
    state.conversationId = result.conversation_id;
    sessionStorage.setItem("auraConversationId", state.conversationId);
    addChatMessage(
      "assistant",
      result.answer || "AURA did not return an answer.",
      Array.isArray(result.citations) ? result.citations : [],
    );
    await refreshConversations();
  } catch (error) {
    $("chat-error").textContent = error.message;
    addChatMessage("assistant", "I could not complete that request.");
  } finally {
    $("send-question").disabled = false;
    input.focus();
  }
}

function clearChat() {
  $("chat-messages").innerHTML = '<p class="chat-empty">Ask a question about your indexed documents.</p>';
  $("chat-error").textContent = "";
  state.conversationId = "";
  sessionStorage.removeItem("auraConversationId");
}

function saveSettings() {
  state.apiUrl = apiUrl();
  state.apiKey = $("api-key").value.trim();
  sessionStorage.setItem("auraApiUrl", state.apiUrl);
  sessionStorage.setItem("auraApiKey", state.apiKey);
  checkHealth();
  loadConversation();
}

$("api-url").value = state.apiUrl;
$("api-key").value = state.apiKey;
$("save-settings").addEventListener("click", saveSettings);
$("upload-document").addEventListener("click", uploadDocument);
$("refresh-job").addEventListener("click", refreshJob);
$("refresh-documents").addEventListener("click", refreshDocuments);
$("refresh-metrics").addEventListener("click", refreshMetrics);
$("chat-form").addEventListener("submit", askQuestion);
$("clear-chat").addEventListener("click", clearChat);
$("refresh-conversations").addEventListener("click", refreshConversations);
checkHealth();
loadConversation();
refreshDocuments();
refreshConversations();
