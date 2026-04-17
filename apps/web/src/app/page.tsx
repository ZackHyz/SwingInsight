import { AppShell } from "../components/app-shell";
import { StatusPill } from "../components/status-pill";
import { TerminalPanel } from "../components/terminal-panel";

export default function HomePage() {
  return (
    <AppShell
      currentPath="/"
      title="SwingInsight 终端"
      subtitle="面向 A 股波段研究的统一工作台，覆盖拐点编辑、事件流和形态洞察。"
      topBarContent={
        <>
          <StatusPill label="深色终端" />
          <StatusPill label="研究工作流" />
        </>
      }
    >
      <section className="terminal-grid terminal-grid--overview">
        <TerminalPanel title="工作台入口" eyebrow="总览">
          <div className="terminal-hero">
            <h2 className="terminal-hero__title">SwingInsight 终端</h2>
            <p className="terminal-hero__lede">
              从股票代码进入研究台，在同一套终端壳层里完成图表研判、事件追踪和历史形态比对。
            </p>
            <div className="terminal-actions">
              <a className="terminal-button terminal-button--primary" href="/stocks">
                打开研究台
              </a>
              <a className="terminal-button" href="/library">
                浏览形态库
              </a>
              <a className="terminal-button" href="/watchlist">
                查看观察池
              </a>
              <a className="terminal-button" href="/segments/1">
                查看示例波段
              </a>
            </div>
          </div>
        </TerminalPanel>

        <TerminalPanel title="快捷启动" eyebrow="命令入口">
          <div className="terminal-form">
            <label>
              股票代码
              <input readOnly value="" placeholder="进入研究台后手动输入" aria-label="Quick launch stock code" />
            </label>
            <p className="terminal-copy">
              进入研究台后，可以在同一视图里修正拐点、查看图表上下文，并比对相似样本。
            </p>
          </div>
        </TerminalPanel>
      </section>

      <section className="terminal-grid terminal-grid--cards">
        <TerminalPanel title="拐点编辑" eyebrow="能力">
          <p className="terminal-copy">把自动识别的波段点直接提升为人工确认拐点，并在图表上完成修正。</p>
        </TerminalPanel>
        <TerminalPanel title="事件流洞察" eyebrow="能力">
          <p className="terminal-copy">把公告、资讯和情绪上下文整理成结构化事件流，而不是零散标题列表。</p>
        </TerminalPanel>
        <TerminalPanel title="形态对比" eyebrow="能力">
          <p className="terminal-copy">把当前窗口和历史波段放到同一语境下比对，优先查看同标的样本，再扩展到跨标的。</p>
        </TerminalPanel>
      </section>
    </AppShell>
  );
}
