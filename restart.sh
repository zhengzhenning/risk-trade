#!/usr/bin/env bash
# 一键重启看板：停旧进程 → 起 API → 起快照循环 → 健康检查
# 用法：./restart.sh [stop|status]
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT" || exit 1

PORT="${PORT:-8000}"
PY="$ROOT/.venv/bin/python"
API_LOG="/tmp/brief_api.log"
LIVE_LOG="/tmp/brief_live.log"
URL="http://127.0.0.1:${PORT}/board"

stop_all() {
  pkill -f "uvicorn a_share_brief.interfaces.api" 2>/dev/null
  pkill -f "a_share_brief.interfaces.live_loop" 2>/dev/null
  sleep 1
}

status() {
  echo "--- 端口 ${PORT} ---"
  if lsof -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "API 监听中"
  else
    echo "API 未监听"
  fi
  if pgrep -f "a_share_brief.interfaces.live_loop" >/dev/null 2>&1; then
    echo "快照循环运行中"
  else
    echo "快照循环未运行"
  fi
  code=$(curl -s -m 5 -o /dev/null -w "%{http_code}" "$URL" 2>/dev/null || echo 000)
  echo "看板 HTTP $code → $URL"
}

case "${1:-restart}" in
  stop)
    stop_all
    echo "已停止 API 与快照循环"
    exit 0
    ;;
  status)
    status
    exit 0
    ;;
esac

if [ ! -x "$PY" ]; then
  echo "缺少虚拟环境：$PY"
  echo "先执行：python3 -m venv .venv && .venv/bin/pip install fastapi uvicorn httpx pytest"
  exit 1
fi

echo "1/3 停止旧进程"
stop_all

if [ -n "${QG_KEY:-}" ] && [ -n "${QG_PASSWORD:-}" ]; then
  echo "代理：已启用青果（东财走代理，腾讯直连兜底）"
else
  echo "代理：未配置 QG_KEY/QG_PASSWORD，直连抓取"
fi

echo "2/3 启动 API 与快照循环"
PYTHONPATH=src nohup "$PY" -m uvicorn a_share_brief.interfaces.api:create_app \
  --factory --port "$PORT" > "$API_LOG" 2>&1 &
disown
PYTHONPATH=src nohup "$PY" -m a_share_brief.interfaces.live_loop \
  --root work/store --interval 120 > "$LIVE_LOG" 2>&1 &
disown

echo "3/3 等待服务就绪"
for _ in $(seq 1 20); do
  code=$(curl -s -m 2 -o /dev/null -w "%{http_code}" "$URL" 2>/dev/null || echo 000)
  if [ "$code" = "200" ]; then
    echo "就绪：$URL"
    status
    exit 0
  fi
  sleep 1
done

echo "启动失败：看板未返回 200"
echo "--- $API_LOG ---"
tail -20 "$API_LOG" 2>/dev/null
echo "--- $LIVE_LOG ---"
tail -10 "$LIVE_LOG" 2>/dev/null
exit 1
