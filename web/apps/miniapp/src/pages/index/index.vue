<script setup lang="ts">
/** 小程序首屏：复用 @brief/core 与 @brief/ui，实时走 WebSocket。 */
import { onMounted, ref } from "vue";
import { KpiCard } from "@brief/ui";
import { createRealtime, detectPlatform, toUnit } from "@brief/core";

const platform = detectPlatform();
const cards = ref([{ label: "上证指数", value: 0 }]);
const padding = toUnit(24, platform);

onMounted(() => {
  const client = createRealtime(platform, {
    url: "/api/live",
    onMessage: (payload) => {
      const data = payload as { indexes?: { name: string; change_pct: number }[] };
      cards.value = (data.indexes ?? []).map((i) => ({ label: i.name, value: i.change_pct }));
    },
  });
  client.start();
});
</script>

<template>
  <view class="page" :style="{ padding }">
    <KpiCard v-for="card in cards" :key="card.label" :label="card.label" :value="card.value" suffix="%" />
  </view>
</template>

<style scoped>
.page { background: var(--canvas); min-height: 100vh; display: flex; flex-direction: column; gap: 8px; }
</style>
