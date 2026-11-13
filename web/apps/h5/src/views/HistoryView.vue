<script setup lang="ts">
/** 牛市复盘：轮次列表与年度指数走势。 */
import { computed } from "vue";
import { pct, type CyclePayload } from "@brief/core";

const props = defineProps<{ payload: CyclePayload | null }>();

const chart = computed(() => {
  const series = props.payload?.year?.series?.[0]?.data ?? [];
  if (series.length < 2) return "";
  const low = Math.min(...series);
  const high = Math.max(...series);
  const span = high - low || 1;
  return series
    .map((value, index) => {
      const x = (index / (series.length - 1)) * 600;
      const y = 150 - ((value - low) / span) * 130;
      return `${index === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
});
</script>

<template>
  <view class="wrap">
    <view v-if="!payload" class="empty">复盘数据未导入</view>
    <template v-else>
      <view class="panel">
        <view class="head">
          <text class="title">2026 年指数走势</text>
          <text class="sub">{{ payload.year?.asOf }} · {{ payload.year?.dates?.length ?? 0 }} 个交易日 · {{ payload.year?.series?.[0]?.nm }}</text>
        </view>
        <svg viewBox="0 0 600 160" class="chart" preserveAspectRatio="none">
          <path :d="chart" fill="none" stroke="#0f172a" stroke-width="1.4" />
        </svg>
        <text class="basis">{{ payload.basis }}</text>
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
.basis { font-size: var(--fs-11); color: var(--faint); line-height: 1.6; }
.round { display: grid; grid-template-columns: 1fr auto auto; gap: 8rpx; align-items: baseline;
         padding: 10rpx 0; border-top: 1px solid var(--line); }
.rname { font-size: var(--fs-13); color: var(--ink); }
.rstatus { font-size: var(--fs-11); color: var(--faint); }
.rgain { font-size: var(--fs-13); font-variant-numeric: tabular-nums; }
.rperiod { grid-column: 1 / -1; font-size: var(--fs-11); color: var(--faint); }
.up { color: var(--up); }
.down { color: var(--down); }
</style>
