import type { PropsWithChildren, ReactNode } from "react";

type TerminalPanelProps = PropsWithChildren<{
  title: string;
  eyebrow?: string;
  actions?: ReactNode;
  className?: string;
}>;

export function TerminalPanel({ title, eyebrow, actions, className, children }: TerminalPanelProps) {
  const resolvedClassName = className === undefined ? "terminal-panel" : `terminal-panel ${className}`;

  return (
    <section className={resolvedClassName}>
      <header className="terminal-panel__header">
        <div>
          {eyebrow === undefined ? null : <p className="terminal-panel__eyebrow">{eyebrow}</p>}
          <h2 className="terminal-panel__title">{title}</h2>
        </div>
        {actions === undefined ? null : <div className="terminal-panel__actions">{actions}</div>}
      </header>
      <div className="terminal-panel__body">{children}</div>
    </section>
  );
}
