# APP 端

复用 `apps/miniapp` 的页面与 `packages/*`，差异只在打包配置：

- 使用 HBuilderX 导入 `apps/miniapp`，选择「App 打包」；
- `manifest.json` 的 `app-plus` 段控制启动图、权限与推送；
- 实时通道为 WebSocket，逻辑已由 `@brief/core` 的 `createRealtime` 统一。
