<script setup lang="ts">
/** K 线图：蜡烛 + 成交量，支持日/周切换由父级控制。 */
import { computed } from "vue";
import type { PriceBar } from "@brief/core";

const props = defineProps<{ bars: PriceBar[]; period: "day" | "week" }>();

const W = 640;
const H = 240;
const PRICE_H = 168;
const PAD = 10;

const high = computed(() => Math.max(...props.bars.map((bar) => bar.high)));
const low = computed(() => Math.min(...props.bars.map((bar) => bar.low)));
const span = computed(() => high.value - low.value || 1);
const maxVolume = computed(() => Math.max(...props.bars.map((bar) => bar.volume), 1));
const step = computed(() => (W - PAD * 2) / Math.max(1, props.bars.length));
const width = computed(() => Math.max(2, step.value * 0.6));

const y = (price: number) => PAD + (PRICE_H - PAD) * (1 - (price - low.value) / span.value);
const volTop = (volume: number) => H - PAD - (H - PRICE_H - PAD) * (volume / maxVolume.value);

const ma = (n: number) => {
  const out: (number | null)[] = [];
  props.bars.forEach((_, index) => {
    if (index < n - 1) return out.push(null);
    const slice = props.bars.slice(index - n + 1, index + 1);
    out.push(slice.reduce((sum, bar) => sum + bar.close, 0) / n);
  });
  return out;
};
const maLine = (n: number) =>
  ma(n)
    .map((value, index) =>
      value === null ? "" : `${index === 0 ? "M" : "L"}${(PAD + step.value * (index + 0.5)).toFixed(1)},${y(value).toFixed(1)}`,
    )
    .filter(Boolean)
    .join(" ");
</script>

<template>
  <view class="wrap">
    <svg :viewBox="`0 0 ${W} ${H}`" class="chart" preserveAspectRatio="none">
      <g v-for="(bar, index) in bars" :key="bar.day">
        <line
          :x1="PAD + step * (index + 0.5)"
          :x2="PAD + step * (index + 0.5)"
          :y1="y(bar.high)"
          :y2="y(bar.low)"
          :stroke="bar.close >= bar.open ? '#d63450' : '#0b7a55'"
          stroke-width="1"
        />
        <rect
          :x="PAD + step * (index + 0.5) - width / 2"
          :y="y(Math.max(bar.open, bar.close))"
          :width="width"
          :height="Math.max(1, Math.abs(y(bar.open) - y(bar.close)))"
          :fill="bar.close >= bar.open ? '#d63450' : '#0b7a55'"
        />
        <rect
          :x="PAD + step * (index + 0.5) - width / 2"
          :y="volTop(bar.volume)"
          :width="width"
          :height="H - PAD - volTop(bar.volume)"
          :fill="bar.pct >= 0 ? 'rgba(214,52,80,.35)' : 'rgba(11,122,85,.35)'"
        />
      </g>
      <path :d="maLine(5)" fill="none" stroke="#b45309" stroke-width="1" />
      <path :d="maLine(10)" fill="none" stroke="#3b66d4" stroke-width="1" />
    </svg>
    <view class="legend">
      <text class="tag">MA5</text><text class="tag">MA10</text>
      <text class="period">{{ period === "day" ? "日 K" : "周 K" }} · {{ bars.length }} 根</text>
    </view>
  </view>
</template>

<style scoped>
.wrap { width: 100%; }
.chart { width: 100%; height: 320rpx; display: block; }
.legend { display: flex; gap: 12rpx; align-items: baseline; padding-top: 6rpx; }
.tag { font-size: var(--fs-11); color: var(--faint); }
.period { margin-left: auto; font-size: var(--fs-11); color: var(--faint); }
</style>
