<script setup lang="ts">
/** 板块区间涨跌幅分布：按 5 档统计成员数量。 */
import { computed } from "vue";

const props = defineProps<{ items: { name: string; range_pct: number }[]; title?: string }>();

const BUCKETS = [
  { key: "ge60", label: "≥60%", test: (v: number) => v >= 60 },
  { key: "40", label: "40–60%", test: (v: number) => v >= 40 && v < 60 },
  { key: "20", label: "20–40%", test: (v: number) => v >= 20 && v < 40 },
  { key: "0", label: "0–20%", test: (v: number) => v >= 0 && v < 20 },
  { key: "down", label: "下跌", test: (v: number) => v < 0 },
] as const;

const buckets = computed(() =>
  BUCKETS.map((bucket) => {
    const rows = props.items.filter((item) => bucket.test(item.range_pct));
    return { ...bucket, count: rows.length, names: rows.map((item) => item.name) };
  }),
);
const total = computed(() => props.items.length || 1);
</script>

<template>
  <view class="panel">
    <view class="head"><text class="title">{{ title || "板块区间涨跌幅分布" }}</text><text class="sub">共 {{ items.length }} 只</text></view>
    <view v-if="!items.length" class="empty">暂无板块成员</view>
    <view v-for="bucket in buckets" :key="bucket.key" class="row">
      <text class="label">{{ bucket.label }}</text>
      <view class="bar"><view class="fill" :style="{ width: `${(bucket.count / total) * 100}%` }" /></view>
      <text class="count">{{ bucket.count }}</text>
    </view>
  </view>
</template>

<style scoped>
.panel { background: var(--bg); border-radius: var(--radius); padding: 16rpx 20rpx; }
.head { display: flex; align-items: baseline; gap: 12rpx; padding-bottom: 8rpx; }
.title { font-size: var(--fs-14); color: var(--ink); }
.sub { font-size: var(--fs-11); color: var(--faint); }
.empty { font-size: var(--fs-13); color: var(--faint); }
.row { display: flex; align-items: center; gap: 12rpx; padding: 6rpx 0; }
.label { width: 110rpx; font-size: var(--fs-11); color: var(--sub); }
.bar { flex: 1; height: 16rpx; background: var(--canvas); border-radius: 8rpx; overflow: hidden; }
.fill { height: 100%; background: var(--up); border-radius: 8rpx; }
.count { width: 40rpx; text-align: right; font-size: var(--fs-11); color: var(--faint); }
</style>
