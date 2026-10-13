"""Objective: MetricSet + Target + weights -> a scalar J and its terms. Lower is better."""
from .scalar import (ALL_KEYS, DEFAULT_WEIGHTS, PENALTY_FAILED, PENALTY_INVALID, TERM_KEYS,
                     WEIGHTED_KEYS, objective, penalty_result, resolve_weights, weighted_terms)

__all__ = ["ALL_KEYS", "DEFAULT_WEIGHTS", "PENALTY_FAILED", "PENALTY_INVALID", "TERM_KEYS",
           "WEIGHTED_KEYS", "objective", "penalty_result", "resolve_weights", "weighted_terms"]
