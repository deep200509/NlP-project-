import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../api.js";
import { useAuth } from "../auth.jsx";

export function formatDate(value) {
  return new Date(value + "Z").toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

export function StatusTag({ status }) {
  const text = { tests_passed: "Tests passed", tests_failed: "Tests failed", generated: "Not tested" }[status] || status;
  return <span className={`tag tag-${status}`}>{text}</span>;
}

export default function Dashboard() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api("/dashboard").then(setData).catch((err) => setError(err.message));
  }, []);

  if (error) return <div className="page"><p className="error" role="alert">{error}</p></div>;
  if (!data) return <div className="page"><p className="muted">Loading your dashboard…</p></div>;

  const firstName = user.name.split(" ")[0];
  const figures = [
    { value: data.total_projects, label: "projects" },
    { value: data.total_endpoints, label: "endpoints generated" },
    { value: data.projects_passing, label: "projects passing all tests" },
    { value: data.repairs_fixed, label: "bugs fixed by the repair agent" },
  ];

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Welcome back, {firstName}</h1>
          <p className="muted">Describe an API in plain English and get tested, documented code.</p>
        </div>
        <Link className="button" to="/new-api">Start a new API</Link>
      </header>

      <dl className="figures">
        {figures.map((figure) => (
          <div key={figure.label}>
            <dd>{figure.value}</dd>
            <dt>{figure.label}</dt>
          </div>
        ))}
      </dl>

      <section>
        <h2>Recent projects</h2>
        {data.recent_projects.length === 0 ? (
          <p className="empty">
            No projects yet. <Link to="/new-api">Start a new API</Link> to create your first one.
          </p>
        ) : (
          <table className="list">
            <thead>
              <tr><th>Project</th><th>Endpoints</th><th>Tests</th><th>Status</th><th>Created</th></tr>
            </thead>
            <tbody>
              {data.recent_projects.map((project) => (
                <tr key={project.id}>
                  <td><Link to={`/projects/${project.id}`}>{project.project_name}</Link></td>
                  <td>{project.endpoints}</td>
                  <td>{project.tests}</td>
                  <td><StatusTag status={project.status} /></td>
                  <td>{formatDate(project.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section>
        <h2>Last conversation</h2>
        {data.last_conversation ? (
          <Link className="conversation-link" to={`/chat/${data.last_conversation.id}`}>
            <strong>{data.last_conversation.title}</strong>
            <span>{data.last_conversation.last_message}</span>
          </Link>
        ) : (
          <p className="empty">You have not chatted with the agent yet.</p>
        )}
      </section>
    </div>
  );
}
