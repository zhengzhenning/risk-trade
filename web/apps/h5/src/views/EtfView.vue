<script setup lang="ts">
/** ETF 申赎：六类累计净流入、宽基曲线与重点基金。 */
import { computed } from "vue";
import { amount, type EtfPayload } from "@brief/core";

const props = defineProps<{ payload: EtfPayload | null }>();

const cards = computed(() => {
  if (!props.payload) return [];
  return Object.entries(props.payload.types).map(([key, name]) => {
    const series = props.payload?.series[key] ?? [];
    const last = series[series.length - 1];
    return { key, name, net: last?.[1] ?? 0, cum: last?.[2] ?? 0 };
  });
});

const curve = computed(() => {
  const series = props.payload?.series["1"] ?? [];
  return series.slice(-60);
});

const chart = computed(() => {
  const points = curve.value;
  if (points.length < 2) return "";
  const values = points.map((point) => point[2]);
  const low = Math.min(...values);
  const high = Math.max(...values);
  const span = high - low || 1;
  return points
    .map((point, index) => {
      const x = (index / (points.length - 1)) * 600;
      const y = 140 - ((point[2] - low) / span) * 120;
      return `${index === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
});

const funds = computed(() => (props.payload?.funds ?? []).slice(0, 6));
const industries = computed(() => (props.payload?.industries ?? []).slice(0, 12));
</script>

<template>
  <view class="wrap">
    <view v-if="!payload" class="empty">ETF 数据未导入</view>
    <template v-else>
      <view class="cards">
        <view v-for="item in cards" :key="item.key" class="card">
          <text class="name">{{ item.name }}</text>
          <text class="net" :class="item.net >= 0 ? 'up' : 'down'">{{ amount(item.net * 1e8) }}</text>
          <text class="cum">累计 {{ amount(item.cum * 1e8) }}</text>
        </view>
      </view>

      <view class="panel">
        <view class="head">
          <text class="title">宽基累计净流入（近 60 日）</text>
          <text class="sub">截至 {{ payload.asOf }}</text>
        </view>
        <svg viewBox="0 0 600 160" class="chart" preserveAspectRatio="none">
          <path :d="chart" fill="none" stroke="#3b66d4" stroke-width="1.6" />
        </svg>
      </view>

      <view v-if="industries.length" class="panel">
        <view class="head"><text class="title">行业专区</text><text class="sub">行业 → 代表基金</text></view>
        <view v-for="item in industries" :key="item.fund.code" class="row">
          <text class="icat">{{ item.cat }}</text>
          <text class="iname">{{ item.idx }}</text>
          <text class="ifund">{{ item.fund.name }}</text>
          <text class="fnet" :class="item.fund.netIn5 >= 0 ? 'up' : 'down'">{{ item.fund.netIn5.toFixed(1) }} 亿</text>
        </view>
      </view>

      <view class="panel">
        <view class="head"><text class="title">重点 ETF</text><text class="sub">按 5 日净流入</text></view>
        <view v-for="fund in funds" :key="fund.code" class="row">
          <text class="fname">{{ fund.name }}</text>
          <text class="fcode">{{ fund.code }}</text>
          <text class="fnet" :class="fund.netIn5 >= 0 ? 'up' : 'down'">{{ fund.netIn5.toFixed(1) }} 亿</text>
        </view>
      </view>
    </template>
  </view>
</template>

<style scoped>
.wrap { display: flex; flex-direction: column; gap: 16rpx; }
.empty { background: var(--bg); border-radius: var(--radius); padding: 40rpx; color: var(--faint); }
.cards { display: grid; gap: 12rpx; grid-template-columns: repeat(auto-fit, minmax(200rpx, 1fr)); }
.card { background: var(--bg); border-radius: var(--radius); padding: 16rpx 20rpx; display: flex; flex-direction: column; gap: 4rpx; }
.name { font-size: var(--fs-12); color: var(--sub); }
.net { font-size: var(--fs-16); font-variant-numeric: tabular-nums; }
.cum { font-size: var(--fs-11); color: var(--faint); }
.up { color: var(--up); }
.down { color: var(--down); }
.panel { background: var(--bg); border-radius: var(--radius); padding: 16rpx 20rpx; }
.head { display: flex; align-items: baseline; gap: 12rpx; padding-bottom: 8rpx; }
.title { font-size: var(--fs-14); color: var(--ink); }
.sub { font-size: var(--fs-11); color: var(--faint); }
.chart { width: 100%; height: 240rpx; }
.row { display: flex; gap: 12rpx; align-items: baseline; padding: 8rpx 0; border-top: 1px solid var(--line); }
.fname { font-size: var(--fs-13); color: var(--ink); }
.icat { width: 80rpx; font-size: var(--fs-11); color: var(--faint); }
.iname { width: 160rpx; font-size: var(--fs-12); color: var(--ink); }
.ifund { flex: 1; font-size: var(--fs-12); color: var(--sub); }
.fcode { font-size: var(--fs-11); color: var(--faint); }
.fnet { margin-left: auto; font-size: var(--fs-13); font-variant-numeric: tabular-nums; }
</style>
