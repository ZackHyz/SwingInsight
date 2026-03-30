"use client";

type SegmentFilterBarProps = {
  stockCode: string;
  segmentType: string;
  label: string;
  onStockCodeChange: (value: string) => void;
  onSegmentTypeChange: (value: string) => void;
  onLabelChange: (value: string) => void;
};

export function SegmentFilterBar(props: SegmentFilterBarProps) {
  return (
    <section>
      <label>
        股票代码过滤
        <input value={props.stockCode} onChange={(event) => props.onStockCodeChange(event.target.value)} />
      </label>
      <label>
        波段类型过滤
        <input value={props.segmentType} onChange={(event) => props.onSegmentTypeChange(event.target.value)} />
      </label>
      <label>
        标签过滤
        <input value={props.label} onChange={(event) => props.onLabelChange(event.target.value)} />
      </label>
    </section>
  );
}
