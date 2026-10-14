"""Phase 2, stage A: metric surrogate (11_PHASE2_SURROGATE section 4).

``gates`` is pure numpy and always importable. ``features``/``model``/``train``/``predict``
need the optional ``torch`` dependency (``pip install -e ".[surrogate]"``) and are imported
lazily; importing this package never imports torch.
"""
