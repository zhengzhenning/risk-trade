<script setup lang="ts">
/** H5 首屏：复用 core/api/ui，与小程序同一套页面逻辑。 */
import { onMounted, ref } from "vue";
import { KpiCard, RankMatrix } from "@brief/ui";
import { createApi, createFetchTransport } from "@brief/api";
import type { Briefing, MatrixCell } from "@brief/core";

const api = createApi(createFetchTransport({ baseUrl: "/" }));
const indexes = ref<{ name: string; pct: number }[]>([]);
const rows = ref<(MatrixCell | null)[][]>([]);
const dates = ref<string[]>([]);

onMounted(async () => {
  const day = new Date().toISOString().slice(0, 10);
  const briefing: Briefing = await api.briefing(day);
  indexes.value = briefing.indexes.map((item) => ({
    name: item.base.name,
    pct: item.quote?.change_pct ?? 0,
  }));
  const month = briefing.rankings.find((item) => item.window === "MONTH");
  dates.value = month ? [month.day] : [];

  const matrix = await api.poolHistory("MONTH", 6);
  dates.value = matrix.dates;
  rows.value = matrix.rows.map((row) => row.cells);
});
</script>

<template>
  <view class="page">
    <view class="kpi-row">
      <KpiCard v-for="item in indexes" :key="item.name" :label="item.name" :value="item.pct" suffix="%" />
    </view>
    <RankMatrix :rows="rows" :dates="dates" />
  </view>
</template>

<style scoped>
.page { min-height: 100vh; padding: 24rpx; background: var(--canvas); }
.kpi-row { display: grid; gap: 16rpx; grid-template-columns: repeat(auto-fit, minmax(200rpx, 1fr)); }
</style>
