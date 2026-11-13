/** 名次七色：与看板一致的唯一色源。 */
export const RANK_COLORS = [
  { bg: "#7c2d12", ink: "#7c2d12", tint: "#fdf1e7" },
  { bg: "#b45309", ink: "#b45309", tint: "#fdf3e3" },
  { bg: "#f59e0b", ink: "#8a5a00", tint: "#fef7e6" },
  { bg: "#0f766e", ink: "#0f766e", tint: "#e9f7f4" },
  { bg: "#1d4ed8", ink: "#1d4ed8", tint: "#eaf0fe" },
  { bg: "#7c3aed", ink: "#7c3aed", tint: "#f2ecfe" },
  { bg: "#475569", ink: "#475569", tint: "#eef1f5" },
] as const;

export function rankColor(rank: number | null | undefined) {
  if (!rank || rank < 1 || rank > RANK_COLORS.length) return RANK_COLORS[6];
  return RANK_COLORS[rank - 1];
}
