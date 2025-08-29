# memory.py
import time
from collections import deque

class SessionMemory:
    def __init__(self, max_turns: int = 20):
        self.max_turns = max_turns
        self.turns = deque()          # [{"role":"user/assistant", "content":"..."}]
        self.summary = ""              # 누적 요약
        self.turns_since_summary = 0   # 요약 갱신 주기 카운터
        self.updated_at = time.time()
        

    def add(self, role: str, content: str):
        if not content:
            return
        self.turns.append({"role": role, "content": content})
        while len(self.turns) > self.max_turns:
            self.turns.popleft()
        self.turns_since_summary += 1
        self.updated_at = time.time()

    def recent(self, k: int = 8):
        return list(self.turns)[-k:]

    def maybe_summarize(self, summarizer, threshold: int = 10):
        """
        threshold턴마다 요약 갱신 (예: 10)
        summarizer(turns, prev_summary) -> new_summary[str]
        """
        if self.turns_since_summary >= threshold:
            self.summary = summarizer(self.turns, self.summary)
            self.turns_since_summary = 0

class MemoryStore:
    def __init__(self):
        self._store = {}  # sessionId -> SessionMemory

    def get(self, session_id: str) -> SessionMemory:
        if session_id not in self._store:
            self._store[session_id] = SessionMemory()
        return self._store[session_id]

    def clear(self, session_id: str):
        self._store.pop(session_id, None)

MEMORY = MemoryStore()
