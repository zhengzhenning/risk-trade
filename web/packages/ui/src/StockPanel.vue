<script setup lang="ts">
/** 个股面板：行情、异动、题材位。数据为空时显示占位。 */
import { computed } from "vue";
import { pct, pctTone, type PhaseView, type StockView } from "@brief/core";

const props = defineProps<{ stock: StockView | null; phases?: PhaseView[] }>();
const phaseLabels: Record<string, string> = { acc: "吸筹", start: "启动", wash: "洗盘", dist: "派发" };
const phaseLabel = (kind: string) => phaseLabels[kind] ?? kind;
const tone = computed(() => pctTone(props.stock?.quote?.pct ?? 0));
const alertText = computed(() => {
  const alert = props.stock?.alert;
  if (!alert) return "无异动";
  const labels: Record<string, string> = {
    TRIGGERED: "已触发", NEAR: "临近", WATCH: "关注", FAR: "远",
  };
  return `${labels[alert.level] ?? alert.level} · 距触发 ${alert.distance_pct.toFixed(2)}%`;
});
</script>

<template>
  <view class="panel">
    <view v-if="!stock" class="empty">从左侧矩阵选择个股</view>
    <template v-else>
      <view class="head">
        <text class="name">{{ stock.name }}</text>
        <text class="code">{{ stock.code }}</text>
      </view>
      <view class="row">
        <text class="label">最新</text>
        <text class="value" :data-tone="tone">{{ stock.quote ? stock.quote.close.toFixed(2) : "—" }}</text>
        <text class="label">涨跌</text>
        <text class="value" :data-tone="tone">{{ pct(stock.quote?.pct ?? 0) }}</text>
      </view>
      <view class="row">
        <text class="label">换手</text>
        <text class="value">{{ (stock.quote?.turnover ?? 0).toFixed(2) }}%</text>
        <text class="label">连板</text>
        <text class="value">{{ stock.quote?.consecutive_limit_up ?? 0 }}</text>
      </view>
      <view v-if="phases?.length" class="phases">
        <text v-for="phase in phases ?? []" :key="phase.start" class="phase" :data-kind="phase.kind">
          {{ phaseLabel(phase.kind) }} {{ phase.start.slice(5) }}–{{ phase.end.slice(5) }}
        </text>
      </view>
      <view v-if="stock.context" class="context">
        {{ stock.context.day }} 窗口涨幅 {{ pct(stock.context.range_pct) }}
      </view>
      <view class="alert">{{ alertText }}</view>
    </template>
  </view>
</template>

<style scoped>
.panel { background: var(--bg); border-radius: var(--radius); padding: 20rpx; min-height: 200rpx; }
.empty { color: var(--faint); font-size: var(--fs-13); }
.head { display: flex; align-items: baseline; gap: 12rpx; margin-bottom: 12rpx; }
.name { font-size: var(--fs-16); color: var(--ink); }
.code { font-size: var(--fs-12); color: var(--faint); }
.row { display: flex; gap: 12rpx; align-items: baseline; margin-bottom: 8rpx; }
.label { font-size: var(--fs-12); color: var(--faint); width: 72rpx; }
.value { font-size: var(--fs-14); color: var(--ink); font-variant-numeric: tabular-nums; }
.value[data-tone="up"] { color: var(--up); }
.value[data-tone="down"] { color: var(--down); }
.phases { display: flex; flex-wrap: wrap; gap: 8rpx; margin-top: 8rpx; }
.phase { font-size: var(--fs-11); padding: 2rpx 8rpx; border-radius: 4rpx; background: var(--canvas);
         color: var(--sub); }
.phase[data-kind="start"] { color: var(--up); }
.phase[data-kind="dist"] { color: var(--risk, #9f1239); }
.context { margin-top: 8rpx; font-size: var(--fs-12); color: var(--sub); }
.alert { margin-top: 12rpx; font-size: var(--fs-12); color: var(--risk, #9f1239); }
</style>
