import { SimilarCaseList } from "./similar-case-list";
import type { StockResearchData } from "../lib/api";

type PredictionPanelProps = {
  currentState: StockResearchData["current_state"];
};

export function PredictionPanel({ currentState }: PredictionPanelProps) {
  const probabilities = currentState.probabilities ?? {};
  const keyFeatures = currentState.key_features ?? {};
  const riskFlags = currentState.risk_flags ?? {};
  const similarCases = currentState.similar_cases ?? [];

  return (
    <aside>
      <h2>预测面板</h2>
      <p>当前状态: {currentState.label}</p>
      <p>{currentState.summary}</p>
      <section>
        <h3>方向概率</h3>
        <ul>
          {Object.entries(probabilities).map(([key, value]) => (
            <li key={key}>
              {key} {(value * 100).toFixed(1)}%
            </li>
          ))}
        </ul>
      </section>
      <section>
        <h3>关键触发特征</h3>
        <ul>
          {Object.entries(keyFeatures).map(([key, value]) => (
            <li key={key}>
              {key} {value}
            </li>
          ))}
        </ul>
      </section>
      <section>
        <h3>风险提示</h3>
        <ul>
          {Object.entries(riskFlags).map(([key, value]) => (
            <li key={key}>
              {key}: {value}
            </li>
          ))}
        </ul>
      </section>
      <SimilarCaseList items={similarCases} />
    </aside>
  );
}
