"use client";

import { useMemo, useState } from "react";

import { KlineChart } from "./kline-chart";
import { TradeMarkerLayer } from "./trade-marker-layer";
import type { ApiClient, PriceRow, StockPoint, StockResearchData, TurningPointCommitResponse } from "../lib/api";

type PendingAction = "peak" | "trough" | null;

type TurningPointEditorProps = {
  stockCode: string;
  initialData: StockResearchData;
  apiClient: ApiClient;
  onCommitSuccess?: (response: TurningPointCommitResponse) => void;
};

function clonePoint(point: StockPoint): StockPoint {
  return {
    id: point.id,
    point_date: point.point_date,
    point_type: point.point_type,
    point_price: point.point_price,
    source_type: point.source_type,
  };
}

function getPointKey(point: StockPoint, index: number): string {
  return `${point.point_date}|${point.point_type}|${index}`;
}

function getSelectedPointPrice(row: PriceRow, pointType: "peak" | "trough"): number {
  return pointType === "peak" ? row.high_price : row.low_price;
}

export function TurningPointEditor({ stockCode, initialData, apiClient, onCommitSuccess }: TurningPointEditorProps) {
  const [pendingAction, setPendingAction] = useState<PendingAction>(null);
  const [draftFinalPoints, setDraftFinalPoints] = useState<StockPoint[]>(() => initialData.final_turning_points.map(clonePoint));
  const [operations, setOperations] = useState<
    Array<{ operation_type: string; old_value: Record<string, unknown> | null; new_value: Record<string, unknown> | null }>
  >([]);
  const [selectedPointKey, setSelectedPointKey] = useState<string | null>(null);
  const [saveStatus, setSaveStatus] = useState<"idle" | "saving" | "success" | "error">("idle");
  const [rebuildMessage, setRebuildMessage] = useState<string | null>(null);

  const sortedDraftPoints = useMemo(
    () =>
      [...draftFinalPoints].sort((left, right) => {
        if (left.point_date === right.point_date) {
          return left.point_type.localeCompare(right.point_type);
        }
        return left.point_date.localeCompare(right.point_date);
      }),
    [draftFinalPoints]
  );

  function handleSelectPrice(row: PriceRow) {
    if (pendingAction === null) {
      return;
    }
    if (selectedPointKey !== null) {
      setDraftFinalPoints((current) =>
        current.map((point, index) => {
          const pointKey = getPointKey(point, index);
          if (pointKey !== selectedPointKey) {
            return point;
          }
          const pointPrice = getSelectedPointPrice(row, pendingAction);
          return {
            ...point,
            point_date: row.trade_date,
            point_type: pendingAction,
            point_price: pointPrice,
            source_type: "manual",
          };
        })
      );
      const [pointDate, pointType] = selectedPointKey.split("|");
      const pointPrice = getSelectedPointPrice(row, pendingAction);
      setOperations((current) => [
        ...current,
        {
          operation_type: "move",
          old_value: { point_date: pointDate, point_type: pointType },
          new_value: { point_date: row.trade_date, point_type: pendingAction, point_price: pointPrice },
        },
      ]);
      setSelectedPointKey(null);
      setPendingAction(null);
      setRebuildMessage(null);
      setSaveStatus("idle");
      return;
    }
    const pointPrice = getSelectedPointPrice(row, pendingAction);
    const newPoint: StockPoint = {
      point_date: row.trade_date,
      point_type: pendingAction,
      point_price: pointPrice,
      source_type: "manual",
    };
    setDraftFinalPoints((current) => [...current, newPoint]);
    setOperations((current) => [...current, { operation_type: "add", old_value: null, new_value: newPoint }]);
    setPendingAction(null);
    setRebuildMessage(null);
    setSaveStatus("idle");
  }

  async function handleSave() {
    setSaveStatus("saving");
    try {
      const response = await apiClient.commitTurningPoints(stockCode, {
        operations,
        final_points: sortedDraftPoints.map((point) => ({
          point_date: point.point_date,
          point_type: point.point_type,
          point_price: point.point_price,
        })),
      });
      setDraftFinalPoints(response.final_turning_points.map(clonePoint));
      setOperations([]);
      setRebuildMessage(
        `重算完成: ${response.rebuild_summary.segments} 个波段 / ${response.rebuild_summary.features} 个特征 / ${response.rebuild_summary.predictions} 条预测`
      );
      onCommitSuccess?.(response);
      setSaveStatus("success");
    } catch {
      setSaveStatus("error");
    }
  }

  function handleReset() {
    setDraftFinalPoints(initialData.final_turning_points.map(clonePoint));
    setOperations([]);
    setPendingAction(null);
    setSelectedPointKey(null);
    setRebuildMessage(null);
    setSaveStatus("idle");
  }

  function handleDeleteSelected() {
    if (selectedPointKey === null) {
      return;
    }
    const pointToDelete = sortedDraftPoints.find((point, index) => getPointKey(point, index) === selectedPointKey);
    if (!pointToDelete) {
      return;
    }
    setDraftFinalPoints((current) =>
      current.filter((point, index) => getPointKey(point, index) !== selectedPointKey)
    );
    setOperations((current) => [
      ...current,
      {
        operation_type: "delete",
        old_value: pointToDelete,
        new_value: null,
      },
    ]);
    setSelectedPointKey(null);
    setRebuildMessage(null);
    setSaveStatus("idle");
  }

  return (
    <div className="terminal-stack">
      <div className="turning-point-toolbar terminal-button-row">
        <button className={pendingAction === "peak" ? "terminal-button terminal-button--primary" : "terminal-button"} type="button" onClick={() => setPendingAction("peak")}>
          标记波峰
        </button>
        <button
          className={pendingAction === "trough" ? "terminal-button terminal-button--primary" : "terminal-button"}
          type="button"
          onClick={() => setPendingAction("trough")}
        >
          标记波谷
        </button>
        <button className="terminal-button" type="button" onClick={handleReset}>
          撤销本次编辑
        </button>
        <button className="terminal-button" type="button" onClick={handleDeleteSelected} disabled={selectedPointKey === null}>
          删除选中点
        </button>
        <button className="terminal-button terminal-button--primary" type="button" onClick={handleSave} disabled={saveStatus === "saving"}>
          保存修正
        </button>
      </div>

      <div className="terminal-chart-frame terminal-chart-frame--workspace turning-point-editor__chart">
        <KlineChart
          prices={initialData.prices}
          autoPoints={initialData.auto_turning_points}
          finalPoints={sortedDraftPoints}
          onSelectPrice={handleSelectPrice}
          height={760}
        />
      </div>

      <section className="terminal-stack">
        <h2>最终拐点</h2>
        <ul className="terminal-list">
          {sortedDraftPoints.map((point, index) => (
            <li key={getPointKey(point, index)}>
              <button
                className="terminal-button"
                type="button"
                onClick={() => setSelectedPointKey(getPointKey(point, index))}
              >
                选择 {point.point_date} {point.point_type}
              </button>{" "}
              {point.point_date} {point.point_type} {point.point_price}
            </li>
          ))}
        </ul>
      </section>

      <TradeMarkerLayer count={initialData.trade_markers.length} />

      {rebuildMessage === null ? null : <div className="terminal-banner terminal-banner--info">{rebuildMessage}</div>}
      {saveStatus === "success" ? <div className="terminal-banner terminal-banner--info">保存成功</div> : null}
      {saveStatus === "error" ? <div className="terminal-banner terminal-banner--error">保存失败</div> : null}
    </div>
  );
}
