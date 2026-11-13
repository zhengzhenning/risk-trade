/** 数值与时间格式化：三端共用，不依赖框架。 */
export function pct(value: number, digits = 2): string {
  if (!Number.isFinite(value)) return "—";
  return `${value > 0 ? "+" : ""}${value.toFixed(digits)}%`;
}

export function amount(value: number): string {
  if (!Number.isFinite(value)) return "—";
  if (Math.abs(value) >= 1e8) return `${(value / 1e8).toFixed(2)} 亿`;
  if (Math.abs(value) >= 1e4) return `${(value / 1e4).toFixed(1)} 万`;
  return value.toFixed(0);
}

/** A 股习惯：涨红跌绿。 */
export function pctTone(value: number): "up" | "down" | "flat" {
  if (value > 0) return "up";
  if (value < 0) return "down";
  return "flat";
}

export function shortTheme(theme: string, max = 4): string {
  const base = theme.replace(/（.*?）|\(.*?\)/g, "");
  return base.length > max ? base.slice(0, max) : base;
}
