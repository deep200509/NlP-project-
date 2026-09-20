// Turns the agent's plain-text reply into something easier to read:
// route lines become method badges, field lines become a small table, test lines get a pass/fail mark.
import EndpointList from "./EndpointList.jsx";

const ROUTE = /^\s{2}(GET|POST|PUT|PATCH|DELETE)\s+(\/\S*)$/;
const FIELD = /^\s{2}([a-z][a-z0-9_]*) \((.+)\)$/;
const RESULT = /^(.*?)\s{2,}(✓ PASS|✗ FAIL|- SKIP)\s+(.*)$/;

function toBlocks(text) {
  const blocks = [];
  const push = (type, item) => {
    const last = blocks[blocks.length - 1];
    if (last && last.type === type) last.items.push(item);
    else blocks.push({ type, items: [item] });
  };
  for (const line of text.split("\n")) {
    let match;
    if ((match = line.match(ROUTE))) push("routes", { method: match[1], path: match[2] });
    else if ((match = line.match(FIELD))) push("fields", { name: match[1], type: match[2] });
    else if ((match = line.match(RESULT))) push("results", { endpoint: match[1], status: match[2], check: match[3] });
    else push("text", line);
  }
  return blocks;
}

export function TestResults({ items }) {
  return (
    <ul className="results">
      {items.map((item, index) => (
        <li key={index} className={item.status.includes("PASS") ? "pass" : item.status.includes("FAIL") ? "fail" : "skip"}>
          <span className="result-mark">{item.status.includes("PASS") ? "Pass" : item.status.includes("FAIL") ? "Fail" : "Skip"}</span>
          <span className="result-endpoint">{item.endpoint}</span>
          <span className="result-check">{item.check}</span>
        </li>
      ))}
    </ul>
  );
}

export function parseReport(lines) {
  return lines.map((line) => line.match(RESULT)).filter(Boolean)
    .map((match) => ({ endpoint: match[1], status: match[2], check: match[3] }));
}

export default function MessageBody({ text }) {
  return (
    <div className="message-body">
      {toBlocks(text).map((block, index) => {
        if (block.type === "routes") return <EndpointList key={index} endpoints={block.items} />;
        if (block.type === "results") return <TestResults key={index} items={block.items} />;
        if (block.type === "fields") {
          return (
            <ul key={index} className="field-list">
              {block.items.map((field) => (
                <li key={field.name}><code>{field.name}</code><span>{field.type}</span></li>
              ))}
            </ul>
          );
        }
        const paragraph = block.items.join("\n").trim();
        return paragraph ? <p key={index}>{paragraph}</p> : null;
      })}
    </div>
  );
}