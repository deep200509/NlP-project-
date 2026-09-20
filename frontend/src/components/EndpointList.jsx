// The signature element of the app: a list of routes with coloured method badges.
export default function EndpointList({ endpoints, tone = "light" }) {
  return (
    <ul className={`endpoints endpoints-${tone}`}>
      {endpoints.map((endpoint) => (
        <li key={`${endpoint.method} ${endpoint.path}`}>
          <span className={`method method-${endpoint.method.toLowerCase()}`}>{endpoint.method}</span>
          <span className="path">{endpoint.path}</span>
          {endpoint.summary && <span className="summary">{endpoint.summary}</span>}
        </li>
      ))}
    </ul>
  );
}