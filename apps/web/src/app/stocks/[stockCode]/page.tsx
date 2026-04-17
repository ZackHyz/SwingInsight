"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";

import { AppShell } from "../../../components/app-shell";
import { PredictionPanel } from "../../../components/prediction-panel";
import { StatusPill } from "../../../components/status-pill";
import { TerminalPanel } from "../../../components/terminal-panel";
import { TurningPointEditor } from "../../../components/turning-point-editor";
import { useRefreshStatus } from "../../../hooks/use-refresh-status";
import { apiClient, type ApiClient, type StockRefreshStatusData, type StockResearchData } from "../../../lib/api";
import { formatShanghaiDateTime } from "../../../lib/datetime";
import { getSignedTone, getStateTone } from "../../../lib/market-tone";

type StockResearchPageProps = {
  stockCode?: string;
  initialData?: StockResearchData;
  apiClient?: ApiClient;
};

function resolveStockCodeFromPath(pathname: string, fallback: string): string {
  const match = pathname.match(/^\/stocks\/([^/]+)$/);
  return match?.[1] ?? fallback;
}

function resolveNewsBadge(item: StockResearchData["news_items"][number]): string {
  if (item.category === "announcement" || item.source_type === "announcement") {
    return "公告";
  }
  return "资讯";
}

function resolveNewsTagStyle(tag: string) {
  if (tag === "公告") {
    return { color: "#ffbf7a", background: "rgba(154, 52, 18, 0.18)" };
  }
  if (tag === "资讯") {
    return { color: "#85b8ff", background: "rgba(29, 78, 216, 0.16)" };
  }
  if (tag === "利多") {
    return { color: "#ff9fac", background: "rgba(153, 27, 27, 0.22)" };
  }
  if (tag === "利空") {
    return { color: "#7ef0c3", background: "rgba(22, 101, 52, 0.18)" };
  }
  if (tag === "中性") {
    return { color: "#d3dcf8", background: "rgba(107, 114, 128, 0.2)" };
  }
  if (tag.includes("顶部")) {
    return { color: "#7ef0c3", background: "rgba(22, 101, 52, 0.18)" };
  }
  if (tag.includes("底部")) {
    return { color: "#ff9fac", background: "rgba(153, 27, 27, 0.22)" };
  }
  if (tag.includes("波段")) {
    return { color: "#ffcf7d", background: "rgba(146, 64, 14, 0.18)" };
  }
  return { color: "#c3d0f6", background: "rgba(255, 255, 255, 0.06)" };
}

function formatMetricValue(value: number | undefined) {
  if (value === undefined) {
    return "--";
  }
  const rounded = Math.round(value * 100) / 100;
  return Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(2);
}

function resolveCountTone(count: number | undefined, tone: "success" | "danger"): "default" | "success" | "danger" {
  if (count === undefined || count <= 0) {
    return "default";
  }
  return tone;
}

function resolveRefreshTone(status: StockRefreshStatusData["status"] | undefined): "default" | "success" | "warning" | "danger" {
  if (status === "success") {
    return "success";
  }
  if (status === "failed") {
    return "danger";
  }
  if (status === "running" || status === "queued" || status === "partial") {
    return "warning";
  }
  return "default";
}

function resolveRefreshLabel(status: StockRefreshStatusData["status"] | undefined): string {
  if (status === "queued") {
    return "排队中";
  }
  if (status === "running") {
    return "刷新中";
  }
  if (status === "success") {
    return "已完成";
  }
  if (status === "failed") {
    return "失败";
  }
  if (status === "partial") {
    return "部分完成";
  }
  return "暂无记录";
}

function formatRefreshTime(value: string | null | undefined): string {
  return formatShanghaiDateTime(value);
}

export default function StockResearchPage(props: StockResearchPageProps) {
  const initialStockCode = props.stockCode ?? "";
  const client = props.apiClient ?? apiClient;
  const [activeStockCode, setActiveStockCode] = useState(initialStockCode);
  const [searchCode, setSearchCode] = useState(initialStockCode);
  const [pageData, setPageData] = useState<StockResearchData | null>(props.initialData ?? null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [reloadVersion, setReloadVersion] = useState(0);
  const refreshStatus = useRefreshStatus(activeStockCode, client);
  const requestedRefreshStockCodeRef = useRef<string | null>(null);
  const appliedRefreshSyncKeyRef = useRef<string | null>(null);

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
    if (!/^\d{6}$/.test(activeStockCode)) {
      setPageData(null);
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
          const message = error instanceof Error ? error.message : "加载研究数据失败";
          setLoadError(message);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [activeStockCode, client, initialStockCode, props.initialData, reloadVersion]);

  useEffect(() => {
    const startRefresh = client.startStockRefresh;
    if (!activeStockCode || startRefresh === undefined) {
      return;
    }
    if (requestedRefreshStockCodeRef.current === activeStockCode) {
      return;
    }

    requestedRefreshStockCodeRef.current = activeStockCode;
    startRefresh(activeStockCode).catch(() => {
      requestedRefreshStockCodeRef.current = null;
    });
  }, [activeStockCode, client]);

  useEffect(() => {
    const status = refreshStatus.data?.status;
    const syncTime = refreshStatus.data?.end_time ?? refreshStatus.data?.updated_at ?? null;
    if (requestedRefreshStockCodeRef.current !== activeStockCode) {
      return;
    }
    if ((status !== "success" && status !== "partial") || syncTime === null) {
      return;
    }
    const syncKey = `${refreshStatus.data?.task_id ?? "none"}:${syncTime}`;
    if (appliedRefreshSyncKeyRef.current === syncKey) {
      return;
    }
    appliedRefreshSyncKeyRef.current = syncKey;
    setPageData(null);
    setLoadError(null);
    setReloadVersion((current) => current + 1);
  }, [refreshStatus.data]);

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

  const hasActiveStockCode = /^\d{6}$/.test(activeStockCode);
  const isLoading = hasActiveStockCode && pageData === null && loadError === null;
  const shellTitle = pageData === null ? (hasActiveStockCode ? `研究台 ${activeStockCode}` : "研究台") : `${pageData.stock.stock_name} (${pageData.stock.stock_code})`;
  const shellSubtitle =
    pageData === null
      ? hasActiveStockCode
        ? "研究工作台正在同步图表上下文、拐点修正和预测洞察。"
        : "输入股票代码并点击搜索后开始加载研究数据。"
      : `${pageData.stock.market} ${pageData.stock.industry ? `/ ${pageData.stock.industry}` : ""} · 当前状态 ${pageData.current_state.label}`;
  const refreshPillLabel = refreshStatus.error
    ? "最近刷新 查询失败"
    : `最近刷新 ${resolveRefreshLabel(refreshStatus.data?.status)} ${formatRefreshTime(
        refreshStatus.data?.end_time ?? refreshStatus.data?.updated_at,
      )}`;
  const refreshPillTone = refreshStatus.loading ? "warning" : resolveRefreshTone(refreshStatus.data?.status);

  return (
    <AppShell
      currentPath={hasActiveStockCode ? `/stocks/${activeStockCode}` : "/stocks"}
      title={shellTitle}
      subtitle={shellSubtitle}
      topBarContent={
        <>
          <form className="terminal-form" onSubmit={handleSearchSubmit}>
            <label className="terminal-field">
              <span className="sr-only">股票代码搜索</span>
              <input
                aria-label="股票代码搜索"
                value={searchCode}
                onChange={(event) => setSearchCode(event.target.value)}
                inputMode="numeric"
                maxLength={6}
                placeholder="例如 600157"
              />
            </label>
            <button className="terminal-button terminal-button--primary" type="submit" disabled={isLoading}>
              {isLoading ? "搜索中..." : "搜索"}
            </button>
          </form>
          <StatusPill label={isLoading ? "工作台同步中" : hasActiveStockCode ? "研究已就绪" : "待输入代码"} tone={isLoading ? "warning" : "default"} />
          {hasActiveStockCode ? <StatusPill label={refreshPillLabel} tone={refreshPillTone} /> : null}
        </>
      }
    >
      {loadError !== null && pageData !== null ? <div className="terminal-banner terminal-banner--error">{loadError}</div> : null}

      {pageData === null ? (
        <section className="terminal-grid terminal-grid--workspace terminal-grid--workspace-priority" data-testid="research-workspace">
          <TerminalPanel title="标的上下文" eyebrow="研究上下文">
            <div className="terminal-banner terminal-banner--info">
              {loadError ?? (hasActiveStockCode ? `${activeStockCode} 的身份、当前状态和事件摘要会在研究数据返回后填充。` : "输入股票代码并点击搜索后开始加载研究数据。")}
            </div>
          </TerminalPanel>

          <TerminalPanel title="图表工作台" eyebrow="核心工作区">
            <div className="terminal-banner terminal-banner--info">
              {loadError !== null ? `加载失败: ${loadError}` : hasActiveStockCode ? "正在加载真实行情数据..." : "等待输入股票代码后再启动搜索。"}
            </div>
          </TerminalPanel>

          <TerminalPanel title="智能侧栏" eyebrow="决策支持">
            <div className="terminal-banner terminal-banner--info">
              {loadError !== null ? "当前无法生成智能解释层。" : hasActiveStockCode ? "预测概率、风险提示与相似样本会在研究数据返回后显示。" : "输入股票代码后显示预测概率、风险提示与相似样本。"}
            </div>
          </TerminalPanel>
        </section>
      ) : (
        <>
          <section className="terminal-grid terminal-grid--workspace terminal-grid--workspace-priority" data-testid="research-workspace">
            <TerminalPanel title="标的上下文" eyebrow="研究上下文">
              <div className="terminal-button-row">
                <StatusPill label={pageData.current_state.label} tone={getStateTone(pageData.current_state.label)} />
                {pageData.stock.market ? <StatusPill label={pageData.stock.market} /> : null}
                {pageData.stock.industry ? <StatusPill label={pageData.stock.industry} /> : null}
              </div>

              <div className="terminal-stack">
                <div>
                  <p className="terminal-section-label">状态摘要</p>
                  <p className="terminal-copy">{pageData.current_state.summary}</p>
                </div>

                <div className="terminal-inline-metrics">
                  <div className="metric-card">
                    <p className="metric-card__eyebrow">交易日数</p>
                    <p className="metric-card__value">{pageData.prices.length}</p>
                  </div>
                  <div className="metric-card">
                    <p className="metric-card__eyebrow">新闻事件</p>
                    <p className="metric-card__value">{pageData.news_items.length}</p>
                  </div>
                  <div className="metric-card">
                    <p className="metric-card__eyebrow">交易标记</p>
                    <p className="metric-card__value">{pageData.trade_markers.length}</p>
                  </div>
                </div>

                {pageData.current_state.news_summary ? (
                  <div className="terminal-stack">
                    <p className="terminal-section-label">窗口新闻摘要</p>
                    <div className="terminal-chip-list">
                      <StatusPill label={`窗口新闻 ${formatMetricValue(pageData.current_state.news_summary.window_news_count)}`} />
                      <StatusPill label={`公告 ${formatMetricValue(pageData.current_state.news_summary.announcement_count)}`} tone="warning" />
                      <StatusPill
                        label={`修正情绪 ${formatMetricValue(pageData.current_state.news_summary.avg_adjusted_sentiment)}`}
                        tone={getSignedTone(pageData.current_state.news_summary.avg_adjusted_sentiment)}
                      />
                      <StatusPill
                        label={`正向事件 ${formatMetricValue(pageData.current_state.news_summary.positive_event_count)}`}
                        tone={resolveCountTone(pageData.current_state.news_summary.positive_event_count, "success")}
                      />
                      <StatusPill
                        label={`负向事件 ${formatMetricValue(pageData.current_state.news_summary.negative_event_count)}`}
                        tone={resolveCountTone(pageData.current_state.news_summary.negative_event_count, "danger")}
                      />
                      <StatusPill label={`治理事件 ${formatMetricValue(pageData.current_state.news_summary.governance_event_count)}`} />
                    </div>
                  </div>
                ) : null}
              </div>
            </TerminalPanel>

            <TerminalPanel title="图表工作台" eyebrow="核心工作区">
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
            </TerminalPanel>

            <PredictionPanel
              apiClient={client}
              stockCode={activeStockCode}
              prices={pageData.prices}
              autoPoints={pageData.auto_turning_points}
              provisionalPoints={pageData.provisional_turning_points ?? []}
              finalPoints={pageData.final_turning_points}
              currentState={pageData.current_state}
            />
          </section>

          <TerminalPanel title="事件流" eyebrow="催化因素">
            <ul className="terminal-list">
              {pageData.news_items.map((item) => {
                const tags = item.display_tags && item.display_tags.length > 0 ? item.display_tags : [resolveNewsBadge(item)];
                return (
                  <li key={item.news_id} className="terminal-panel">
                    <div className="terminal-panel__body">
                      <div className="terminal-chip-list">
                        {tags.map((tag) => {
                          const tagStyle = resolveNewsTagStyle(tag);
                          return (
                            <span
                              key={`${item.news_id}-${tag}`}
                              className="status-pill"
                              style={{
                                color: tagStyle.color,
                                background: tagStyle.background,
                                borderColor: "transparent",
                              }}
                            >
                              {tag}
                            </span>
                          );
                        })}
                        <span className="terminal-copy-muted">
                          {[item.source_name ?? "未知来源", item.news_date ?? "未知日期"].join(" · ")}
                        </span>
                      </div>

                      <strong>{item.title}</strong>

                      {item.event_types && item.event_types.length > 0 ? (
                        <div className="terminal-chip-list">
                          {item.event_types.map((eventType) => (
                            <StatusPill key={`${item.news_id}-${eventType}`} label={eventType} />
                          ))}
                          {typeof item.sentiment_score_adjusted === "number" ? (
                            <span className="terminal-copy-muted">修正后情绪 {item.sentiment_score_adjusted.toFixed(2)}</span>
                          ) : null}
                          {item.event_conflict_flag ? <StatusPill label="事件冲突" tone="danger" /> : null}
                        </div>
                      ) : typeof item.sentiment_score_adjusted === "number" ? (
                        <span className="terminal-copy-muted">修正后情绪 {item.sentiment_score_adjusted.toFixed(2)}</span>
                      ) : null}

                      {item.summary ? <p className="terminal-copy">{item.summary}</p> : null}
                    </div>
                  </li>
                );
              })}
            </ul>
          </TerminalPanel>
        </>
      )}
    </AppShell>
  );
}
