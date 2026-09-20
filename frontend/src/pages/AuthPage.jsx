import { useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../auth.jsx";
import EndpointList from "../components/EndpointList.jsx";

const SAMPLE = [
  { method: "POST", path: "/students" },
  { method: "GET", path: "/students" },
  { method: "GET", path: "/students/{id}" },
  { method: "PUT", path: "/students/{id}" },
  { method: "DELETE", path: "/students/{id}" },
];

export default function AuthPage({ mode }) {
  const isLogin = mode === "login";
  const { login, register } = useAuth();
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const update = (field) => (event) => setForm({ ...form, [field]: event.target.value });

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      if (isLogin) await login(form.email, form.password);
      else await register(form.name, form.email, form.password);
      // no navigate() needed: once the user is set, <GuestOnly> sends them to the dashboard
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <div className="auth">
      <section className="auth-demo" aria-label="What this app does">
        <p className="auth-brand">API Generator</p>
        <p className="auth-quote">
          “A student should have name, email, age and course. Users should be able to add
          students, view all students, find a student by ID, update student details and
          delete students.”
        </p>
        <p className="auth-becomes">becomes</p>
        <EndpointList endpoints={SAMPLE} tone="dark" />
        <p className="auth-foot">with a database, validation, tests and documentation.</p>
      </section>

      <section className="auth-form">
        <form onSubmit={handleSubmit}>
          <h1>{isLogin ? "Log in" : "Create your account"}</h1>

          {!isLogin && (
            <label>
              Name
              <input type="text" value={form.name} onChange={update("name")} required autoComplete="name" />
            </label>
          )}
          <label>
            Email
            <input type="email" value={form.email} onChange={update("email")} required autoComplete="email" />
          </label>
          <label>
            Password
            <input type="password" value={form.password} onChange={update("password")} required
                   minLength={isLogin ? undefined : 8}
                   autoComplete={isLogin ? "current-password" : "new-password"} />
            {!isLogin && <span className="hint">At least 8 characters.</span>}
          </label>

          {error && <p className="error" role="alert">{error}</p>}

          <button type="submit" className="button" disabled={busy}>
            {busy ? "Please wait…" : isLogin ? "Log in" : "Create account"}
          </button>

          <p className="switch">
            {isLogin ? "New here? " : "Already have an account? "}
            <Link to={isLogin ? "/register" : "/login"}>{isLogin ? "Create an account" : "Log in"}</Link>
          </p>
        </form>
      </section>
    </div>
  );
}