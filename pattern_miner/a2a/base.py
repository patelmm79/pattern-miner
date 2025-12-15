# pattern_miner/a2a/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any, List


class BaseSkill(ABC):
    """Base class for all A2A skills"""

    @property
    @abstractmethod
    def skill_id(self) -> str:
        """Unique identifier for the skill"""
        pass

    @property
    @abstractmethod
    def skill_name(self) -> str:
        """Human-readable name"""
        pass

    @property
    @abstractmethod
    def skill_description(self) -> str:
        """Description of what the skill does"""
        pass

    @property
    @abstractmethod
    def tags(self) -> List[str]:
        """Tags for categorizing the skill"""
        pass

    @property
    @abstractmethod
    def input_schema(self) -> Dict[str, Any]:
        """JSON schema for input validation"""
        pass

    @property
    def examples(self) -> List[Dict[str, Any]]:
        """Optional examples of skill usage"""
        return []

    @abstractmethod
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the skill with given input"""
        pass

    def to_agent_card_entry(self) -> Dict[str, Any]:
        """Convert skill to AgentCard format"""
        return {
            "id": self.skill_id,
            "name": self.skill_name,
            "description": self.skill_description,
            "tags": self.tags,
            "input_schema": self.input_schema,
            "examples": self.examples
        }
