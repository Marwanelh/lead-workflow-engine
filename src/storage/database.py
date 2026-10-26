import asyncio
from typing import Dict, Optional, List
from datetime import datetime, timezone
from ..models.task import AgentTask, TaskStatus

class InMemoryTaskRepository:
    """
    Thread-safe repository for agent tasks and human-in-the-loop review state.
    """
    def __init__(self):
        self._tasks: Dict[str, AgentTask] = {}
        self._lock = asyncio.Lock()

    async def save_task(self, task: AgentTask) -> None:
        async with self._lock:
            task.updated_at = datetime.now(timezone.utc)
            self._tasks[task.task_id] = task

    async def get_task(self, task_id: str) -> Optional[AgentTask]:
        async with self._lock:
            return self._tasks.get(task_id)

    async def list_pending_approvals(self) -> List[AgentTask]:
        async with self._lock:
            return [
                t for t in self._tasks.values() 
                if t.status == TaskStatus.WAITING_APPROVAL
            ]

    async def list_all(self) -> List[AgentTask]:
        async with self._lock:
            return list(self._tasks.values())
