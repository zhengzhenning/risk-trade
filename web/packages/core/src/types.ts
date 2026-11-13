/** 与后端领域聚合一一对应的传输类型（snake_case 对齐 Python 序列化）。 */
export type PoolWindow = "MONTH" | "D60";
export type AlertLevel = "TRIGGERED" | "NEAR" | "WATCH" | "FAR";
export type ThemeStatus = "BREWING" | "FERMENTING" | "DIVERGING" | "FADING";

export interface IndexQuote {
  code: string;
  day: string;
  ts: string;
  close: number;
  change_pct: number;
  amount: number;
}

export interface PoolEntry {
  code: string;
  name: string;
  rank: number;
  window: PoolWindow;
  range_pct: number;
  pct: number;
  turnover: number;
  auction_pct: number;
  theme: string;
  is_top: boolean;
}

export interface PoolRanking {
  day: string;
  window: PoolWindow;
  entries: PoolEntry[];
  captured_at: string;
  baseline: boolean;
}

export interface ThemeMember {
  code: string;
  name: string;
  is_anchor: boolean;
  rank_in_pool: number | null;
  range_pct: number;
  limit_up_days: number;
}

export interface Theme {
  id: string;
  name: string;
  anchor_code: string;
  anchor_name: string;
  window: PoolWindow;
  rank: number;
  sector: string;
  status: ThemeStatus;
  members: ThemeMember[];
}

export interface StockAlert {
  code: string;
  day: string;
  level: AlertLevel;
  dev_pct: number;
  need_pct: number;
  distance_pct: number;
  monitor_end: string | null;
}

export interface StockQuote {
  code: string;
  day: string;
  ts: string;
  close: number;
  pct: number;
  turnover: number;
  limit_state: "NONE" | "UP" | "DOWN" | "BROKEN";
  consecutive_limit_up: number;
}

export interface Briefing {
  day: string;
  revision: number;
  indexes: { base: { code: string; name: string }; quote: IndexQuote | null }[];
  rankings: PoolRanking[];
  themes: Theme[];
  stocks: { base: { code: string; name: string; board: string }; quote: StockQuote | null; alert: StockAlert | null }[];
}

export interface MatrixCell {
  day: string;
  rank: number;
  code: string;
  name: string;
  range_pct: number;
  is_new: boolean;
}

export interface MatrixRow {
  rank: number;
  cells: (MatrixCell | null)[];
}

export interface PoolMatrix {
  window: PoolWindow;
  dates: string[];
  today: string | null;
  rows: MatrixRow[];
  tail: MatrixRow[];
}

export interface LiveDigest {
  day: string;
  indexes: { code: string; name: string; close: number | null; change_pct: number | null }[];
}

export interface IndexView {
  code: string;
  name: string;
  close: number;
  change_pct: number;
  amount: number;
}

export interface StockView {
  code: string;
  name: string;
  quote: StockQuote | null;
  alert: StockAlert | null;
  /** 点击矩阵单元格时的历史上下文（日期与窗口涨幅）。 */
  context?: { day: string; range_pct: number } | null;
}

export interface ThemeMemberView {
  code: string;
  name: string;
  is_anchor: boolean;
  rank_in_pool: number | null;
  range_pct: number;
}

export interface ThemeView {
  id: string;
  name: string;
  anchor: { code: string; name: string; rank: number };
  window: PoolWindow;
  status: ThemeStatus;
  narrative: string;
  logic: { trigger: string; diffusion: string; positioning: string; evidence: string[] } | null;
  members: ThemeMemberView[];
}

export interface PhaseView {
  start: string;
  end: string;
  kind: "acc" | "wash" | "start" | "dist";
  note: string;
}

export interface PriceBar {
  day: string;
  open: number;
  close: number;
  high: number;
  low: number;
  volume: number;
  pct: number;
}

export interface IndexHistory {
  code: string;
  name: string;
  bars: PriceBar[];
}

export interface EtfSeriesPoint {
  0: string;
  1: number;
  2: number;
  3: number;
}

export interface EtfFund {
  code: string;
  name: string;
  netIn1: number;
  netIn5: number;
  netIn20?: number;
}

export interface EtfIndustry {
  cat: string;
  idx: string;
  fund: { code: string; name: string; netIn1: number; netIn5: number; netIn20: number; pct5: number };
}

export interface EtfPayload {
  asOf: string;
  types: Record<string, string>;
  series: Record<string, [string, number, number, number][]>;
  funds: EtfFund[];
  industries?: EtfIndustry[];
}

export interface CycleRound {
  id: number;
  name: string;
  status: string;
  ongoing: boolean;
  lead: string;
  start: { d: string; p: number };
  peak: { d: string; p: number };
  gain: number;
  drawdown?: number;
}

export interface CycleSeries {
  nm: string;
  color: string;
  data: number[];
}

export interface CycleEvent {
  d: string;
  t: string;
  src?: string;
  url?: string;
}

export interface CyclePayload {
  basis: string;
  rounds: CycleRound[];
  year: {
    asOf: string;
    dates: number[];
    series: CycleSeries[];
    marks?: number[];
    events?: CycleEvent[];
    rhythm?: string;
  };
}
