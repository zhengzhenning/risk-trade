<script setup lang="ts">
/** H5 看板首屏：指标卡 + 股池矩阵，数据来自 /api/briefing。 */
import { onMounted, ref } from "vue";
import { KpiCard, RankMatrix } from "@brief/ui";
import { createApi, createFetchTransport } from "@brief/api";
import type { Briefing, PoolEntry } from "@brief/core";

const api = createApi(createFetchTransport({ baseUrl: "/" }));
const briefing = ref<Briefing | null>(null);
const rows = ref<PoolEntry[][]>([]);
const dates = ref<string[]>([]);

onMounted(async () => {
  const day = new Date().toISOString().slice(0, 10);
  briefing.value = await api.briefing(day);
  const month = briefing.value.rankings.find((r) => r.window === "MONTH");
  if (month) {
    dates.value = [month.day];
    rows.value = [month.entries];
  }
});
</script>

<template>
  <view class="page">
    <view class="kpi-row">
      <KpiCard v-for="index in briefing?.indexes ?? []" :key="index.base.code"
               :label="index.base.name" :value="index.quote?.change_pct ?? 0" suffix="%" />
    </view>
    <RankMatrix :rows="rows" :dates="dates" />
  </view>
</template>

<style scoped>
.page { min-height: 100vh; padding: 12px; padding-bottom: calc(12px + var(--safe-bottom)); background: var(--canvas); }
.kpi-row { display: grid; gap: 8px; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); }
</style>
