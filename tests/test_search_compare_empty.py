"""`compare` on two runs with empty frequency lists fails with a message, not an IndexError. Offline."""
from types import SimpleNamespace

import pytest

from hornlab_search.cli import compare_metrics


def test_empty_frequency_lists_raise_value_error():
    m = SimpleNamespace(freqs_hz=[])
    with pytest.raises(ValueError, match="empty frequency list"):
        compare_metrics(m, m)
