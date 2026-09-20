import { useState } from "react";

import { api } from "../api.js";
import { useAuth } from "../auth.jsx";
import { formatDate } from "./Dashboard.jsx";

export default function Settings() {
  const { user, logout } = useAuth();
  const [status, setStatus] = useState(null);
  const [checking, setChecking] = useState(false);

  async function checkModel() {
    setChecking(true);
    try {
      setStatus(await api("/llm/status"));
    } catch (err) {
      setStatus({ reachable: false, problem: err.message });
    } finally {
      setChecking(false);
    }
  }

  return (
    <div className="page">
      <header>
        <h1>Settings</h1>
        <p className="muted">Your account and the language model used by the repair agent.</p>
      </header>

      <section>
        <h2>Account</h2>
        <dl className="details">
          <div><dt>Name</dt><dd>{user.name}</dd></div>
          <div><dt>Email</dt><dd>{user.email}</dd></div>
          <div><dt>Member since</dt><dd>{formatDate(user.created_at)}</dd></div>
        </dl>
        <button type="button" className="button-outline" onClick={logout}>Log out</button>
      </section>

      <section>
        <h2>Language model</h2>
        <p className="muted section-note">
          The model is only used to repair generated code when tests fail. Requirements are
          understood by the app's own NLP pipeline, not by the model.
        </p>
        <button type="button" className="button-outline" onClick={checkModel} disabled={checking}>
          {checking ? "Checking…" : "Check connection"}
        </button>
        {status && (
          <dl className="details">
            <div><dt>Provider</dt><dd>{status.provider || "unknown"}</dd></div>
            <div><dt>Model</dt><dd>{status.model || "unknown"}</dd></div>
            <div><dt>Connection</dt><dd>{status.reachable ? "Working" : `Not working: ${status.problem}`}</dd></div>
          </dl>
        )}
      </section>
    </div>
  );
}