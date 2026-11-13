<script setup lang="ts">
/** 指标卡：三端通用，字号与间距走设计令牌。 */
import { computed } from "vue";
import { pct, pctTone } from "@brief/core";

const props = defineProps<{ label: string; value: number; suffix?: string }>();
const tone = computed(() => pctTone(props.value));
</script>

<template>
  <view class="kpi" :data-tone="tone">
    <text class="kpi-label">{{ label }}</text>
    <text class="kpi-value">{{ suffix === "%" ? pct(value) : value.toFixed(2) }}</text>
  </view>
</template>

<style scoped>
.kpi { display: flex; flex-direction: column; gap: 4px; padding: 12px; border-radius: var(--radius); background: var(--bg); }
.kpi-label { font-size: var(--fs-12); color: var(--sub); }
.kpi-value { font-size: var(--fs-22); color: var(--ink); font-variant-numeric: tabular-nums; }
.kpi[data-tone="up"] .kpi-value { color: var(--up); }
.kpi[data-tone="down"] .kpi-value { color: var(--down); }
</style>
