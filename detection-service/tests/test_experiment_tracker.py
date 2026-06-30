from unittest.mock import MagicMock, patch

import pytest
from app.experiment_tracker import ExperimentTracker
from app.schemas import Detection, MisinformationLabel


@pytest.fixture
def mock_mlflow():
    with patch("app.experiment_tracker.mlflow") as m:
        yield m


@pytest.fixture
def tracker(settings, mock_mlflow):
    return ExperimentTracker(settings)


def _detection(label=MisinformationLabel.CREDIBLE, confidence=0.9) -> Detection:
    return Detection(
        post_id="p1",
        post_text="test",
        label=label,
        confidence=confidence,
        reasoning="r",
        model_version="gpt-4o",
        prompt_version="v1",
    )


def test_init_configures_mlflow_tracking_uri_and_experiment(settings, mock_mlflow):
    ExperimentTracker(settings)
    mock_mlflow.set_tracking_uri.assert_called_once_with(settings.mlflow_tracking_uri)
    mock_mlflow.set_experiment.assert_called_once_with(settings.mlflow_experiment_name)


def test_record_aggregates_confidence_and_labels(tracker):
    tracker.record(_detection(MisinformationLabel.CREDIBLE, 0.9))
    tracker.record(_detection(MisinformationLabel.MISINFORMATION, 0.7))

    assert tracker._confidences == [0.9, 0.7]
    assert tracker._labels["CREDIBLE"] == 1
    assert tracker._labels["MISINFORMATION"] == 1


def test_should_flush_false_when_window_empty(tracker):
    assert tracker.should_flush() is False


def test_should_flush_false_before_interval_elapsed(tracker):
    tracker.record(_detection())
    assert tracker.should_flush() is False


def test_should_flush_true_after_interval_elapsed(tracker):
    tracker.record(_detection())
    tracker._window_start -= tracker._flush_interval + 1
    assert tracker.should_flush() is True


def test_flush_logs_params_and_metrics_then_resets(tracker, mock_mlflow):
    tracker.record(_detection(MisinformationLabel.CREDIBLE, 0.8))
    tracker.record(_detection(MisinformationLabel.MISINFORMATION, 0.6))
    mock_mlflow.start_run.return_value.__enter__.return_value = MagicMock()

    tracker.flush()

    mock_mlflow.log_param.assert_any_call("prompt_version", tracker._prompt_version)
    mock_mlflow.log_param.assert_any_call("model", tracker._model)
    mock_mlflow.log_metric.assert_any_call("messages_classified", 2)
    mock_mlflow.log_metric.assert_any_call("avg_confidence", 0.7)
    mock_mlflow.log_metric.assert_any_call("label_count_credible", 1)
    mock_mlflow.log_metric.assert_any_call("label_count_misinformation", 1)

    assert tracker._confidences == []
    assert tracker.should_flush() is False


def test_flush_noop_when_window_empty(tracker, mock_mlflow):
    tracker.flush()
    mock_mlflow.start_run.assert_not_called()


def test_flush_swallows_mlflow_errors(tracker, mock_mlflow):
    tracker.record(_detection())
    mock_mlflow.start_run.side_effect = Exception("MLflow unreachable")

    tracker.flush()  # must not raise

    assert tracker._confidences == []
