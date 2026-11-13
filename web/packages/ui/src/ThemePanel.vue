<script setup lang="ts">
/** 题材面板：题材名、锚定龙头、成员与炒作逻辑。 */
import { pct, shortTheme, type ThemeView } from "@brief/core";

defineProps<{ themes: ThemeView[] }>();
</script>

<template>
  <view class="panel">
    <view class="head"><text class="title">题材</text><text class="sub">按锚点名次排序</text></view>
    <view v-if="!themes.length" class="empty">今日题材待接入（历史日期可查）</view>
    <view v-for="item in themes" :key="item.id" class="theme">
      <view class="line">
        <text class="name">{{ shortTheme(item.name, 6) }}</text>
        <text class="anchor">#{{ item.anchor.rank }} {{ item.anchor.name }}</text>
        <text class="count">{{ item.members.length }} 只</text>
      </view>
      <text class="narrative">{{ item.narrative || "—" }}</text>
      <view class="members">
        <text
          v-for="m in item.members.slice(0, 4)" :key="m.code" class="member"
          :class="{ anchor: m.is_anchor }"
        >
          {{ m.name }} {{ pct(m.range_pct) }}
        </text>
      </view>
    </view>
  </view>
</template>

<style scoped>
.panel { background: var(--bg); border-radius: var(--radius); padding: 16rpx 20rpx; }
.head { display: flex; align-items: baseline; gap: 12rpx; padding-bottom: 8rpx; }
.title { font-size: var(--fs-14); color: var(--ink); }
.sub { font-size: var(--fs-11); color: var(--faint); }
.empty { font-size: var(--fs-13); color: var(--faint); }
.theme { padding: 12rpx 0; border-top: 1px solid var(--line); display: flex; flex-direction: column; gap: 6rpx; }
.line { display: flex; align-items: baseline; gap: 10rpx; }
.name { font-size: var(--fs-13); color: var(--ink); }
.anchor { font-size: var(--fs-12); color: var(--accent, #8f6708); }
.count { margin-left: auto; font-size: var(--fs-11); color: var(--faint); }
.narrative { font-size: var(--fs-12); color: var(--sub); line-height: 1.6; }
.members { display: flex; flex-wrap: wrap; gap: 10rpx; }
.member { font-size: var(--fs-11); color: var(--sub); }
.member.anchor { color: var(--up); }
</style>
