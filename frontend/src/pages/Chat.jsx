import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { api } from "../api.js";
import MessageBody from "../components/MessageBody.jsx";

const EXAMPLES = [
  "Create an API for a student management system. A student should have name, email, age and course. Users should be able to add students, view all students, find a student by ID, update student details and delete students.",
  "I want to create a library management API.",
  "Build an API to manage products with name, price and stock. Users can add, view, update and delete products, search products by name and sort products by price.",
];
const STAGE_TEXT = {
  ANALYZE: "Waiting for your requirement",
  CLARIFY: "The agent needs more information",
  CONFIRM: "Review the proposed API",
  GENERATE: "Generating",
  DONE: "API generated and tested",
};

export default function Chat() {
  const { conversationId } = useParams();
  const navigate = useNavigate();
  const [messages, setMessages] = useState([]);
  const [stage, setStage] = useState("ANALYZE");
  const [projectId, setProjectId] = useState(null);
  const [title, setTitle] = useState("New API");
  const [text, setText] = useState("");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  // open an existing conversation: everything comes back from the database
  useEffect(() => {
    if (!conversationId) {
      setMessages([]); setStage("ANALYZE"); setProjectId(null); setTitle("New API");
      return undefined;
    }
    let cancelled = false;
    api(`/conversations/${conversationId}`)
      .then((conversation) => {
        if (cancelled) return;
        setMessages(conversation.messages);
        setStage(conversation.stage);
        setProjectId(conversation.project_id);
        setTitle(conversation.title);
      })
      .catch((err) => !cancelled && setError(err.message));
    return () => { cancelled = true; };
  }, [conversationId]);

  useEffect(() => {
    if (bottomRef.current) bottomRef.current.scrollIntoView({ block: "end" });
  }, [messages, busy]);

  async function send(content) {
    const message = content.trim();
    if (!message || busy) return;
    const building = stage === "CONFIRM" && /^(yes|ok|okay|sure|generate|go ahead|build|confirm|proceed)/i.test(message);
    setError("");
    setText("");
    setBusy(building ? "Generating the code, creating the database and running the tests. This can take up to a minute…" : "Thinking…");
    setMessages((current) => [...current, { role: "user", content: message }]);
    try {
      let id = conversationId;
      if (!id) id = (await api("/conversations", { method: "POST" })).id;
      const reply = await api(`/conversations/${id}/messages`, { method: "POST", body: { content: message } });
      setMessages((current) => [...current, { role: "assistant", content: reply.reply }]);
      setStage(reply.stage);
      setTitle(reply.conversation.title);
      if (reply.project) setProjectId(reply.project.id);
      if (!conversationId) navigate(`/chat/${id}`, { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }

  function handleKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      send(text);
    }
  }

  return (
    <div className="chat">
      <header className="chat-head">
        <h1>{title}</h1>
        <p className="muted">{STAGE_TEXT[stage] || stage}</p>
      </header>

      <div className="chat-messages" aria-live="polite">
        {messages.length === 0 && !busy && (
          <div className="chat-start">
            <p>Describe the API you need in plain English. The agent asks questions when something is missing.</p>
            <p className="muted">Or start from an example:</p>
            {EXAMPLES.map((example) => (
              <button key={example} type="button" className="example" onClick={() => setText(example)}>{example}</button>
            ))}
          </div>
        )}

        {messages.map((message, index) => (
          <article key={index} className={`message message-${message.role}`}>
            <p className="message-author">{message.role === "user" ? "You" : "Agent"}</p>
            {message.role === "user" ? <p className="message-text">{message.content}</p> : <MessageBody text={message.content} />}
          </article>
        ))}

        {busy && <p className="chat-busy" role="status">{busy}</p>}

        {!busy && stage === "CONFIRM" && (
          <div className="chat-actions">
            <button type="button" className="button" onClick={() => send("generate")}>Generate API</button>
            <button type="button" className="button-outline" onClick={() => inputRef.current && inputRef.current.focus()}>
              Edit requirements
            </button>
          </div>
        )}
        {!busy && stage === "DONE" && projectId && (
          <div className="chat-actions">
            <Link className="button" to={`/projects/${projectId}`}>Open project</Link>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {error && <p className="error" role="alert">{error}</p>}

      <form className="chat-input" onSubmit={(event) => { event.preventDefault(); send(text); }}>
        <label className="visually-hidden" htmlFor="chat-text">Your message</label>
        <textarea id="chat-text" ref={inputRef} rows={3} value={text} disabled={Boolean(busy)}
                  onChange={(event) => setText(event.target.value)} onKeyDown={handleKeyDown}
                  placeholder={stage === "CONFIRM"
                    ? 'Say what to change, for example "add field phone" or "make price an integer"'
                    : "Describe your API, or answer the agent's question"} />
        <button type="submit" className="button" disabled={Boolean(busy) || !text.trim()}>Send</button>
      </form>
      <p className="hint">Press Enter to send, Shift + Enter for a new line.</p>
    </div>
  );
}