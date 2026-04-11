import type { PropsWithChildren, ReactNode } from "react";

type AppShellProps = PropsWithChildren<{
  currentPath: string;
  title: string;
  subtitle?: string;
  topBarContent?: ReactNode;
}>;

type NavItem = {
  href: string;
  label: string;
};

const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "Overview" },
  { href: "/stocks/600157", label: "Research" },
  { href: "/library", label: "Pattern Library" },
];

function isActivePath(currentPath: string, href: string): boolean {
  if (href === "/") {
    return currentPath === "/";
  }
  return currentPath === href || currentPath.startsWith(`${href}/`) || (href === "/stocks/600157" && currentPath.startsWith("/stocks/"));
}

export function AppShell({ currentPath, title, subtitle, topBarContent, children }: AppShellProps) {
  return (
    <div className="app-shell">
      <header className="app-shell__chrome">
        <a className="app-shell__brand" href="/">
          SwingInsight
          <span className="app-shell__brand-accent">Terminal</span>
        </a>
        <nav className="app-shell__top-nav" aria-label="Main navigation">
          {NAV_ITEMS.map((item) => (
            <a
              key={item.href}
              href={item.href}
              className={isActivePath(currentPath, item.href) ? "app-shell__nav-link is-active" : "app-shell__nav-link"}
            >
              {item.label}
            </a>
          ))}
        </nav>
        <div className="app-shell__chrome-copy">
          <p className="app-shell__eyebrow">Terminal Mode</p>
          <p className="terminal-copy-muted">Kraken-inspired dark research workspace for A-share analysis.</p>
        </div>
      </header>

      <div className="app-shell__main">
        <header className="app-shell__header">
          <div>
            <p className="app-shell__eyebrow">Swing Research Workspace</p>
            <h1 className="app-shell__title">{title}</h1>
            {subtitle === undefined ? null : <p className="app-shell__subtitle">{subtitle}</p>}
          </div>
          <div className="app-shell__topbar">{topBarContent}</div>
        </header>

        <main className="app-shell__content">{children}</main>
      </div>
    </div>
  );
}
