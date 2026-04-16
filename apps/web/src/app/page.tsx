import { AppShell } from "../components/app-shell";
import { StatusPill } from "../components/status-pill";
import { TerminalPanel } from "../components/terminal-panel";

export default function HomePage() {
  return (
    <AppShell
      currentPath="/"
      title="SwingInsight Terminal"
      subtitle="A-share swing research workspace for turning points, event flow, and pattern intelligence."
      topBarContent={
        <>
          <StatusPill label="Dark Terminal" />
          <StatusPill label="Kraken-Inspired" />
        </>
      }
    >
      <section className="terminal-grid terminal-grid--overview">
        <TerminalPanel title="Terminal Entry" eyebrow="Overview">
          <div className="terminal-hero">
            <h2 className="terminal-hero__title">SwingInsight Terminal</h2>
            <p className="terminal-hero__lede">
              Start from a stock code, move into the chart workspace, and drill into event flow and historical pattern
              evidence without leaving the same terminal shell.
            </p>
            <div className="terminal-actions">
              <a className="terminal-button terminal-button--primary" href="/stocks/600157">
                Open Research Workspace
              </a>
              <a className="terminal-button" href="/library">
                Browse Pattern Library
              </a>
              <a className="terminal-button" href="/watchlist">
                Open Ranked Watchlist
              </a>
              <a className="terminal-button" href="/segments/1">
                Inspect Demo Segment
              </a>
            </div>
          </div>
        </TerminalPanel>

        <TerminalPanel title="Quick Launch" eyebrow="Command Line">
          <div className="terminal-form">
            <label>
              Stock Code
              <input readOnly value="600157" aria-label="Quick launch stock code" />
            </label>
            <p className="terminal-copy">
              Use the research workspace to adjust turning points, inspect chart context, and compare similar cases in a
              single view.
            </p>
          </div>
        </TerminalPanel>
      </section>

      <section className="terminal-grid terminal-grid--cards">
        <TerminalPanel title="Turning Point Editing" eyebrow="Capability">
          <p className="terminal-copy">Move from auto-detected swing points to analyst-confirmed turning points directly on the chart.</p>
        </TerminalPanel>
        <TerminalPanel title="Event Flow Intelligence" eyebrow="Capability">
          <p className="terminal-copy">Read announcements, news events, and sentiment context as a structured event stream instead of raw headlines.</p>
        </TerminalPanel>
        <TerminalPanel title="Pattern Comparison" eyebrow="Capability">
          <p className="terminal-copy">Compare the current window with same-stock-first historical segments and open local chart comparisons in context.</p>
        </TerminalPanel>
      </section>
    </AppShell>
  );
}
