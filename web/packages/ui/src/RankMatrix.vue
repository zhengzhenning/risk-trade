<script setup lang="ts">
/** 股池矩阵：名次七色，列随屏幕收缩，触控行高不低于 44px。 */
import { computed } from "vue";
import { rankColor, pct, type PoolEntry } from "@brief/core";

const props = defineProps<{ rows: PoolEntry[][]; dates: string[] }>();
const todayIndex = computed(() => Math.max(0, props.dates.length - 1));
const toneOf = (entry: PoolEntry | undefined) => rankColor(entry?.rank ?? 1).ink;
const colorOf = (value: number) => (value >= 0 ? "var(--up)" : "var(--down)");
</script>

<template>
  <scroll-view class="mx" scroll-x>
    <view class="mx-grid">
      <view v-for="(row, ri) in rows" :key="ri" class="mx-row">
        <text class="mx-rank" :style="{ color: toneOf(row[0]) }">#{{ ri + 1 }}</text>
        <view v-for="(cell, ci) in row" :key="ci" class="mx-cell" :class="{ today: ci === todayIndex }">
          <text class="mx-name">{{ cell.name }}</text>
          <text class="mx-pct" :style="{ color: colorOf(cell.range_pct) }">
            {{ pct(cell.range_pct) }}
          </text>
        </view>
      </view>
    </view>
  </scroll-view>
</template>

<style scoped>
.mx { width: 100%; }
.mx-grid { min-width: 100%; display: flex; flex-direction: column; }
.mx-row { display: flex; align-items: center; gap: 6px; min-height: 44px; }
.mx-rank { width: 32px; font-size: var(--fs-12); }
.mx-cell { flex: 1 1 0; min-width: 92px; display: flex; flex-direction: column; }
.mx-cell.today { background: var(--canvas); border-radius: var(--radius); }
.mx-name { font-size: var(--fs-13); color: var(--ink); }
.mx-pct { font-size: var(--fs-12); font-variant-numeric: tabular-nums; }
</style>
