<script setup lang="ts">
/** 看盘主屏：三个页签对齐静态看板（情绪周期 / ETF申赎 / 牛市复盘）。 */
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { IndexStrip, RankMatrix, StockPanel, ThemePanel } from "@brief/ui";
import { createApi, createFetchTransport } from "@brief/api";
import type { Briefing, IndexView, MatrixCell, PhaseView, StockView, ThemeView } from "@brief/core";

const TABS = [
  { key: "cycle", label: "情绪周期" },
  { key: "etf", label: "ETF 申赎" },
  { key: "history", label: "牛市复盘" },
] as const;

const api = createApi(createFetchTransport({ baseUrl: "/" }));
const tab = ref<(typeof TABS)[number]["key"]>("cycle");
const indexes = ref<IndexView[]>([]);
const month = ref<{ dates: string[]; rows: (MatrixCell | null)[][] }>({ dates: [], rows: [] });
const d60 = ref<{ dates: string[]; rows: (MatrixCell | null)[][] }>({ dates: [], rows: [] });
const stocks = ref<Record<string, StockView>>({});
const themes = ref<ThemeView[]>([]);
const phases = ref<PhaseView[]>([]);
const alertCodes = ref<string[]>([]);
const selected = ref<StockView | null>(null);
const status = ref("加载中…");
const updatedAt = ref("");
let timer: ReturnType<typeof setInterval> | null = null;

const totalAmount = computed(() =>
  indexes.value
    .filter((item) => item.code === "000001" || item.code === "399001")
    .reduce((sum, item) => sum + (item.amount || 0), 0),
);
const latest = computed(() => month.value.dates[month.value.dates.length - 1] ?? "");
const alerts = computed(() =>
  alertCodes.value
    .map((code) => stocks.value[code])
    .filter((item): item is StockView => Boolean(item)),
);

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
    alertCodes.value = briefing.stocks
      .filter((item) => item.alert && ["TRIGGERED", "NEAR"].includes(item.alert.level))
      .map((item) => item.base.code);

    const [m, d, t] = await Promise.all([
      api.poolHistory("MONTH", 6),
      api.poolHistory("D60", 6),
      api.themes(day),
    ]);
    themes.value = t.themes;
    month.value = { dates: m.dates, rows: m.rows.map((row) => row.cells) };
    d60.value = { dates: d.dates, rows: d.rows.map((row) => row.cells) };
    if (!selected.value) await select(month.value.rows[0]?.[month.value.dates.length - 1] ?? null);
    status.value = `${latest.value} · rev ${briefing.revision}`;
    updatedAt.value = new Date().toLocaleTimeString("zh-CN", { hour12: false });
  } catch (error) {
    status.value = `加载失败：${String(error)}`;
  }
}

async function select(cell: MatrixCell | null): Promise<void> {
  if (!cell) return;
  const base = stocks.value[cell.code] ?? { code: cell.code, name: cell.name, quote: null, alert: null };
  selected.value = { ...base, name: cell.name, context: { day: cell.day, range_pct: cell.range_pct } };
  try {
    const detail = await api.stock(cell.code);
    phases.value = detail.phases;
  } catch {
    phases.value = [];
  }
}

onMounted(async () => {
  await load();
  timer = setInterval(load, 60_000);
});
onBeforeUnmount(() => {
  if (timer) clearInterval(timer);
});
</script>

<template>
  <view class="page">
    <view class="topbar">
      <text class="title">A 股每日看板</text>
      <text class="status">{{ status }}</text>
      <text class="amount">两市 {{ (totalAmount / 1e8).toFixed(0) }} 亿 · 预警 {{ alertCodes.length }}</text>
      <text class="updated">更新于 {{ updatedAt }}</text>
    </view>

    <view class="tabs">
      <text
        v-for="item in TABS"
        :key="item.key"
        class="tab"
        :class="{ active: tab === item.key }"
        @tap="tab = item.key"
      >
        {{ item.label }}
      </text>
    </view>

    <template v-if="tab === 'cycle'">
      <IndexStrip :items="indexes" />
      <view class="grid">
        <view class="col">
          <view class="card">
            <view class="card-head"><text class="card-title">月度前七</text><text class="card-sub">列=交易日</text></view>
            <RankMatrix :dates="month.dates" :rows="month.rows" :alert-codes="alertCodes" @tap-cell="select" />
          </view>
          <view class="card">
            <view class="card-head"><text class="card-title">近 60 日前七</text><text class="card-sub">窗口涨幅</text></view>
            <RankMatrix :dates="d60.dates" :rows="d60.rows" :alert-codes="alertCodes" @tap-cell="select" />
          </view>
        </view>
        <view class="side">
          <StockPanel :stock="selected" :phases="phases" />
          <view class="card">
            <view class="card-head"><text class="card-title">异动预警</text><text class="card-sub">已触发 / 临近</text></view>
            <view v-if="!alerts.length" class="empty">今日无预警</view>
            <view v-for="item in alerts" :key="item.code" class="alert-row">
              <text class="alert-name">{{ item.name }}</text>
              <text class="alert-level">{{ item.alert?.level }}</text>
              <text class="alert-dist">距触发 {{ item.alert?.distance_pct.toFixed(2) }}%</text>
            </view>
          </view>
          <ThemePanel :themes="themes" />
        </view>
      </view>
    </template>

    <view v-else class="placeholder">
      <text class="ph-title">{{ tab === "etf" ? "ETF 申赎" : "牛市复盘" }}</text>
      <text class="ph-desc">
        静态看板已有此模块；网页端尚未接入（数据侧需补 ETF 名称映射与历史轮次接口）。
      </text>
    </view>
  </view>
</template>

<style scoped>
.page { min-height: 100vh; padding: 24rpx; background: var(--canvas); display: flex; flex-direction: column; gap: 16rpx; }
.topbar { display: flex; align-items: baseline; gap: 16rpx; }
.title { font-size: var(--fs-16); color: var(--ink); }
.status { font-size: var(--fs-12); color: var(--faint); }
.amount { margin-left: auto; font-size: var(--fs-12); color: var(--sub); font-variant-numeric: tabular-nums; }
.updated { font-size: var(--fs-11); color: var(--faint); }
.tabs { display: flex; gap: 8rpx; border-bottom: 1px solid var(--line); }
.tab { padding: 12rpx 20rpx; font-size: var(--fs-13); color: var(--sub); border-bottom: 2px solid transparent; }
.tab.active { color: var(--ink); border-bottom-color: var(--ink); }
.grid { display: grid; gap: 16rpx; grid-template-columns: 1fr; }
.col, .side { display: flex; flex-direction: column; gap: 16rpx; }
.card { background: var(--bg); border-radius: var(--radius); padding: 16rpx 20rpx; }
.card-head { display: flex; align-items: baseline; gap: 12rpx; padding-bottom: 8rpx; }
.card-title { font-size: var(--fs-14); color: var(--ink); }
.card-sub { font-size: var(--fs-11); color: var(--faint); }
.empty { font-size: var(--fs-13); color: var(--faint); }
.alert-row { display: flex; gap: 12rpx; align-items: baseline; padding: 8rpx 0; border-top: 1px solid var(--line); }
.alert-name { font-size: var(--fs-13); color: var(--ink); }
.alert-level { font-size: var(--fs-11); color: var(--risk, #9f1239); }
.alert-dist { margin-left: auto; font-size: var(--fs-11); color: var(--faint); }
.placeholder { background: var(--bg); border-radius: var(--radius); padding: 40rpx; display: flex; flex-direction: column; gap: 12rpx; }
.ph-title { font-size: var(--fs-16); color: var(--ink); }
.ph-desc { font-size: var(--fs-13); color: var(--sub); line-height: 1.7; }
@media (min-width: 900px) {
  .grid { grid-template-columns: minmax(0, 1fr) 340px; align-items: start; }
}
</style>
