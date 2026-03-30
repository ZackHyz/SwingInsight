import type { SegmentLibraryData } from "../lib/api";

type SegmentTableProps = {
  rows: SegmentLibraryData["rows"];
};

export function SegmentTable({ rows }: SegmentTableProps) {
  return (
    <table>
      <thead>
        <tr>
          <th>股票</th>
          <th>波段类型</th>
          <th>标签</th>
          <th>涨跌幅</th>
          <th>持续天数</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.id}>
            <td>{row.stock_code}</td>
            <td>{row.segment_type ?? "--"}</td>
            <td>{row.label_names.join(", ")}</td>
            <td>{row.pct_change?.toFixed(2) ?? "--"}</td>
            <td>{row.duration_days ?? "--"}</td>
            <td>
              <a href={`/segments/${row.id}`}>查看详情</a>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
