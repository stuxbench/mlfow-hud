"""Vulnerability specification and grading system for Stuxbench."""
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Literal, Optional

logger = logging.getLogger(__name__)


@dataclass(kw_only=True, frozen=True)
class SubGrade:
    """Individual component of a vulnerability assessment."""
    name: str
    score: float  # 0.0 to 1.0
    weight: float
    parameters: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(kw_only=True, frozen=True)
class Grade:
    """Overall grade for vulnerability patching attempt."""
    subscores: dict[str, float]
    weights: dict[str, float]
    metadata: dict[str, Any] | None
    
    @property
    def score(self):
        """Calculate weighted score."""
        assert self.subscores.keys() == self.weights.keys()
        assert abs(sum(self.weights.values()) - 1.0) < 0.001
        assert all(0 <= s <= 1 for s in self.subscores.values())
        
        score = sum(self.subscores[key] * self.weights[key] for key in self.subscores.keys())
        return max(0.0, min(1.0, score))
    
    @staticmethod
    def from_subscores(subscores: list[SubGrade]) -> "Grade":
        """Create Grade from list of SubGrades."""
        subscores_dict = {}
        weights_dict = {}
        metadata_dict = {}
        
        for subscore in subscores:
            subscores_dict[subscore.name] = subscore.score
            weights_dict[subscore.name] = subscore.weight
            if subscore.metadata:
                metadata_dict[subscore.name] = subscore.metadata
        
        return Grade(
            subscores=subscores_dict,
            weights=weights_dict,
            metadata=metadata_dict if metadata_dict else None
        )


@dataclass
class EnvironmentState:
    """Tracks the state of the MinIO testing environment."""
    minio_version: str
    patches_applied: List[str] = field(default_factory=list)


class Grader:
    """Base class for vulnerability graders."""
    name: str = "BaseGrader"
    
    @classmethod
    def grade(cls, state: EnvironmentState, weight: float, **kwargs) -> SubGrade:
        """Grade the current state and return a SubGrade."""
        result = cls.compute_score(state, **kwargs)
        
        if isinstance(result, tuple):
            score, metadata = result
        else:
            score = result
            metadata = {}
        
        return SubGrade(
            name=cls.name,
            score=score,
            weight=weight,
            parameters=kwargs,
            metadata=metadata
        )
    
    @classmethod
    def compute_score(cls, state: EnvironmentState, **kwargs) -> float | tuple[float, dict]:
        """Compute the score for this grader. Override in subclasses."""
        raise NotImplementedError