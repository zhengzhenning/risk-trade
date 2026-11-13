<script setup lang="ts">
/** 量价全景：指数收盘面积 + 成交量柱 + MA5/MA10。 */
import { computed } from "vue";
import { pct } from "@brief/core";

export interface PriceBar {
  day: string;
  close: number;
  high: number;
  low: number;
  volume: number;
  pct: number;
}

const props = defineProps<{ name: string; bars: PriceBar[] }>();

const W = 640;
const H = 220;
const PAD = 12;
const PRICE_H = 150;

const highs = computed(() => props.bars.map((bar) => bar.high));
const lows = computed(() => props.bars.map((bar) => bar.low));

const bounds = computed(() => {
  const low = Math.min(...lows.value);
  const high = Math.max(...highs.value);
  const pad = (high - low) * 0.08 || 1;
  return { low: low - pad, high: high + pad };
});

const step = computed(() => (W - PAD * 2) / Math.max(1, props.bars.length - 1));
const x = (index: number) => PAD + step.value * index;
const y = (price: number) => {
  const { low, high } = bounds.value;
  return PAD + (PRICE_H - PAD * 2) * (1 - (price - low) / (high - low));
};

const area = computed(() => {
  if (!props.bars.length) return "";
  const line = props.bars.map((bar, index) => `${index === 0 ? "M" : "L"}${x(index)},${y(bar.close)}`).join(" ");
  return `${line} L${x(props.bars.length - 1)},${PRICE_H} L${x(0)},${PRICE_H} Z`;
});
const line = computed(() =>
  props.bars.map((bar, index) => `${index === 0 ? "M" : "L"}${x(index)},${y(bar.close)}`).join(" "),
);

const maxVolume = computed(() => Math.max(...props.bars.map((bar) => bar.volume), 1));
const barWidth = computed(() => Math.max(2, step.value * 0.6));
const volY = (volume: number) => H - PAD - (H - PRICE_H - PAD * 2) * (volume / maxVolume.value);

const stats = computed(() => {
  const first = props.bars[0];
  const last = props.bars[props.bars.length - 1];
  if (!first || !last) return null;
  return {
    change: ((last.close / first.close) - 1) * 100,
    high: Math.max(...highs.value),
    low: Math.min(...lows.value),
    volume: props.bars.reduce((sum, bar) => sum + bar.volume, 0),
    last: last.close,
  };
});
</script>

<template>
  <view class="panel">
    <view class="head">
      <text class="title">量价全景 · {{ name }}</text>
      <text v-if="stats" class="sub">
        {{ stats.last.toFixed(2) }} · {{ pct(stats.change) }} · 高 {{ stats.high.toFixed(2) }} · 低 {{ stats.low.toFixed(2) }}
      </text>
    </view>
    <svg :viewBox="`0 0 ${W} ${H}`" class="chart" preserveAspectRatio="none">
      <path :d="area" fill="rgba(214,52,80,.10)" />
      <path :d="line" fill="none" stroke="#d63450" stroke-width="1.6" />
      <rect
        v-for="(bar, index) in bars"
        :key="bar.day"
        :x="x(index) - barWidth / 2"
        :y="volY(bar.volume)"
        :width="barWidth"
        :height="H - PAD - volY(bar.volume)"
        :fill="bar.pct >= 0 ? 'rgba(214,52,80,.45)' : 'rgba(11,122,85,.45)'"
      />
    </svg>
  </view>
</template>

<style scoped>
.panel { background: var(--bg); border-radius: var(--radius); padding: 16rpx 20rpx; }
.head { display: flex; align-items: baseline; gap: 12rpx; padding-bottom: 8rpx; }
.title { font-size: var(--fs-14); color: var(--ink); }
.sub { font-size: var(--fs-12); color: var(--sub); font-variant-numeric: tabular-nums; }
.chart { width: 100%; height: 300rpx; display: block; }
</style>
