# pattern_miner/a2a/registry.py
from typing import Dict, List
from pattern_miner.a2a.base import BaseSkill

class SkillRegistry:
    """Registry for all A2A skills"""

    def __init__(self):
        self._skills: Dict[str, BaseSkill] = {}

    def register(self, skill: BaseSkill):
        self._skills[skill.skill_id] = skill

    def get_skill(self, skill_id: str) -> BaseSkill:
        return self._skills.get(skill_id)

    def get_skill_ids(self) -> List[str]:
        return list(self._skills.keys())

    def to_agent_card_skills(self) -> List[Dict]:
        return [skill.to_agent_card_entry() for skill in self._skills.values()]

# Global registry instance
_registry = None

def get_registry() -> SkillRegistry:
    global _registry
    if _registry is None:
        _registry = SkillRegistry()
    return _registry