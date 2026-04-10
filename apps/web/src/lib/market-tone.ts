export type StatusTone = "default" | "success" | "warning" | "danger";

const POSITIVE_STATE_PATTERNS = [/主升/, /上涨/, /走强/, /强势/, /突破/, /企稳/, /反弹/, /利多/, /底部/];
const NEGATIVE_STATE_PATTERNS = [/见顶/, /下跌/, /走弱/, /回撤/, /风险/, /利空/, /顶部/];

export function getSignedTone(value?: number | null): StatusTone {
  if (value === undefined || value === null || value === 0) {
    return "default";
  }
  return value > 0 ? "success" : "danger";
}

export function getTrendTone(trend?: string | null): StatusTone {
  if (trend === "up") {
    return "success";
  }
  if (trend === "down") {
    return "danger";
  }
  return "default";
}

export function getStateTone(label?: string | null): StatusTone {
  if (label === undefined || label === null || label.trim() === "") {
    return "default";
  }
  if (NEGATIVE_STATE_PATTERNS.some((pattern) => pattern.test(label))) {
    return "danger";
  }
  if (POSITIVE_STATE_PATTERNS.some((pattern) => pattern.test(label))) {
    return "success";
  }
  return "default";
}

export function getMarketValueClass(value?: number | null): string {
  if (value === undefined || value === null || value === 0) {
    return "market-value market-value--neutral";
  }
  return value > 0 ? "market-value market-value--positive" : "market-value market-value--negative";
}
