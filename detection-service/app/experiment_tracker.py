import logging
import statistics
import time
from collections import Counter

import mlflow
from app.config import Settings
from app.schemas import Detection

logger = logging.getLogger(__name__)


class ExperimentTracker:
    """Aggregates classification results over a time window and logs one
    MLflow run per window, instead of one run per message."""

    def __init__(self, settings: Settings) -> None:
        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        mlflow.set_experiment(settings.mlflow_experiment_name)
        self._model = settings.llm_model
        self._prompt_version = settings.prompt_version
        self._flush_interval = settings.mlflow_flush_interval_seconds
        self._reset()

    def _reset(self) -> None:
        self._confidences: list[float] = []
        self._labels: Counter[str] = Counter()
        self._window_start = time.monotonic()

    def record(self, detection: Detection) -> None:
        self._confidences.append(detection.confidence)
        self._labels[detection.label.value] += 1

    def should_flush(self) -> bool:
        elapsed = time.monotonic() - self._window_start
        return bool(self._confidences) and elapsed >= self._flush_interval

    def flush(self) -> None:
        if not self._confidences:
            return
        try:
            with mlflow.start_run():
                mlflow.log_param("prompt_version", self._prompt_version)
                mlflow.log_param("model", self._model)
                mlflow.log_metric("messages_classified", len(self._confidences))
                mlflow.log_metric("avg_confidence", statistics.mean(self._confidences))
                for label, count in self._labels.items():
                    mlflow.log_metric(f"label_count_{label.lower()}", count)
        except Exception:
            logger.exception("Failed to log MLflow run — continuing without tracking")
        finally:
            self._reset()
