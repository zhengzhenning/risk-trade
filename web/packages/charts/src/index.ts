/** 图表适配层：H5 用 ECharts 实例，小程序用 ec-canvas，APP 复用 Canvas。 */
export type ChartPlatform = "h5" | "miniapp" | "app";

export interface ChartSpec {
  type: "line" | "bar";
  categories: string[];
  series: { name: string; data: number[] }[];
  /** A 股配色：上涨红、下跌绿。 */
  tone?: "up" | "down" | "flat";
}

export function toEChartsOption(spec: ChartSpec) {
  const color = spec.tone === "down" ? "#0b7a55" : spec.tone === "flat" ? "#475569" : "#d63450";
  return {
    grid: { left: 8, right: 8, top: 16, bottom: 24, containLabel: true },
    xAxis: { type: "category", data: spec.categories, axisTick: { show: false } },
    yAxis: { type: "value", splitLine: { lineStyle: { color: "#EEF1F5" } } },
    series: spec.series.map((s) => ({
      name: s.name,
      type: spec.type,
      data: s.data,
      smooth: spec.type === "line",
      itemStyle: { color },
    })),
  };
}

/** 小程序需在 ec-canvas 上初始化；H5/APP 返回 null 由页面自行挂载。 */
export function initForPlatform(platform: ChartPlatform, canvasId: string) {
  if (platform !== "miniapp") return { canvasId, mode: "canvas" as const };
  return { canvasId, mode: "ec-canvas" as const, lazyLoad: true };
}
