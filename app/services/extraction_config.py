from dataclasses import dataclass
from typing import Optional, Callable, List
from enum import Enum


class ProcessingStrategy(str, Enum):
    INCREMENTAL = "incremental"
    PARALLEL = "parallel"
    SLIDING_WINDOW = "sliding_window"


class ConfidenceMergeStrategy(str, Enum):
    MAX = "max"
    WEIGHTED_AVG = "weighted_avg"
    ACCUMULATE = "accumulate"


@dataclass
class ExtractionConfig:
    strategy: ProcessingStrategy = ProcessingStrategy.INCREMENTAL
    chunk_size: int = 1500
    chunk_overlap: int = 100
    max_concurrent_chunks: int = 3
    enable_parallel_processing: bool = False
    entity_similarity_threshold: float = 0.8
    confidence_merge_strategy: ConfidenceMergeStrategy = ConfidenceMergeStrategy.MAX
    enable_entity_aliasing: bool = True
    enable_cross_chunk_relations: bool = True
    relation_confidence_threshold: float = 0.6
    max_relation_distance: int = 3
    enable_context_enhancement: bool = True
    max_context_entities: int = 10
    context_window_size: int = 2
    enable_caching: bool = True
    cache_max_size: int = 1000
    enable_progress_tracking: bool = True
    min_entity_confidence: float = 0.3
    min_relationship_confidence: float = 0.4
    enable_duplicate_filtering: bool = True
    max_retries: int = 3
    continue_on_chunk_error: bool = True
    progress_callback: Optional[Callable[[int, int, int, int], None]] = None
    error_callback: Optional[Callable[[Exception, int], None]] = None
    enable_debug_logging: bool = False
    log_intermediate_results: bool = False
    
    def validate(self) -> List[str]:
        errors = []
        if self.chunk_size <= 0:
            errors.append("chunk_size must be positive")
        if self.chunk_overlap >= self.chunk_size:
            errors.append("chunk_overlap must be less than chunk_size")
        if not 0 <= self.entity_similarity_threshold <= 1:
            errors.append("entity_similarity_threshold must be between 0 and 1")
        if not 0 <= self.relation_confidence_threshold <= 1:
            errors.append("relation_confidence_threshold must be between 0 and 1")
        if self.max_concurrent_chunks <= 0:
            errors.append("max_concurrent_chunks must be positive")
        return errors
    
