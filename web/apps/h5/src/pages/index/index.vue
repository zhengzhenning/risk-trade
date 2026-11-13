<script setup lang="ts">
/** 浏览器看盘主屏：指数条 + 双窗口矩阵 + 个股面板。 */
import { computed, onMounted, ref } from "vue";
import { IndexStrip, RankMatrix, StockPanel, ThemePanel } from "@brief/ui";
import { createApi, createFetchTransport } from "@brief/api";
import type { Briefing, IndexView, MatrixCell, StockView, ThemeView } from "@brief/core";

const api = createApi(createFetchTransport({ baseUrl: "/" }));
const indexes = ref<IndexView[]>([]);
const month = ref<{ dates: string[]; rows: (MatrixCell | null)[][] }>({ dates: [], rows: [] });
const d60 = ref<{ dates: string[]; rows: (MatrixCell | null)[][] }>({ dates: [], rows: [] });
const stocks = ref<Record<string, StockView>>({});
const themes = ref<ThemeView[]>([]);
const selected = ref<StockView | null>(null);
const status = ref("加载中…");

const MARKET_CODES = new Set(["000001", "399001"]);
const totalAmount = computed(() =>
  indexes.value
    .filter((item: IndexView) => MARKET_CODES.has(item.code))
    .reduce((sum: number, item: IndexView) => sum + (item.amount || 0), 0),
);
const latest = computed(() => month.value.dates[month.value.dates.length - 1] ?? "");

async function load(): Promise<void> {
  try {
    const day = new Date().toISOString().slice(0, 10);
    const briefing: Briefing = await api.briefing(day);
    indexes.value = briefing.indexes.map((item) => ({
      code: item.base.code,
      name: item.base.name,
      close: item.quote?.close ?? 0,
      change_pct: item.quote?.change_pct ?? 0,
      amount: item.quote?.amount ?? 0,
    }));
    stocks.value = Object.fromEntries(
      briefing.stocks.map((item) => [item.base.code, {
        code: item.base.code, name: item.base.name, quote: item.quote, alert: item.alert,
      }]),
    );
    const [m, d, t] = await Promise.all([
      api.poolHistory("MONTH", 6),
      api.poolHistory("D60", 6),
      api.themes(day),
    ]);
    themes.value = t.themes;
    month.value = { dates: m.dates, rows: m.rows.map((row) => row.cells) };
    select(month.value.rows[0]?.[month.value.dates.length - 1] ?? null);
    d60.value = { dates: d.dates, rows: d.rows.map((row) => row.cells) };
    status.value = `${latest.value} · rev ${briefing.revision}`;
  } catch (error) {
    status.value = `加载失败：${String(error)}`;
  }
}

function select(cell: MatrixCell | null): void {
  if (!cell) return;
  const base = stocks.value[cell.code] ?? { code: cell.code, name: cell.name, quote: null, alert: null };
  selected.value = { ...base, name: cell.name, context: { day: cell.day, range_pct: cell.range_pct } };
}

onMounted(load);
</script>

<template>
  <view class="page">
    <view class="topbar">
      <text class="title">A 股每日看板</text>
      <text class="status">{{ status }}</text>
      <text class="amount">两市 {{ (totalAmount / 1e8).toFixed(0) }} 亿</text>
    </view>

    <IndexStrip :items="indexes" />

    <view class="grid">
      <view class="col">
        <view class="card">
          <view class="card-head"><text class="card-title">月度前七</text><text class="card-sub">列=交易日</text></view>
          <RankMatrix :dates="month.dates" :rows="month.rows" @tap-cell="select" />
        </view>
        <view class="card">
          <view class="card-head"><text class="card-title">近 60 日前七</text><text class="card-sub">窗口涨幅</text></view>
          <RankMatrix :dates="d60.dates" :rows="d60.rows" @tap-cell="select" />
        </view>
      </view>
      <view class="side">
        <StockPanel :stock="selected" />
        <ThemePanel :themes="themes" />
      </view>
    </view>
  </view>
</template>

<style scoped>
.page { min-height: 100vh; padding: 24rpx; background: var(--canvas); display: flex; flex-direction: column; gap: 16rpx; }
.topbar { display: flex; align-items: baseline; gap: 16rpx; }
.title { font-size: var(--fs-16); color: var(--ink); }
.status { font-size: var(--fs-12); color: var(--faint); }
.amount { margin-left: auto; font-size: var(--fs-12); color: var(--sub); font-variant-numeric: tabular-nums; }
.grid { display: grid; gap: 16rpx; grid-template-columns: 1fr; }
.col { display: flex; flex-direction: column; gap: 16rpx; }
.card { background: var(--bg); border-radius: var(--radius); padding: 16rpx 20rpx; }
.card-head { display: flex; align-items: baseline; gap: 12rpx; padding-bottom: 8rpx; }
.card-title { font-size: var(--fs-14); color: var(--ink); }
.card-sub { font-size: var(--fs-11); color: var(--faint); }
.side { display: flex; flex-direction: column; gap: 16rpx; }
@media (min-width: 900px) {
  .grid { grid-template-columns: minmax(0, 1fr) 320px; align-items: start; }
}
</style>
