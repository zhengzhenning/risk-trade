/** 多端自适应：断点、rpx 换算与安全区。 */

export type Platform = "h5" | "miniapp" | "app";

export const BREAKPOINTS = { sm: 375, md: 768, lg: 1024, xl: 1440 } as const;

/** 设计稿宽度 750，uni-app 用 rpx，H5 用 px。 */
export function toUnit(px: number, platform: Platform): string {
  return platform === "h5" ? `${px / 2}px` : `${px}rpx`;
}

export function columnsOf(width: number): number {
  if (width >= BREAKPOINTS.xl) return 4;
  if (width >= BREAKPOINTS.md) return 2;
  return 1;
}

export function detectPlatform(): Platform {
  const uni = (globalThis as { uni?: { getSystemInfoSync?: () => { platform?: string } } }).uni;
  if (!uni) return "h5";
  const platform = uni.getSystemInfoSync?.().platform ?? "";
  return platform === "android" || platform === "ios" ? "app" : "miniapp";
}

/** 安全区内边距：H5 用 env()，小程序/APP 由系统注入。 */
export const SAFE_AREA = "env(safe-area-inset-bottom)";
