import { useEffect, useState } from "react";

import type { PatternGroupStatData, PatternScoreData, PatternSimilarCaseData } from "../lib/api";

export type PatternInsightState = {
  score: PatternScoreData | null;
  similarCases: PatternSimilarCaseData[];
  groupStat: PatternGroupStatData | null;
};

type PatternInsightStatus = "idle" | "loading" | "ready" | "error";

type PatternInsightClient = {
  getPatternScore?: (stockCode: string) => Promise<PatternScoreData>;
  getPatternSimilarCases?: (stockCode: string) => Promise<PatternSimilarCaseData[]>;
  getPatternGroupStat?: (stockCode: string) => Promise<PatternGroupStatData>;
};

export function usePatternInsight(stockCode: string, apiClient: PatternInsightClient) {
  const [data, setData] = useState<PatternInsightState>({
    score: null,
    similarCases: [],
    groupStat: null,
  });
  const [status, setStatus] = useState<PatternInsightStatus>("idle");
  const [selectedCaseId, setSelectedCaseId] = useState<number | null>(null);

  useEffect(() => {
    if (!stockCode || apiClient.getPatternScore === undefined || apiClient.getPatternSimilarCases === undefined || apiClient.getPatternGroupStat === undefined) {
      setStatus("error");
      setData({
        score: null,
        similarCases: [],
        groupStat: null,
      });
      setSelectedCaseId(null);
      return;
    }

    let cancelled = false;
    setStatus("loading");
    Promise.all([
      apiClient.getPatternScore(stockCode),
      apiClient.getPatternSimilarCases(stockCode),
      apiClient.getPatternGroupStat(stockCode),
    ])
      .then(([score, similarCases, groupStat]) => {
        if (cancelled) {
          return;
        }
        setData({
          score,
          similarCases,
          groupStat,
        });
        setSelectedCaseId((current) => {
          if (current === null) {
            return similarCases[0]?.window_id ?? null;
          }
          return similarCases.some((item) => item.window_id === current) ? current : (similarCases[0]?.window_id ?? null);
        });
        setStatus("ready");
      })
      .catch(() => {
        if (!cancelled) {
          setStatus("error");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [stockCode, apiClient]);

  return {
    data,
    status,
    selectedCaseId,
    setSelectedCaseId,
  };
}
