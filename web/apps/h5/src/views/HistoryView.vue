<script setup lang="ts">
/** 牛市复盘：年度曲线（含关键打点）、节奏说明、事件时间线与历轮列表。 */
import { computed } from "vue";
import { pct, type CyclePayload } from "@brief/core";

const props = defineProps<{ payload: CyclePayload | null }>();

const series = computed(() => props.payload?.year?.series?.[0]?.data ?? []);
const dates = computed(() => props.payload?.year?.dates ?? []);

const bounds = computed(() => {
  const values = series.value;
  if (values.length < 2) return { low: 0, high: 1 };
  const low = Math.min(...values);
  const high = Math.max(...values);
  return { low, high: high === low ? low + 1 : high };
});

const point = (index: number, value: number) => {
  const x = (index / Math.max(1, series.value.length - 1)) * 600;
  const y = 150 - ((value - bounds.value.low) / (bounds.value.high - bounds.value.low)) * 130;
  return { x, y };
};

const path = computed(() =>
  series.value
    .map((value, index) => {
      const { x, y } = point(index, value);
      return `${index === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" "),
);

const marks = computed(() =>
  (props.payload?.year?.marks ?? [])
    .map((mark) => {
      const index = dates.value.indexOf(mark);
      if (index < 0) return null;
      const value = series.value[index];
      if (value === undefined) return null;
      const { x, y } = point(index, value);
      return { label: String(mark), x, y };
    })
    .filter((item): item is { label: string; x: number; y: number } => Boolean(item)),
);

const events = computed(() => (props.payload?.year?.events ?? []).slice(0, 8));
</script>

<template>
  <view class="wrap">
    <view v-if="!payload" class="empty">复盘数据未导入</view>
    <template v-else>
      <view class="panel">
        <view class="head">
          <text class="title">2026 年指数走势</text>
          <text class="sub">{{ payload.year?.asOf }} · {{ dates.length }} 个交易日 · {{ payload.year?.series?.[0]?.nm }}</text>
        </view>
        <svg viewBox="0 0 600 160" class="chart" preserveAspectRatio="none">
          <path :d="path" fill="none" stroke="#0f172a" stroke-width="1.4" />
          <g v-for="mark in marks" :key="mark.label">
            <circle :cx="mark.x" :cy="mark.y" r="3" fill="#d63450" />
            <text :x="mark.x + 4" :y="mark.y - 6" font-size="9" fill="#9f1239">{{ mark.label.slice(4) }}</text>
          </g>
        </svg>
        <text v-if="payload.year?.rhythm" class="rhythm">{{ payload.year.rhythm }}</text>
        <text class="basis">{{ payload.basis }}</text>
      </view>

      <view class="panel">
        <view class="head"><text class="title">关键事件</text><text class="sub">按日期</text></view>
        <view v-for="event in events" :key="event.d + event.t" class="event">
          <text class="edate">{{ event.d }}</text>
          <text class="etext">{{ event.t }}</text>
          <text class="esrc">{{ event.src }}</text>
        </view>
      </view>

      <view class="panel">
        <view class="head"><text class="title">历轮行情</text><text class="sub">{{ payload.rounds.length }} 轮</text></view>
        <view v-for="round in payload.rounds" :key="round.id" class="round">
          <text class="rname">{{ round.name }}</text>
          <text class="rstatus">{{ round.status }}</text>
          <text class="rgain" :class="round.gain >= 0 ? 'up' : 'down'">{{ pct(round.gain) }}</text>
          <text class="rperiod">{{ round.start.d }} → {{ round.peak.d }}</text>
        </view>
      </view>
    </template>
  </view>
</template>

<style scoped>
.wrap { display: flex; flex-direction: column; gap: 16rpx; }
.empty { background: var(--bg); border-radius: var(--radius); padding: 40rpx; color: var(--faint); }
.panel { background: var(--bg); border-radius: var(--radius); padding: 16rpx 20rpx; }
.head { display: flex; align-items: baseline; gap: 12rpx; padding-bottom: 8rpx; }
.title { font-size: var(--fs-14); color: var(--ink); }
.sub { font-size: var(--fs-11); color: var(--faint); }
.chart { width: 100%; height: 240rpx; }
.rhythm { display: block; font-size: var(--fs-12); color: var(--sub); line-height: 1.7; padding-top: 6rpx; }
.basis { display: block; font-size: var(--fs-11); color: var(--faint); line-height: 1.6; }
.event { display: flex; gap: 12rpx; align-items: baseline; padding: 8rpx 0; border-top: 1px solid var(--line); }
.edate { width: 130rpx; font-size: var(--fs-11); color: var(--faint); }
.etext { flex: 1; font-size: var(--fs-12); color: var(--ink); line-height: 1.6; }
.esrc { font-size: var(--fs-11); color: var(--faint); }
.round { display: grid; grid-template-columns: 1fr auto auto; gap: 8rpx; align-items: baseline;
         padding: 10rpx 0; border-top: 1px solid var(--line); }
.rname { font-size: var(--fs-13); color: var(--ink); }
.rstatus { font-size: var(--fs-11); color: var(--faint); }
.rgain { font-size: var(--fs-13); font-variant-numeric: tabular-nums; }
.rperiod { grid-column: 1 / -1; font-size: var(--fs-11); color: var(--faint); }
.up { color: var(--up); }
.down { color: var(--down); }
</style>
