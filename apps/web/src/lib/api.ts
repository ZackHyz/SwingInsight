const API_BASE = (import.meta as { env?: { VITE_API_BASE?: string } }).env?.VITE_API_BASE ?? "/api";

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
  volume?: number | null;
};

export type SimilarCase = {
  segment_id: number;
  stock_code: string;
  score: number;
  price_score?: number;
  volume_score?: number;
  turnover_score?: number;
  pattern_score?: number;
  pct_change: number | null;
  return_1d?: number | null;
  return_3d?: number | null;
  return_5d?: number | null;
  return_10d?: number | null;
  start_date?: string;
  end_date?: string;
};

export type SegmentChartWindowData = {
  segment: {
    id: number;
    stock_code: string;
    start_date: string;
    end_date: string;
  };
  highlight_range: {
    start_date: string;
    end_date: string;
  };
  prices: PriceRow[];
  auto_turning_points: StockPoint[];
  final_turning_points: StockPoint[];
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
  trade_markers: Array<{
    id?: number;
    trade_date: string;
    trade_type: string;
    price: number;
    quantity?: number;
    strategy_tag?: string | null;
    note?: string | null;
  }>;
  news_items: Array<{
    news_id: number;
    title: string;
    summary: string | null;
    source_name: string | null;
    news_date: string | null;
  }>;
  current_state: {
    label: string;
    summary: string;
    probabilities?: Record<string, number>;
    key_features?: Record<string, number>;
    risk_flags?: Record<string, string>;
    similar_cases?: SimilarCase[];
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
  auto_turning_points: StockPoint[];
  final_turning_points: StockPoint[];
  rebuild_summary: {
    segments: number;
    features: number;
    predictions: number;
    version_code: string;
  };
  current_state: StockResearchData["current_state"] | null;
};

export type ApiClient = {
  getStockResearch: (stockCode: string) => Promise<StockResearchData>;
  commitTurningPoints: (stockCode: string, payload: TurningPointCommitPayload) => Promise<TurningPointCommitResponse>;
  getSegmentChartWindow: (segmentId: string) => Promise<SegmentChartWindowData>;
  getSegmentDetail: (segmentId: string) => Promise<SegmentDetailData>;
  getSegmentLibrary: () => Promise<SegmentLibraryData>;
  getPrediction: (stockCode: string, predictDate: string) => Promise<PredictionData>;
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

export type PredictionData = {
  stock_code: string;
  predict_date: string;
  current_state: string;
  summary: string;
  probabilities: Record<string, number>;
  key_features: Record<string, number>;
  risk_flags: Record<string, string>;
  similar_cases: SimilarCase[];
};

export const apiClient: ApiClient = {
  async getStockResearch(stockCode) {
    const response = await fetch(`${API_BASE}/stocks/${stockCode}`);
    if (!response.ok) {
      throw new Error(`Failed to load stock research: ${response.status}`);
    }
    return (await response.json()) as StockResearchData;
  },
  async commitTurningPoints(stockCode, payload) {
    const response = await fetch(`${API_BASE}/stocks/${stockCode}/turning-points/commit`, {
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
  async getSegmentChartWindow(segmentId) {
    const response = await fetch(`${API_BASE}/segments/${segmentId}/chart`);
    if (!response.ok) {
      throw new Error(`Failed to load segment chart window: ${response.status}`);
    }
    return (await response.json()) as SegmentChartWindowData;
  },
  async getSegmentDetail(segmentId) {
    const response = await fetch(`${API_BASE}/segments/${segmentId}`);
    if (!response.ok) {
      throw new Error(`Failed to load segment detail: ${response.status}`);
    }
    return (await response.json()) as SegmentDetailData;
  },
  async getSegmentLibrary() {
    const response = await fetch(`${API_BASE}/library`);
    if (!response.ok) {
      throw new Error(`Failed to load segment library: ${response.status}`);
    }
    return (await response.json()) as SegmentLibraryData;
  },
  async getPrediction(stockCode, predictDate) {
    const response = await fetch(`${API_BASE}/predictions/${stockCode}?predict_date=${predictDate}`);
    if (!response.ok) {
      throw new Error(`Failed to load prediction: ${response.status}`);
    }
    return (await response.json()) as PredictionData;
  },
};
