import type { SegmentLibraryData } from "../lib/api";
import { getMarketValueClass } from "../lib/market-tone";

type SegmentTableProps = {
  rows: SegmentLibraryData["rows"];
};

export function SegmentTable({ rows }: SegmentTableProps) {
  return (
    <div className="terminal-table-wrap">
      <table className="terminal-table">
        <thead>
          <tr>
            <th>股票</th>
            <th>波段类型</th>
            <th>标签</th>
            <th className="numeric">涨跌幅</th>
            <th className="numeric">持续天数</th>
            <th>详情</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id}>
              <td>{row.stock_code}</td>
              <td>{row.segment_type ?? "--"}</td>
              <td>{row.label_names.join(", ")}</td>
              <td className={`numeric ${getMarketValueClass(row.pct_change)}`}>{row.pct_change?.toFixed(2) ?? "--"}</td>
              <td className="numeric">{row.duration_days ?? "--"}</td>
              <td>
                <a href={`/segments/${row.id}`}>查看详情</a>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
