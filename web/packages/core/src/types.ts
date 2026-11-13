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
