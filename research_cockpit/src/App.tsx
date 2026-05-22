import mockData from "./mock/execution_reality_mock.json";
import type { CockpitData } from "./types";
import { AlertPanel } from "./components/AlertPanel";
import { Alerts } from "./pages/Alerts";
import { ExecutionReality } from "./pages/ExecutionReality";
import { OutcomeTruth } from "./pages/OutcomeTruth";
import { Overview } from "./pages/Overview";
import { QuoteAge } from "./pages/QuoteAge";
import { Readiness } from "./pages/Readiness";
import { Trend } from "./pages/Trend";
import "./styles.css";

const data = mockData as CockpitData;

const pages = [
  { label: "Overview", href: "#overview" },
  { label: "Execution Reality", href: "#execution-reality" },
  { label: "Quote Age", href: "#quote-age" },
  { label: "Outcome Truth", href: "#outcome-truth" },
  { label: "Trend", href: "#trend" },
  { label: "Readiness", href: "#readiness" },
  { label: "Alerts", href: "#alerts" },
];

export default function App() {
  return (
    <main className="cockpit-shell">
      <header className="hero">
        <div>
          <p className="eyebrow">Local offline dashboard skeleton</p>
          <h1>Research Cockpit v2</h1>
          <p className="hero-copy">Static artifact driven. Mock JSON only. No backend, no websocket, no runtime JSONL reads.</p>
        </div>
        <div className="hero-status">
          <span>Mode: {data.run.mode.toUpperCase()}</span>
          <span>Run ID: {data.run.runId}</span>
          <span>Readiness: {data.readiness.percent}%</span>
        </div>
      </header>

      <nav className="page-nav" aria-label="Research Cockpit pages">
        {pages.map((page) => (
          <a key={page.href} href={page.href}>
            {page.label}
          </a>
        ))}
      </nav>

      <div className="layout">
        <div className="content-stack">
          <Overview data={data} />
          <ExecutionReality data={data} />
          <QuoteAge data={data} />
          <OutcomeTruth data={data} />
          <Trend data={data} />
          <Readiness data={data} />
          <Alerts data={data} />
        </div>
        <AlertPanel alerts={data.alerts} />
      </div>
    </main>
  );
}
