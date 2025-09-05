
import json
from datetime import datetime
from typing import Dict, List, Any
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class TaskMemory:
    id: str
    timestamp: datetime
    description: str
    progress: Dict[str, Any]
    decisions: List[Dict[str, str]]
    context: str
    files_changed: List[str]
    next_steps: List[str]
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TaskMemory':
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


class TaskMemoryManager:
    
    def __init__(self, memory_dir: str = ".hakken"):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(exist_ok=True)
        self.memory_file = self.memory_dir / "task_memory.jsonl"
    
    def save_memory(self, memory: TaskMemory) -> bool:
        try:
            with open(self.memory_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(memory.to_dict(), ensure_ascii=False) + '\n')
            return True
        except Exception as e:
            print(f"Memory save failed: {e}")
            return False
    
    def get_recent_memories(self, days: int = 7) -> List[TaskMemory]:
        if not self.memory_file.exists():
            return []
        
        cutoff = datetime.now().timestamp() - (days * 24 * 3600)
        memories = []
        
        try:
            with open(self.memory_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        memory = TaskMemory.from_dict(data)
                        if memory.timestamp.timestamp() >= cutoff:
                            memories.append(memory)
        except Exception as e:
            print(f"Memory load failed: {e}")
            return []
        
        return sorted(memories, key=lambda x: x.timestamp, reverse=True)
    
    def find_similar_tasks(self, description: str, limit: int = 3) -> List[TaskMemory]:
        all_memories = self.get_recent_memories(days=30)
        keywords = set(description.lower().split())
        
        scored_memories = []
        for memory in all_memories:
            memory_words = set(memory.description.lower().split())
            overlap = len(keywords.intersection(memory_words))
            if overlap > 0:
                scored_memories.append((overlap, memory))
        
        scored_memories.sort(key=lambda x: x[0], reverse=True)
        return [memory for _, memory in scored_memories[:limit]]
    
    def get_context_summary(self, days: int = 3) -> str:
        memories = self.get_recent_memories(days)
        if not memories:
            return "No recent task context available."
        
        summary = f"Recent task context ({len(memories)} entries):\n"
        for memory in memories[:5]:
            summary += f"- {memory.description} ({memory.timestamp.strftime('%m-%d %H:%M')})\n"
            if memory.next_steps:
                summary += f"  Next: {', '.join(memory.next_steps[:2])}\n"
        
        return summary
