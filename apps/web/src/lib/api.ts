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
  getSegmentDetail: (segmentId: string) => Promise<SegmentDetailData>;
  getSegmentLibrary: () => Promise<SegmentLibraryData>;
};

export type SegmentDetailData = {
  segment: {
    id: number;
    stock_code: string;
    trend_direction: string | null;
    start_date: string;
    end_date: string;
    start_price: number;
    end_price: number;
    pct_change: number | null;
    duration_days: number | null;
    max_drawdown_pct: number | null;
    max_upside_pct: number | null;
    avg_daily_change_pct: number | null;
  };
  news_timeline: Array<{
    news_id: number;
    title: string;
    summary: string | null;
    source_name: string | null;
    relation_type: string;
    distance_days: number | null;
    news_date: string | null;
  }>;
  labels: Array<{
    label_type: string;
    label_name: string;
    label_value: string | null;
  }>;
};

export type SegmentLibraryData = {
  rows: Array<{
    id: number;
    stock_code: string;
    segment_type: string | null;
    label_names: string[];
    pct_change: number | null;
    duration_days: number | null;
  }>;
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
  async getSegmentDetail(segmentId) {
    const response = await fetch(`http://127.0.0.1:8000/segments/${segmentId}`);
    if (!response.ok) {
      throw new Error(`Failed to load segment detail: ${response.status}`);
    }
    return (await response.json()) as SegmentDetailData;
  },
  async getSegmentLibrary() {
    const response = await fetch("http://127.0.0.1:8000/library");
    if (!response.ok) {
      throw new Error(`Failed to load segment library: ${response.status}`);
    }
    return (await response.json()) as SegmentLibraryData;
  },
};
