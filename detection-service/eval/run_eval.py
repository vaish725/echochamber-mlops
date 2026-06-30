"""Manual evaluation harness — scores the current prompt/model against a
hand-labeled dataset and logs the result to MLflow. Costs real OpenAI API
calls; not run in CI.

Usage (from detection-service/):
    pip install -r eval/requirements.txt
    python -m eval.run_eval
"""
import asyncio
import csv
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from app.config import get_settings
from app.detector import MisinformationDetector
from app.schemas import MisinformationLabel, Post
from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support

import mlflow

DATASET_PATH = Path(__file__).parent / "dataset.jsonl"
LABELS = [label.value for label in MisinformationLabel]


def _load_dataset() -> list[dict]:
    rows = []
    with DATASET_PATH.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


async def _classify_all(detector: MisinformationDetector, rows: list[dict]) -> list[str]:
    predictions = []
    for row in rows:
        post = Post(
            user_id="eval",
            username="eval",
            post_text=row["post_text"],
            created_at=datetime.now(timezone.utc).isoformat(),
            location="N/A, N/A",
        )
        detection = await detector.classify(post)
        predictions.append(detection.label.value)
    return predictions


def _confusion_matrix_csv(y_true: list[str], y_pred: list[str]) -> str:
    matrix = confusion_matrix(y_true, y_pred, labels=LABELS)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([""] + LABELS)
    for label, row in zip(LABELS, matrix):
        writer.writerow([label] + list(row))
    return buf.getvalue()


async def main() -> None:
    settings = get_settings()
    rows = _load_dataset()
    y_true = [row["true_label"] for row in rows]

    detector = MisinformationDetector(settings)
    y_pred = await _classify_all(detector, rows)

    accuracy = accuracy_score(y_true, y_pred)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, labels=LABELS, average="macro", zero_division=0
    )

    print(f"Examples evaluated: {len(rows)}")
    print(f"Accuracy:           {accuracy:.3f}")
    print(f"Precision (macro):  {precision:.3f}")
    print(f"Recall (macro):     {recall:.3f}")
    print(f"F1 (macro):         {f1:.3f}")

    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    mlflow.set_experiment(f"{settings.mlflow_experiment_name}-eval")
    run_name = f"eval-{settings.prompt_version}-{datetime.now(timezone.utc):%Y%m%dT%H%M%S}"
    with mlflow.start_run(run_name=run_name):
        mlflow.set_tag("prompt_version", settings.prompt_version)
        mlflow.log_param("prompt_version", settings.prompt_version)
        mlflow.log_param("model", settings.llm_model)
        mlflow.log_param("dataset_size", len(rows))
        mlflow.log_metric("accuracy", accuracy)
        mlflow.log_metric("precision_macro", precision)
        mlflow.log_metric("recall_macro", recall)
        mlflow.log_metric("f1_macro", f1)
        mlflow.log_text(_confusion_matrix_csv(y_true, y_pred), "confusion_matrix.csv")

    print(
        f"\nLogged to MLflow experiment '{settings.mlflow_experiment_name}-eval' "
        f"as run '{run_name}'"
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(1)
