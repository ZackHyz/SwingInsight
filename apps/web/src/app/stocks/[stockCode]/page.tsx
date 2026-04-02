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
              <p>
                {pageData.stock.market} / {pageData.stock.industry ?? "Unknown"}
              </p>
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
            <ul>
              {pageData.news_items.map((item) => (
                <li key={item.news_id}>
                  <strong>{item.title}</strong> <span>{item.news_date ?? "unknown-date"}</span>
                </li>
              ))}
            </ul>
          </section>
        </>
      )}
    </main>
  );
}
