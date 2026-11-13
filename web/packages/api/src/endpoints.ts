/** 与后端契约一致：路径与参数集中在此，页面不拼 URL。 */
import type { HttpTransport } from "./http";
import type { Briefing, PoolMatrix, PoolRanking, StockAlert } from "@brief/core";

export function createApi(transport: HttpTransport) {
  return {
    briefing: (day: string) => transport.get<Briefing>("/api/briefing", { date: day }),
    pool: (window: string, day: string) =>
      transport.get<PoolRanking>("/api/pool/" + window, { date: day }),
    alert: (codes: string[]) =>
      transport.get<Record<string, StockAlert>>("/api/alert", { codes: codes.join(",") }),
    poolHistory: (window: string, days = 6) =>
      transport.get<PoolMatrix>("/api/pool/history", { window, days: String(days) }),
  };
}
