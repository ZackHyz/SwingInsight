export type StockPoint = {
  id?: number;
  point_date: string;
  point_type: "peak" | "trough";
  point_price: number;
  source_type?: string;
};

export type PriceRow = {
  trade_date: string;
  open_price: number;
  high_price: number;
  low_price: number;
  close_price: number;
};

export type StockResearchData = {
  stock: {
    stock_code: string;
    stock_name: string;
    market: string;
    industry: string | null;
    concept_tags: string[];
  };
  prices: PriceRow[];
  auto_turning_points: StockPoint[];
  final_turning_points: StockPoint[];
  trade_markers: Array<Record<string, unknown>>;
  current_state: {
    label: string;
    summary: string;
  };
};

export type TurningPointCommitPayload = {
  operator?: string;
  operations: Array<{
    operation_type: string;
    old_value: Record<string, unknown> | null;
    new_value: Record<string, unknown> | null;
  }>;
  final_points: Array<{
    point_date: string;
    point_type: "peak" | "trough";
    point_price: number;
  }>;
};

export type TurningPointCommitResponse = {
  final_turning_points: StockPoint[];
  rebuild_summary: {
    segments: number;
    version_code: string;
  };
};

export type ApiClient = {
  getStockResearch: (stockCode: string) => Promise<StockResearchData>;
  commitTurningPoints: (stockCode: string, payload: TurningPointCommitPayload) => Promise<TurningPointCommitResponse>;
};

export const apiClient: ApiClient = {
  async getStockResearch(stockCode) {
    const response = await fetch(`http://127.0.0.1:8000/stocks/${stockCode}`);
    if (!response.ok) {
      throw new Error(`Failed to load stock research: ${response.status}`);
    }
    return (await response.json()) as StockResearchData;
  },
  async commitTurningPoints(stockCode, payload) {
    const response = await fetch(`http://127.0.0.1:8000/stocks/${stockCode}/turning-points/commit`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      throw new Error(`Failed to save turning points: ${response.status}`);
    }
    return (await response.json()) as TurningPointCommitResponse;
  },
};
