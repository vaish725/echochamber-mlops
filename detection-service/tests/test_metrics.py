from prometheus_client import REGISTRY


def test_all_required_metrics_registered():
    """FR-6.1: All five required metric names must exist in the Prometheus registry.

    prometheus_client strips the _total suffix from Counter names internally;
    _total is added only in the exported text format. Histograms and Gauges
    keep their full names.
    """
    names = {m.name for m in REGISTRY.collect()}
    # Counters: registry stores base name, _total appears only in /metrics output
    required_counters = {
        "echochamber_posts_processed",
        "echochamber_detections_by_label",
        "echochamber_errors",
    }
    # Histograms and Gauges keep their names as-is
    required_others = {
        "echochamber_llm_request_duration_seconds",
        "echochamber_kafka_consumer_lag",
    }
    missing = (required_counters | required_others) - names
    assert not missing, f"Missing metrics in registry: {missing}"
