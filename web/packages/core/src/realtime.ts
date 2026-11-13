/** 实时通道：H5 用 SSE，小程序/APP 用 WebSocket。 */

export interface RealtimeOptions {
  url: string;
  onMessage: (payload: unknown) => void;
  onError?: (error: unknown) => void;
}

export interface RealtimeClient {
  start(): void;
  stop(): void;
}

export function createRealtime(platform: "h5" | "miniapp" | "app", options: RealtimeOptions): RealtimeClient {
  if (platform === "h5" && typeof EventSource !== "undefined") {
    let source: EventSource | null = null;
    return {
      start() {
        source = new EventSource(options.url);
        source.onmessage = (event) => options.onMessage(JSON.parse(event.data));
        source.onerror = (error) => options.onError?.(error);
      },
      stop() {
        source?.close();
        source = null;
      },
    };
  }

  let socket: WebSocket | null = null;
  let timer: ReturnType<typeof setInterval> | null = null;
  return {
    start() {
      socket = new WebSocket(options.url.replace(/^http/, "ws"));
      socket.onmessage = (event) => options.onMessage(JSON.parse(event.data));
      socket.onerror = (error) => options.onError?.(error);
      timer = setInterval(() => socket?.readyState === 1 && socket.send("ping"), 25_000);
    },
    stop() {
      if (timer) clearInterval(timer);
      socket?.close();
      socket = null;
    },
  };
}
