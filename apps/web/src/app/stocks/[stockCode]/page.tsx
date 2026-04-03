"use client";

import { useEffect, useState, type FormEvent } from "react";

import { PredictionPanel } from "../../../components/prediction-panel";
import { TurningPointEditor } from "../../../components/turning-point-editor";
import { apiClient, type ApiClient, type StockResearchData } from "../../../lib/api";

type StockResearchPageProps = {
  stockCode?: string;
  initialData?: StockResearchData;
  apiClient?: ApiClient;
};

function resolveStockCodeFromPath(pathname: string, fallback: string): string {
  const match = pathname.match(/^\/stocks\/([^/]+)$/);
  return match?.[1] ?? fallback;
}

export default function StockResearchPage(props: StockResearchPageProps) {
  const initialStockCode = props.stockCode ?? "600157";
  const client = props.apiClient ?? apiClient;
  const [activeStockCode, setActiveStockCode] = useState(initialStockCode);
  const [searchCode, setSearchCode] = useState(initialStockCode);
  const [pageData, setPageData] = useState<StockResearchData | null>(props.initialData ?? null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [reloadVersion, setReloadVersion] = useState(0);

  useEffect(() => {
    setActiveStockCode(initialStockCode);
    setSearchCode(initialStockCode);
    setPageData(props.initialData ?? null);
    setLoadError(null);
    setReloadVersion(0);
  }, [initialStockCode, props.initialData]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    const handlePopState = () => {
      const nextStockCode = resolveStockCodeFromPath(window.location.pathname, initialStockCode);
      setSearchCode(nextStockCode);
      setActiveStockCode(nextStockCode);
      setPageData(null);
      setLoadError(null);
      setReloadVersion((current) => current + 1);
    };
    window.addEventListener("popstate", handlePopState);
    return () => {
      window.removeEventListener("popstate", handlePopState);
    };
  }, [initialStockCode]);

  useEffect(() => {
    if (props.initialData !== undefined && activeStockCode === initialStockCode && reloadVersion === 0) {
      setPageData(props.initialData);
      setLoadError(null);
      return;
    }
    let cancelled = false;
    setPageData(null);
    setLoadError(null);
    client
      .getStockResearch(activeStockCode)
      .then((data) => {
        if (!cancelled) {
          setPageData(data);
          setLoadError(null);
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          const message = error instanceof Error ? error.message : "Failed to load stock research";
          setLoadError(message);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [activeStockCode, client, initialStockCode, props.initialData, reloadVersion]);

  function handleSearchSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedCode = searchCode.trim();
    if (!/^\d{6}$/.test(normalizedCode)) {
      setLoadError("请输入 6 位股票代码");
      return;
    }
    if (typeof window !== "undefined") {
      const nextPath = `/stocks/${normalizedCode}`;
      if (window.location.pathname !== nextPath) {
        window.history.pushState({}, "", nextPath);
      }
    }
    setSearchCode(normalizedCode);
    setPageData(null);
    setLoadError(null);
    setActiveStockCode(normalizedCode);
    setReloadVersion((current) => current + 1);
  }

  const isLoading = pageData === null && loadError === null;

  function resolveNewsBadge(item: StockResearchData["news_items"][number]): string {
    if (item.category === "announcement" || item.source_type === "announcement") {
      return "公告";
    }
    return "资讯";
  }

  function resolveNewsTagStyle(tag: string) {
    if (tag === "公告") {
      return { color: "#9a3412", background: "#fed7aa" };
    }
    if (tag === "资讯") {
      return { color: "#1d4ed8", background: "#dbeafe" };
    }
    if (tag === "利多") {
      return { color: "#166534", background: "#dcfce7" };
    }
    if (tag === "利空") {
      return { color: "#991b1b", background: "#fee2e2" };
    }
    if (tag === "中性") {
      return { color: "#374151", background: "#e5e7eb" };
    }
    if (tag.includes("顶部") || tag.includes("底部")) {
      return { color: "#155e75", background: "#cffafe" };
    }
    if (tag.includes("波段")) {
      return { color: "#92400e", background: "#fde68a" };
    }
    return { color: "#6b7280", background: "#f3f4f6" };
  }

  function formatMetricValue(value: number | undefined) {
    if (value === undefined) {
      return "--";
    }
    const rounded = Math.round(value * 100) / 100;
    return Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(2);
  }

  return (
    <main
      style={{
        maxWidth: 1440,
        margin: "0 auto",
        padding: "24px 20px 48px",
        display: "grid",
        gap: 24,
        background: "linear-gradient(180deg, #f8f3e6 0%, #fffdf8 35%, #ffffff 100%)",
      }}
    >
      <section
        style={{
          display: "grid",
          gap: 12,
          padding: 20,
          borderRadius: 20,
          border: "1px solid #e7dcc8",
          background: "rgba(255, 251, 243, 0.92)",
          boxShadow: "0 18px 48px rgba(30, 20, 10, 0.08)",
        }}
      >
        <form onSubmit={handleSearchSubmit} style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "end" }}>
          <label style={{ display: "grid", gap: 8, minWidth: 220 }}>
            <span style={{ fontWeight: 600, color: "#3f3a32" }}>股票代码搜索</span>
            <input
              aria-label="股票代码搜索"
              value={searchCode}
              onChange={(event) => setSearchCode(event.target.value)}
              inputMode="numeric"
              maxLength={6}
              placeholder="例如 600157"
              style={{
                padding: "12px 14px",
                borderRadius: 12,
                border: "1px solid #d6cbb7",
                fontSize: 16,
                background: "#fffdf8",
                color: "#1f2937",
              }}
            />
          </label>
          <button
            type="submit"
            disabled={isLoading}
            style={{
              padding: "12px 20px",
              borderRadius: 12,
              border: "none",
              background: isLoading ? "#d6cbb7" : "#b45309",
              color: "#fffdf8",
              fontWeight: 700,
              cursor: isLoading ? "not-allowed" : "pointer",
            }}
          >
            {isLoading ? "搜索中..." : "搜索"}
          </button>
        </form>
        <p style={{ margin: 0, color: "#6b7280" }}>输入 6 位股票代码后，页面会重新获取真实日 K、拐点和预测数据。</p>
        {loadError !== null && pageData !== null ? (
          <p style={{ margin: 0, color: "#b91c1c", fontWeight: 600 }}>{loadError}</p>
        ) : null}
      </section>

      {pageData === null ? (
        <section
          style={{
            padding: 24,
            borderRadius: 20,
            border: "1px solid #e7dcc8",
            background: "#fffdf8",
            boxShadow: "0 18px 48px rgba(30, 20, 10, 0.06)",
          }}
        >
          <h1>{loadError === null ? "正在加载真实行情数据..." : "加载失败"}</h1>
          <p>{loadError ?? `${activeStockCode} 的日线、拐点和预测结果会在接口返回后显示。`}</p>
        </section>
      ) : (
        <>
          <section
            style={{
              display: "flex",
              justifyContent: "space-between",
              gap: 16,
              flexWrap: "wrap",
              padding: 20,
              borderRadius: 20,
              border: "1px solid #e7dcc8",
              background: "rgba(255, 251, 243, 0.92)",
              boxShadow: "0 18px 48px rgba(30, 20, 10, 0.08)",
            }}
          >
            <div>
              <h1>
                {pageData.stock.stock_name} ({pageData.stock.stock_code})
              </h1>
              {pageData.stock.industry ? (
                <p>
                  {pageData.stock.market} / {pageData.stock.industry}
                </p>
              ) : null}
              <p>当前状态: {pageData.current_state.label}</p>
            </div>
            <div style={{ minWidth: 280, color: "#6b7280" }}>
              <p>区间样本: {pageData.prices.length} 根日K</p>
              <p>新闻事件: {pageData.news_items.length} 条</p>
              <p>交易记录: {pageData.trade_markers.length} 条</p>
            </div>
          </section>

          <section style={{ display: "grid", gridTemplateColumns: "minmax(0, 2fr) minmax(320px, 1fr)", gap: 24, alignItems: "start" }}>
            <div style={{ minWidth: 0 }}>
              <TurningPointEditor
                stockCode={activeStockCode}
                initialData={pageData}
                apiClient={client}
                onCommitSuccess={(response) =>
                  setPageData((current) => ({
                    ...(current ?? pageData),
                    auto_turning_points: response.auto_turning_points,
                    final_turning_points: response.final_turning_points,
                    current_state: response.current_state ?? (current ?? pageData).current_state,
                  }))
                }
              />
            </div>
            <div
              style={{
                padding: 20,
                borderRadius: 20,
                border: "1px solid #e7dcc8",
                background: "#fffdf8",
                boxShadow: "0 18px 48px rgba(30, 20, 10, 0.08)",
                position: "sticky",
                top: 20,
              }}
            >
              <PredictionPanel
                apiClient={client}
                stockCode={activeStockCode}
                prices={pageData.prices}
                autoPoints={pageData.auto_turning_points}
                finalPoints={pageData.final_turning_points}
                currentState={pageData.current_state}
              />
            </div>
          </section>

          <section
            style={{
              padding: 20,
              borderRadius: 20,
              border: "1px solid #e7dcc8",
              background: "#fffdf8",
              boxShadow: "0 18px 48px rgba(30, 20, 10, 0.06)",
            }}
          >
            <h2>相关新闻</h2>
            {pageData.current_state.news_summary ? (
              <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 16 }}>
                <span
                  style={{
                    padding: "6px 10px",
                    borderRadius: 999,
                    background: "#f3efe6",
                    color: "#5b4632",
                    fontSize: 13,
                    fontWeight: 700,
                  }}
                >
                  窗口新闻 {formatMetricValue(pageData.current_state.news_summary.window_news_count)}
                </span>
                <span
                  style={{
                    padding: "6px 10px",
                    borderRadius: 999,
                    background: "#fff1e6",
                    color: "#9a3412",
                    fontSize: 13,
                    fontWeight: 700,
                  }}
                >
                  公告 {formatMetricValue(pageData.current_state.news_summary.announcement_count)}
                </span>
                <span
                  style={{
                    padding: "6px 10px",
                    borderRadius: 999,
                    background: "#e0f2fe",
                    color: "#0c4a6e",
                    fontSize: 13,
                    fontWeight: 700,
                  }}
                >
                  修正情绪 {formatMetricValue(pageData.current_state.news_summary.avg_adjusted_sentiment)}
                </span>
                <span
                  style={{
                    padding: "6px 10px",
                    borderRadius: 999,
                    background: "#dcfce7",
                    color: "#166534",
                    fontSize: 13,
                    fontWeight: 700,
                  }}
                >
                  正向事件 {formatMetricValue(pageData.current_state.news_summary.positive_event_count)}
                </span>
                <span
                  style={{
                    padding: "6px 10px",
                    borderRadius: 999,
                    background: "#fee2e2",
                    color: "#991b1b",
                    fontSize: 13,
                    fontWeight: 700,
                  }}
                >
                  负向事件 {formatMetricValue(pageData.current_state.news_summary.negative_event_count)}
                </span>
                <span
                  style={{
                    padding: "6px 10px",
                    borderRadius: 999,
                    background: "#ede9fe",
                    color: "#5b21b6",
                    fontSize: 13,
                    fontWeight: 700,
                  }}
                >
                  治理事件 {formatMetricValue(pageData.current_state.news_summary.governance_event_count)}
                </span>
              </div>
            ) : null}
            <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "grid", gap: 12 }}>
              {pageData.news_items.map((item) => (
                (() => {
                  const tags = item.display_tags && item.display_tags.length > 0 ? item.display_tags : [resolveNewsBadge(item)];
                  return (
                <li
                  key={item.news_id}
                  style={{
                    display: "grid",
                    gap: 6,
                    padding: 14,
                    borderRadius: 14,
                    border: "1px solid #eadfca",
                    background: item.category === "announcement" ? "#fff7ed" : "#fffcf5",
                  }}
                >
                  <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
                    {tags.map((tag) => {
                      const tagStyle = resolveNewsTagStyle(tag);
                      return (
                        <span
                          key={`${item.news_id}-${tag}`}
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            padding: "2px 8px",
                            borderRadius: 999,
                            fontSize: 12,
                            fontWeight: 700,
                            color: tagStyle.color,
                            background: tagStyle.background,
                          }}
                        >
                          {tag}
                        </span>
                      );
                    })}
                    <span style={{ color: "#6b7280", fontSize: 13 }}>
                      {[item.source_name ?? "未知来源", item.news_date ?? "unknown-date"].join(" · ")}
                    </span>
                  </div>
                  <strong>{item.title}</strong>
                  {item.event_types && item.event_types.length > 0 ? (
                    <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
                      {item.event_types.map((eventType) => (
                        <span
                          key={`${item.news_id}-${eventType}`}
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            padding: "2px 8px",
                            borderRadius: 999,
                            fontSize: 12,
                            fontWeight: 700,
                            color: "#4338ca",
                            background: "#e0e7ff",
                          }}
                        >
                          {eventType}
                        </span>
                      ))}
                      {typeof item.sentiment_score_adjusted === "number" ? (
                        <span style={{ color: "#6b7280", fontSize: 13, fontWeight: 600 }}>
                          修正后情绪 {item.sentiment_score_adjusted.toFixed(2)}
                        </span>
                      ) : null}
                      {item.event_conflict_flag ? (
                        <span
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            padding: "2px 8px",
                            borderRadius: 999,
                            fontSize: 12,
                            fontWeight: 700,
                            color: "#7c2d12",
                            background: "#ffedd5",
                          }}
                        >
                          事件冲突
                        </span>
                      ) : null}
                    </div>
                  ) : typeof item.sentiment_score_adjusted === "number" ? (
                    <div style={{ color: "#6b7280", fontSize: 13, fontWeight: 600 }}>
                      修正后情绪 {item.sentiment_score_adjusted.toFixed(2)}
                    </div>
                  ) : null}
                  {item.summary ? <p style={{ margin: 0, color: "#4b5563", lineHeight: 1.6 }}>{item.summary}</p> : null}
                </li>
                  );
                })()
              ))}
            </ul>
          </section>
        </>
      )}
    </main>
  );
}
