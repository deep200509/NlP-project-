import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { api, download } from "../api.js";
import { useAuth } from "../auth.jsx";
import EndpointList from "../components/EndpointList.jsx";
import { TestResults, parseReport } from "../components/MessageBody.jsx";
import { StatusTag, formatDate } from "./Dashboard.jsx";

export default function ProjectDetail() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [project, setProject] = useState(null);
  const [repairs, setRepairs] = useState([]);
  const [bugs, setBugs] = useState({});
  const [conversationId, setConversationId] = useState(null);
  const [file, setFile] = useState(null);
  const [bug, setBug] = useState("");
  const [busy, setBusy] = useState("");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  async function load() {
    const [detail, history] = await Promise.all([api(`/projects/${projectId}`), api(`/projects/${projectId}/repairs`)]);
    setProject(detail);
    setRepairs(history);
  }

  useEffect(() => {
    load().catch((err) => setError(err.message));
    api(`/projects/${projectId}/bugs`).then(setBugs).catch(() => {});
    api(`/projects/${projectId}/conversation`).then((data) => setConversationId(data.conversation_id)).catch(() => {});
  }, [projectId]);

  // every button uses this: show what is happening, call the server, reload, report the outcome
  async function run(label, path, describe) {
    setBusy(label); setError(""); setNotice("");
    try {
      const result = await api(path, { method: "POST" });
      await load();
      setFile(null);
      setNotice(describe(result));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }

  async function openFile(name) {
    try {
      setFile(await api(`/projects/${projectId}/files/${name}`));
    } catch (err) {
      setError(err.message);
    }
  }

  async function downloadZip() {
    setBusy("Preparing the download…"); setError(""); setNotice("");
    try {
      await download(`/projects/${projectId}/download`, `${project.specification.slug}.zip`);
      await load();
      setNotice("Download started. The zip contains the code, the tests and the documentation.");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }

  async function remove() {
    if (!window.confirm(`Delete "${project.project_name}" and its generated code? This cannot be undone.`)) return;
    try {
      await api(`/projects/${projectId}`, { method: "DELETE" });
      navigate("/projects");
    } catch (err) {
      setError(err.message);
    }
  }

  if (!project) {
    return <div className="page">{error ? <p className="error" role="alert">{error}</p> : <p className="muted">Loading the project…</p>}</div>;
  }

  const spec = project.specification;
  const folder = `generated_projects\\u${user.id}_${spec.slug}`;

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>{project.project_name}</h1>
          <p className="muted">
            <StatusTag status={project.status} /> {project.tests}, created {formatDate(project.created_at)}
          </p>
        </div>
        <div className="button-row">
          <button type="button" className="button" disabled={Boolean(busy)}
                  onClick={() => run("Running the tests…", `/projects/${projectId}/run-tests`, (r) => `Tests finished: ${r.tests}.`)}>
            Run tests
          </button>
          {project.status === "tests_failed" && (
            <button type="button" className="button" disabled={Boolean(busy)}
                    onClick={() => run("The repair agent is working. This can take a minute…", `/projects/${projectId}/repair`,
                      (r) => (r.fixed ? `Repaired in ${r.attempts_used} attempts.` : `Not repaired after ${r.attempts_used} attempts.`))}>
              Repair
            </button>
          )}
          <button type="button" className="button-outline" disabled={Boolean(busy)}
                  onClick={() => run("Generating the code again…", `/projects/${projectId}/regenerate`, (r) => `Regenerated: ${r.tests}.`)}>
            Regenerate
          </button>
          {conversationId && <Link className="button-outline" to={`/chat/${conversationId}`}>View conversation</Link>}
        </div>
      </header>

      {busy && <p className="chat-busy" role="status">{busy}</p>}
      {notice && <p className="notice" role="status">{notice}</p>}
      {error && <p className="error" role="alert">{error}</p>}

      <section>
        <h2>Requirement</h2>
        <p className="quote">{project.requirement}</p>
      </section>

      <section>
        <h2>Endpoints</h2>
        <div className="panel"><EndpointList endpoints={spec.endpoints} /></div>
      </section>

      <section>
        <h2>Database table “{spec.table_name}”</h2>
        <table className="list">
          <thead><tr><th>Field</th><th>Type</th><th>Required</th><th>Unique</th><th>How the type was decided</th></tr></thead>
          <tbody>
            <tr><td><code>id</code></td><td>integer</td><td>automatic</td><td>yes</td><td>primary key</td></tr>
            {spec.fields.map((field) => (
              <tr key={field.name}>
                <td><code>{field.name}</code></td><td>{field.type}</td>
                <td>{field.required ? "yes" : "no"}</td><td>{field.unique ? "yes" : "no"}</td><td>{field.type_source}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section>
        <h2>Test results</h2>
        {project.test_report.length === 0
          ? <p className="empty">This project has not been tested yet. Choose Run tests.</p>
          : <div className="panel"><TestResults items={parseReport(project.test_report)} /></div>}
        <p className="hint">Tests have been run {project.test_runs} times.</p>
      </section>

      <section>
        <h2>Documentation and download</h2>
        <p className="muted section-note">
          README.md explains how to run the project, API.md shows a request and a response example for
          every endpoint, and openapi.json can be imported into Postman or Swagger Editor.
        </p>
        <div className="button-row">
          <button type="button" className="button" disabled={Boolean(busy)} onClick={downloadZip}>Download project</button>
          <button type="button" className="button-outline" disabled={Boolean(busy)}
                  onClick={() => run("Writing the documentation…", `/projects/${projectId}/documentation`,
                    (r) => `Documentation written: ${r.files.join(", ")}.`)}>
            Write documentation
          </button>
          {project.files.includes("API.md") && (
            <button type="button" className="button-outline" onClick={() => openFile("API.md")}>Read API reference</button>
          )}
        </div>
      </section>

      <section>
        <h2>Generated files</h2>
        <div className="file-tabs">
          {project.files.map((name) => (
            <button key={name} type="button" className={file && file.name === name ? "active" : ""} onClick={() => openFile(name)}>
              {name}
            </button>
          ))}
        </div>
        {file
          ? <pre className={file.name.endsWith(".md") ? "code code-document" : "code"}><code>{file.content}</code></pre>
          : <p className="hint">Choose a file to read its code.</p>}
      </section>

      <section>
        <h2>Repair history</h2>
        {repairs.length === 0 ? <p className="empty">The repair agent has not been needed for this project.</p> : (
          <table className="list">
            <thead><tr><th>Attempt</th><th>Error type</th><th>File</th><th>Diagnosis</th><th>Tests</th><th>Result</th></tr></thead>
            <tbody>
              {repairs.map((attempt, index) => (
                <tr key={index}>
                  <td>{attempt.attempt}</td><td>{attempt.error_type}</td><td><code>{attempt.file || "none"}</code></td>
                  <td>{attempt.diagnosis}</td><td>{attempt.tests}</td><td>{attempt.result.replaceAll("_", " ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section>
        <h2>Demonstrate self-repair</h2>
        <p className="muted section-note">
          Break the generated code in a known way, watch the tests fail, then choose Repair.
        </p>
        <div className="button-row">
          <label className="visually-hidden" htmlFor="bug">Bug to inject</label>
          <select id="bug" value={bug} onChange={(event) => setBug(event.target.value)}>
            <option value="">Choose a bug…</option>
            {Object.entries(bugs).map(([name, description]) => <option key={name} value={name}>{description}</option>)}
          </select>
          <button type="button" className="button-outline" disabled={!bug || Boolean(busy)}
                  onClick={() => run("Injecting the bug and running the tests…", `/projects/${projectId}/inject-bug/${bug}`,
                    (r) => `Bug injected. ${r.tests}.`)}>
            Inject bug
          </button>
        </div>
      </section>

      <section>
        <h2>Run this API yourself</h2>
        <pre className="code"><code>{`cd ${folder}\nuvicorn main:app --reload --port 8001\n\nThen open http://127.0.0.1:8001/docs`}</code></pre>
        <button type="button" className="button-danger" onClick={remove}>Delete project</button>
      </section>
    </div>
  );
}