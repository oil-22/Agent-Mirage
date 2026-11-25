"""One extra gray-band request can be considered, independent of the capture implementation."""
from toggle_protocol import gray


def route(arm, current, prior, extra_spent):
    """Classify a fresh standard result without changing its reported choice."""
    if current['decision'] == 'YES':
        return 'original_yes'
    assert current['decision'] == 'NO'
    if arm == 'global046' and gray(current):
        return 'comparator_046'
    if arm == 'scoped' and not extra_spent and prior is not None and gray(prior) and gray(current):
        return 'evaluate_control_hit'
    return 'hold'
