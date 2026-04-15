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
  candle_score?: number | null;
  trend_score?: number | null;
  vola_score?: number | null;
  pct_change: number | null;
  return_1d?: number | null;
  return_3d?: number | null;
  return_5d?: number | null;
  return_10d?: number | null;
  start_date?: string;
  end_date?: string;
  window_id?: number | null;
  window_start_date?: string | null;
  window_end_date?: string | null;
  window_size?: number | null;
  segment_start_date?: string | null;
  segment_end_date?: string | null;
};

export type QueryWindow = {
  window_id?: number | null;
  segment_id?: number | null;
  start_date: string;
  end_date: string;
  window_size?: number | null;
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
    source_type?: string | null;
    news_date: string | null;
    category?: string | null;
    sub_category?: string | null;
    sentiment?: string | null;
    display_tags?: string[];
    sentiment_score_adjusted?: number | null;
    event_types?: string[];
    event_conflict_flag?: boolean;
  }>;
  current_state: {
    label: string;
    summary: string;
    probabilities?: Record<string, number>;
    key_features?: Record<string, number>;
    risk_flags?: Record<string, string>;
    similar_cases?: SimilarCase[];
    query_window?: QueryWindow | null;
    group_stat?: {
      sample_count?: number;
      future_1d_mean?: number;
      future_1d_median?: number;
      future_1d_win_rate?: number;
      future_3d_mean?: number;
      future_5d_mean?: number;
      future_10d_mean?: number;
      future_5d_max_dd_median?: number;
      future_10d_max_dd_median?: number;
    };
    news_summary?: {
      window_news_count?: number;
      announcement_count?: number;
      positive_news_ratio?: number;
      high_heat_count?: number;
      avg_adjusted_sentiment?: number;
      positive_event_count?: number;
      negative_event_count?: number;
      governance_event_count?: number;
    };
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
  getPatternScore?: (stockCode: string) => Promise<PatternScoreData>;
  getPatternSimilarCases?: (stockCode: string) => Promise<PatternSimilarCaseData[]>;
  getPatternGroupStat?: (stockCode: string) => Promise<PatternGroupStatData>;
};

export type PatternScoreData = {
  horizon_days: number;
  raw_win_rate?: number;
  win_rate_5d?: number;
  win_rate_10d?: number;
  win_rate: number;
  avg_return: number;
  sample_count: number;
  confidence: "low" | "medium" | "high";
  calibrated?: boolean;
};

export type PatternSimilarCaseData = {
  window_id?: number | null;
  window_start_date?: string | null;
  window_end_date?: string | null;
  segment_start_date?: string | null;
  segment_end_date?: string | null;
  similarity_score: number;
  future_return_5d?: number | null;
  future_return_10d?: number | null;
  stock_code?: string | null;
  segment_id?: number | null;
};

export type PatternGroupStatData = {
  horizon_days: number[];
  win_rates: number[];
  avg_returns: number[];
  sample_counts: number[];
  return_distribution: number[];
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
  query_window?: QueryWindow | null;
  group_stat?: StockResearchData["current_state"]["group_stat"];
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
  async getPatternScore(stockCode) {
    const response = await fetch(`${API_BASE}/stocks/${stockCode}/pattern-score`);
    if (!response.ok) {
      throw new Error(`Failed to load pattern score: ${response.status}`);
    }
    return (await response.json()) as PatternScoreData;
  },
  async getPatternSimilarCases(stockCode) {
    const response = await fetch(`${API_BASE}/stocks/${stockCode}/similar-cases`);
    if (!response.ok) {
      throw new Error(`Failed to load similar cases: ${response.status}`);
    }
    return (await response.json()) as PatternSimilarCaseData[];
  },
  async getPatternGroupStat(stockCode) {
    const response = await fetch(`${API_BASE}/stocks/${stockCode}/group-stat`);
    if (!response.ok) {
      throw new Error(`Failed to load group stat: ${response.status}`);
    }
    return (await response.json()) as PatternGroupStatData;
  },
};
