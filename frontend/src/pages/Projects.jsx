import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../api.js";
import { StatusTag, formatDate } from "./Dashboard.jsx";

export default function Projects() {
  const [projects, setProjects] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api("/projects").then(setProjects).catch((err) => setError(err.message));
  }, []);

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>My projects</h1>
          <p className="muted">Every API you have generated, with its latest test result.</p>
        </div>
        <Link className="button" to="/new-api">Start a new API</Link>
      </header>

      {error && <p className="error" role="alert">{error}</p>}
      {!projects && !error && <p className="muted">Loading your projects…</p>}
      {projects && projects.length === 0 && (
        <p className="empty">No projects yet. <Link to="/new-api">Start a new API</Link> to create your first one.</p>
      )}
      {projects && projects.length > 0 && (
        <table className="list">
          <thead>
            <tr><th>Project</th><th>Endpoints</th><th>Tests</th><th>Status</th><th>Created</th></tr>
          </thead>
          <tbody>
            {projects.map((project) => (
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
    </div>
  );
}