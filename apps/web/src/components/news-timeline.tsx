import type { SegmentDetailData } from "../lib/api";

type NewsTimelineProps = {
  items: SegmentDetailData["news_timeline"];
};

export function NewsTimeline({ items }: NewsTimelineProps) {
  return (
    <section className="terminal-panel">
      <header className="terminal-panel__header">
        <div>
          <p className="terminal-panel__eyebrow">事件时间线</p>
          <h2 className="terminal-panel__title">新闻时间线</h2>
        </div>
      </header>
      <ul className="terminal-list terminal-panel__body">
        {items.map((item) => (
          <li key={item.news_id} className="metric-card">
            <strong>{item.title}</strong> <span>{item.relation_type}</span>{" "}
            <span>{item.news_date ?? "未知日期"}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
