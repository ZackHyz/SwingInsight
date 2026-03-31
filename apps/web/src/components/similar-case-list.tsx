type SimilarCaseListProps = {
  items: Array<{
    segment_id: number;
    stock_code: string;
    score: number;
    pct_change: number | null;
  }>;
};

export function SimilarCaseList({ items }: SimilarCaseListProps) {
  return (
    <section>
      <h3>相似历史样本</h3>
      <ul>
        {items.map((item) => (
          <li key={item.segment_id}>
            {item.stock_code} {item.score.toFixed(2)} {item.pct_change?.toFixed(2) ?? "--"}
          </li>
        ))}
      </ul>
    </section>
  );
}
