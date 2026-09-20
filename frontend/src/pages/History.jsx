import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../api.js";
import { formatDate } from "./Dashboard.jsx";

export default function History() {
  const [conversations, setConversations] = useState(null);
  const [error, setError] = useState("");

  const load = () => api("/conversations").then(setConversations).catch((err) => setError(err.message));
  useEffect(() => { load(); }, []);

  async function remove(conversation) {
    if (!window.confirm(`Delete the conversation "${conversation.title}"? Its projects are kept.`)) return;
    try {
      await api(`/conversations/${conversation.id}`, { method: "DELETE" });
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Chat history</h1>
          <p className="muted">Open a conversation to continue exactly where you stopped.</p>
        </div>
        <Link className="button" to="/new-api">Start a new API</Link>
      </header>

      {error && <p className="error" role="alert">{error}</p>}
      {!conversations && !error && <p className="muted">Loading your conversations…</p>}
      {conversations && conversations.length === 0 && (
        <p className="empty">No conversations yet. <Link to="/new-api">Start a new API</Link> to begin one.</p>
      )}
      {conversations && conversations.length > 0 && (
        <ul className="history">
          {conversations.map((conversation) => (
            <li key={conversation.id}>
              <Link to={`/chat/${conversation.id}`}>
                <strong>{conversation.title}</strong>
                <span>{conversation.last_message || "No messages yet"}</span>
              </Link>
              <span className="history-meta">{formatDate(conversation.updated_at)}, {conversation.messages} messages</span>
              <button type="button" className="button-outline button-small" onClick={() => remove(conversation)}>Delete</button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}