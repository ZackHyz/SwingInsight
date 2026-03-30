import type { SegmentDetailData } from "../lib/api";

type NewsTimelineProps = {
  items: SegmentDetailData["news_timeline"];
};

export function NewsTimeline({ items }: NewsTimelineProps) {
  return (
    <section>
      <h2>新闻时间线</h2>
      <ul>
        {items.map((item) => (
          <li key={item.news_id}>
            <strong>{item.title}</strong> <span>{item.relation_type}</span>{" "}
            <span>{item.news_date ?? "unknown-date"}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
