<script setup lang="ts">
/** 指数条：点位、涨跌、成交额，桌面横排、窄屏纵向。 */
import { pct, amount, pctTone, type IndexView } from "@brief/core";

defineProps<{ items: IndexView[] }>();
</script>

<template>
  <view class="strip">
    <view v-for="item in items" :key="item.code" class="cell" :data-tone="pctTone(item.change_pct)">
      <text class="name">{{ item.name }}</text>
      <text class="close">{{ item.close.toFixed(2) }}</text>
      <text class="chg">{{ pct(item.change_pct) }}</text>
      <text class="amt">{{ amount(item.amount) }}</text>
    </view>
  </view>
</template>

<style scoped>
.strip { display: grid; gap: 12rpx; grid-template-columns: repeat(auto-fit, minmax(220rpx, 1fr)); }
.cell { display: flex; flex-direction: column; gap: 2rpx; padding: 16rpx 20rpx;
        background: var(--bg); border-radius: var(--radius); }
.name { font-size: var(--fs-12); color: var(--sub); }
.close { font-size: var(--fs-22); color: var(--ink); font-variant-numeric: tabular-nums; }
.chg { font-size: var(--fs-13); font-variant-numeric: tabular-nums; }
.amt { font-size: var(--fs-11); color: var(--faint); }
.cell[data-tone="up"] .close, .cell[data-tone="up"] .chg { color: var(--up); }
.cell[data-tone="down"] .close, .cell[data-tone="down"] .chg { color: var(--down); }
</style>
