type TradeMarkerLayerProps = {
  count: number;
};

export function TradeMarkerLayer({ count }: TradeMarkerLayerProps) {
  return <p>历史买卖点占位: {count}</p>;
}
