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
  { href: "/", label: "总览" },
  { href: "/stocks/600157", label: "研究台" },
  { href: "/library", label: "形态库" },
  { href: "/watchlist", label: "观察池" },
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
          <span className="app-shell__brand-accent">终端</span>
        </a>
        <nav className="app-shell__top-nav" aria-label="主导航">
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
          <p className="app-shell__eyebrow">终端模式</p>
          <p className="terminal-copy-muted">面向 A 股研究的深色工作台，聚合图表、事件流与形态分析。</p>
        </div>
      </header>

      <div className="app-shell__main">
        <header className="app-shell__header">
          <div>
            <p className="app-shell__eyebrow">SwingInsight 研究工作台</p>
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
