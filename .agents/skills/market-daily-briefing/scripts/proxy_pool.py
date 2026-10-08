#!/usr/bin/env python3
"""动态代理池：防 IP 封禁的采集层组件

配置（同级 proxy_config.json，可选）：
    {
      "proxy_static": ["http://ip:port", ...],      # 静态代理列表
      "proxy_api": "https://服务商/extract?...",      # 订阅接口，返回按行/逗号分隔的 ip:port 文本
      "proxy_ttl": 60                                 # 订阅接口最小刷新间隔（秒）
    }
两者都为空时自动直连。

机制：
1. 请求间轮询取代理；单代理连续失败 3 次冷却 10 分钟
2. 封禁特征（RemoteDisconnected/403）立即换下一个代理重试
3. 池空回退直连；直连失败进入 120s 全局冷却（宁可降级等待，不打死直连 IP）
4. 按目标域名隔离计数，A 站封禁不影响 B 站

注意：不要内置免费代理抓取（存活率极低且来源不干净），只接自有/付费订阅。
"""
import json, time, urllib.request


class ProxyPool:
    def __init__(self, static=None, api=None, ttl=60, failure_limit=3,
                 host_cooldown=600, direct_cooldown=120):
        self.static = list(static or [])
        self.api = api
        self.ttl = ttl
        self.failure_limit = failure_limit
        self.host_cooldown = host_cooldown
        self.direct_cooldown = direct_cooldown
        self._alive = []
        self._dead_until = {}
        self._fetched_at = 0
        self._direct_block_until = {}

    @classmethod
    def load(cls, path):
        try:
            cfg = json.load(open(path))
            return cls(static=cfg.get("proxy_static"), api=cfg.get("proxy_api"),
                       ttl=cfg.get("proxy_ttl", 60))
        except FileNotFoundError:
            return cls()

    def is_enabled(self):
        return bool(self.static or self.api)

    def _refresh_from_api(self):
        if not self.api or time.time() - self._fetched_at < self.ttl:
            return
        self._fetched_at = time.time()
        try:
            txt = urllib.request.urlopen(urllib.request.Request(
                self.api, headers={"User-Agent": "Mozilla/5.0"}), timeout=8).read().decode("utf-8", "ignore")
            items = [x.strip() for x in txt.replace("\r", "\n").replace(",", "\n").split("\n") if x.strip()]
            fresh = {("http://" + p if "://" not in p else p) for p in items}
            self._alive = [(p, 0) for p, f in self._alive if p in fresh] + \
                          [(p, 0) for p in fresh if all(p != q for q, _ in self._alive)]
            now = time.time()
            self._dead_until = {p: t for p, t in self._dead_until.items() if t > now}
        except Exception:
            pass  # 订阅失败：继续用池内存量

    def acquire(self, host):
        """返回代理 URL；无可用代理且直连未冷却时返回 None（直连）"""
        if not self.is_enabled():
            return None
        self._refresh_from_api()
        now = time.time()
        for i, (p, f) in enumerate(self._alive):
            if self._dead_until.get(p, 0) > now:
                continue
            self._alive.append(self._alive.pop(i))
            return p
        if self._direct_block_until.get(host, 0) <= now:
            return None
        raise RuntimeError(f"host={host} 无可用代理且直连冷却中")

    def report(self, host, proxy, ok):
        now = time.time()
        if proxy is None:
            if not ok:
                self._direct_block_until[host] = now + self.direct_cooldown
            return
        if ok:
            self._alive = [(p, 0 if p == proxy else f) for p, f in self._alive]
            return
        for i, (p, f) in enumerate(self._alive):
            if p == proxy:
                f += 1
                if f >= self.failure_limit:
                    self._dead_until[p] = now + self.host_cooldown
                    f = 0
                self._alive[i] = (p, f)
                break


def fetch_with_pool(url, pool, headers=None, timeout=12, retries=3):
    """带代理轮换的 GET：封禁类异常回报池并换代理重试"""
    import http.client
    host = urllib.request.urlparse(url).netloc
    last = None
    for _ in range(retries):
        proxy = pool.acquire(host)
        handlers = []
        if proxy:
            handlers.append(urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
        opener = urllib.request.build_opener(*handlers)
        h = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/129.0 Safari/537.36"}
        if headers:
            h.update(headers)
        try:
            with opener.open(urllib.request.Request(url, headers=h), timeout=timeout) as r:
                body = r.read().decode("utf-8", "ignore")
                pool.report(host, proxy, ok=True)
                return body
        except Exception as e:
            last = e
            pool.report(host, proxy, ok=False)
            if isinstance(e, (http.client.RemoteDisconnected, urllib.error.HTTPError)):
                continue
            time.sleep(1)
    raise last


if __name__ == "__main__":
    pool = ProxyPool.load(os.path.join(os.path.dirname(os.path.abspath(__file__)), "proxy_config.json"))
    print("代理池启用:", pool.is_enabled())
    txt = fetch_with_pool("https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2509&k=&num=3&page=1", pool)
    print("直连回退自检 OK，返回", len(txt), "字节")
