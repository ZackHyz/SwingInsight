"use client";

import { PredictionPanel } from "../../../components/prediction-panel";
import { TurningPointEditor } from "../../../components/turning-point-editor";
import { apiClient, type ApiClient, type StockResearchData } from "../../../lib/api";

type StockResearchPageProps = {
  stockCode?: string;
  initialData?: StockResearchData;
  apiClient?: ApiClient;
};

function buildFallbackData(stockCode: string): StockResearchData {
  return {
    stock: {
      stock_code: stockCode,
      stock_name: "SwingInsight Demo",
      market: "A",
      industry: "Demo",
      concept_tags: [],
    },
    prices: [
      { trade_date: "2024-01-02", open_price: 10, high_price: 10.2, low_price: 9.8, close_price: 10 },
      { trade_date: "2024-01-03", open_price: 9.8, high_price: 9.9, low_price: 9.2, close_price: 9.4 },
      { trade_date: "2024-01-04", open_price: 9.2, high_price: 9.3, low_price: 8.7, close_price: 8.8 },
    ],
    auto_turning_points: [],
    final_turning_points: [],
    trade_markers: [],
    current_state: {
      label: "placeholder",
      summary: "Prediction pending",
      probabilities: {},
      key_features: {},
      risk_flags: {},
      similar_cases: [],
    },
  };
}

export default function StockResearchPage(props: StockResearchPageProps) {
  const stockCode = props.stockCode ?? "000001";
  const pageData = props.initialData ?? buildFallbackData(stockCode);
  const client = props.apiClient ?? apiClient;

  return (
    <main>
      <section>
        <h1>
          {pageData.stock.stock_name} ({pageData.stock.stock_code})
        </h1>
        <p>
          {pageData.stock.market} / {pageData.stock.industry ?? "Unknown"}
        </p>
        <p>当前状态: {pageData.current_state.label}</p>
      </section>

      <PredictionPanel currentState={pageData.current_state} />

      <TurningPointEditor stockCode={stockCode} initialData={pageData} apiClient={client} />
    </main>
  );
}
