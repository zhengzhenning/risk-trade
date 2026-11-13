<script setup lang="ts">
/** 股池矩阵：行=名次，列=交易日；名次七色，触控行高 44px。 */
import { computed } from "vue";
import { rankColor, pct, type MatrixCell } from "@brief/core";

const props = defineProps<{ dates: string[]; rows: (MatrixCell | null)[][] }>();
const colors = computed(() => props.rows.map((_, index) => rankColor(index + 1)));

function label(day: string): string {
  return day.slice(5).replace("-", "/");
}

function tone(value: number | undefined): string {
  if (value === undefined) return "var(--faint)";
  return value >= 0 ? "var(--up)" : "var(--down)";
}
</script>

<template>
  <scroll-view class="mx-scroll" scroll-x>
    <view class="mx">
      <view class="mx-head">
        <text class="mx-rank-head">#</text>
        <text v-for="day in dates" :key="day" class="mx-day">{{ label(day) }}</text>
      </view>
      <view v-for="(row, ri) in rows" :key="ri" class="mx-row">
        <text class="mx-rank" :style="{ color: colors[ri]?.ink }">#{{ ri + 1 }}</text>
        <view
          v-for="(cell, ci) in row"
          :key="ci"
          class="mx-cell"
          :class="{ today: ci === dates.length - 1 }"
        >
          <text v-if="cell" class="mx-name">{{ cell.name }}</text>
          <text v-if="cell" class="mx-pct" :style="{ color: tone(cell.range_pct) }">
            {{ pct(cell.range_pct) }}
          </text>
          <text v-else class="mx-empty">—</text>
        </view>
      </view>
    </view>
  </scroll-view>
</template>

<style scoped>
.mx-scroll { width: 100%; }
.mx { min-width: 100%; border-radius: var(--radius); }
.mx-head, .mx-row { display: flex; align-items: center; gap: 6px; }
.mx-head { min-height: 28px; color: var(--faint); font-size: var(--fs-11); }
.mx-row { min-height: 44px; border-top: 1px solid var(--line); }
.mx-rank-head, .mx-rank { width: 56rpx; flex: none; font-size: var(--fs-12); }
.mx-day { flex: 1 1 0; text-align: center; }
.mx-cell { flex: 1 1 0; min-width: 96rpx; display: flex; flex-direction: column; }
.mx-cell.today { background: var(--canvas); border-radius: var(--radius); }
.mx-name { font-size: var(--fs-13); color: var(--ink); }
.mx-pct { font-size: var(--fs-12); font-variant-numeric: tabular-nums; }
.mx-empty { font-size: var(--fs-12); color: var(--faint); }
</style>
