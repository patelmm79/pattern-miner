# pattern_miner/a2a/__init__.py
"""A2A Protocol Support for Pattern Miner"""

# pattern_miner/a2a/base.py
from typing import Dict, Any, List
from abc import ABC, abstractmethod

class BaseSkill(ABC):
    """Base class for Pattern Miner A2A skills"""

    @property
    @abstractmethod
    def skill_id(self) -> str:
        pass

    @property
    @abstractmethod
    def skill_name(self) -> str:
        pass

    @property
    @abstractmethod
    def skill_description(self) -> str:
        pass

    @property
    @abstractmethod
    def input_schema(self) -> Dict[str, Any]:
        pass

    @property
    def tags(self) -> List[str]:
        return []

    @property
    def requires_authentication(self) -> bool:
        return False

    @property
    def examples(self) -> List[Dict[str, Any]]:
        return []

    @abstractmethod
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        pass

    def to_agent_card_entry(self) -> Dict[str, Any]:
        return {
            "id": self.skill_id,
            "name": self.skill_name,
            "description": self.skill_description,
            "tags": self.tags,
            "requires_authentication": self.requires_authentication,
            "input_schema": self.input_schema,
            "examples": self.examples
        }