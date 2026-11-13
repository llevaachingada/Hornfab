"""Offline study registry and adaptive-package orchestration.

Importing this package opens no databases, imports no optional engine and
starts no lane/solver process.
"""
from .package import (ADAPTIVE_POLICY, EXECUTION_BUDGET, EXECUTION_MODE, PACKAGE_KIND,
                      PACKAGE_SCHEMA, RECOVERY_RULES, STATUS_NOTE, STOP_RULES,
                      VERIFICATION_POLICY, package_hash, prepare_run_package, verify_package)
from .builders import (ANALYSIS_SCHEMA, MODEL_MANIFEST_SCHEMA, POOL_MANIFEST_SCHEMA,
                       PROPOSAL_SCHEMA, SNAPSHOT_SCHEMA, TRAINING_MANIFEST_SCHEMA,
                       build_analysis, build_proposal, build_training, freeze_snapshot)
from .evaluator import PipelineStudyEvaluator, build_production_wiring
from .runner import (CAPABILITY_MISSING, CapabilityMissing, ContractError,
                     StudyEvaluatorAdapter, decode_proposal_history, encode_proposal_history,
                     run_package, select_verification)
from .schema import Conflict, NotFound, StudyError, Unavailable, canonical, digest, validate_spec
from .service import DraftAttemptJournal, StudyService

__all__ = [
    'ADAPTIVE_POLICY', 'EXECUTION_BUDGET', 'EXECUTION_MODE', 'PACKAGE_KIND', 'PACKAGE_SCHEMA',
    'RECOVERY_RULES', 'STATUS_NOTE', 'STOP_RULES', 'VERIFICATION_POLICY',
    'package_hash', 'prepare_run_package', 'verify_package',
    'ANALYSIS_SCHEMA', 'MODEL_MANIFEST_SCHEMA', 'POOL_MANIFEST_SCHEMA', 'PROPOSAL_SCHEMA',
    'SNAPSHOT_SCHEMA', 'TRAINING_MANIFEST_SCHEMA',
    'build_analysis', 'build_proposal', 'build_training', 'freeze_snapshot',
    'PipelineStudyEvaluator', 'build_production_wiring',
    'CAPABILITY_MISSING', 'CapabilityMissing', 'ContractError', 'StudyEvaluatorAdapter',
    'decode_proposal_history', 'encode_proposal_history', 'run_package', 'select_verification',
    'Conflict', 'NotFound', 'StudyError', 'Unavailable', 'canonical', 'digest', 'validate_spec',
    'DraftAttemptJournal', 'StudyService',
]
