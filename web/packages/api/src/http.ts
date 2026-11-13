/** 传输抽象：H5 用 fetch，小程序/APP 注入 uni.request。 */
export interface HttpTransport {
  get<T>(path: string, query?: Record<string, string>): Promise<T>;
}

export interface ApiConfig {
  baseUrl: string;
  token?: () => string | null;
}

export function createFetchTransport(config: ApiConfig): HttpTransport {
  return {
    async get<T>(path: string, query?: Record<string, string>): Promise<T> {
      const base = config.baseUrl.startsWith("/")
        ? `${globalThis.location?.origin ?? ""}${config.baseUrl}`
        : config.baseUrl;
      const url = new URL(path, base);
      Object.entries(query ?? {}).forEach(([k, v]) => url.searchParams.set(k, v));
      const token = config.token?.();
      const response = await fetch(url, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return (await response.json()) as T;
    },
  };
}
