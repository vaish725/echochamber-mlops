from prometheus_client import Counter, Gauge, Histogram

posts_processed_total = Counter(
    "echochamber_posts_processed_total",
    "Total posts processed by the detection service",
)

detections_by_label_total = Counter(
    "echochamber_detections_by_label_total",
    "Total detections by classification label",
    ["label"],
)

llm_request_duration_seconds = Histogram(
    "echochamber_llm_request_duration_seconds",
    "LLM API call latency in seconds",
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
)

kafka_consumer_lag = Gauge(
    "echochamber_kafka_consumer_lag",
    "Approximate Kafka consumer lag in messages",
    ["partition"],
)

errors_total = Counter(
    "echochamber_errors_total",
    "Total errors encountered",
    ["error_type"],
)
