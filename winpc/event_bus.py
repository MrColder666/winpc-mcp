"""事件总线：MCP 工具调用、对话同步、系统状态 → Dashboard SSE 推送。

内存实现：一个 asyncio 队列环 + 历史缓冲区。多订阅者各自消费同一事件流。
"""
import asyncio
import time
from collections import deque
from typing import Any, Dict, List

MAX_HISTORY = 500  # 浏览器打开时回放的最大事件数


class EventBus:
    def __init__(self) -> None:
        self._subscribers: List[asyncio.Queue] = []
        self._history: deque = deque(maxlen=MAX_HISTORY)
        self._lock = asyncio.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None

    def attach_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """在应用 lifespan 中绑定主事件循环（供线程安全发布使用）。"""
        self._loop = loop

    def publish_sync(self, event: Dict[str, Any]) -> None:
        """线程安全的同步发布：工具 wrapper（worker 线程）与异步端点均可调用。"""
        event.setdefault("ts", time.time())
        self._history.append(event)
        loop = self._loop
        if loop is not None and loop.is_running():
            loop.call_soon_threadsafe(self._broadcast_nowait, event)
        else:
            self._broadcast_nowait(event)

    def _broadcast_nowait(self, event: Dict[str, Any]) -> None:
        for q in list(self._subscribers):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass

    async def publish(self, event: Dict[str, Any]) -> None:
        """发布事件：追加历史 + 广播给所有订阅者。"""
        self.publish_sync(event)

    def history(self, limit: int = 200) -> List[Dict[str, Any]]:
        """返回历史事件（新的在前）。"""
        items = list(self._history)[-limit:]
        return list(reversed(items))

    async def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=1000)
        async with self._lock:
            self._subscribers.append(q)
        return q

    async def unsubscribe(self, q: asyncio.Queue) -> None:
        async with self._lock:
            if q in self._subscribers:
                self._subscribers.remove(q)


bus = EventBus()
