import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any

from faker import Faker
from kafka import KafkaProducer

fake = Faker()

_bootstrap = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")


class _JsonFormatter(logging.Formatter):
    _skip = {
        "args", "created", "exc_info", "exc_text", "filename", "funcName",
        "levelname", "levelno", "lineno", "message", "module", "msecs",
        "msg", "name", "pathname", "process", "processName",
        "relativeCreated", "stack_info", "thread", "threadName",
    }

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": "producer",
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        for key, value in record.__dict__.items():
            if key not in self._skip:
                entry[key] = value
        return json.dumps(entry)


_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(_JsonFormatter())
_root = logging.getLogger()
_root.setLevel(logging.INFO)
_root.handlers = [_handler]

logger = logging.getLogger(__name__)


def _json_serializer(data: Any) -> bytes:
    return json.dumps(data).encode("utf-8")


producer = KafkaProducer(
    bootstrap_servers=[_bootstrap],
    value_serializer=_json_serializer,
)

if __name__ == "__main__":
    logger.info("Starting data production", extra={"bootstrap_servers": _bootstrap})
    while True:
        try:
            post = {
                "user_id": fake.uuid4(),
                "username": fake.user_name(),
                "post_text": fake.text(max_nb_chars=140),
                "created_at": fake.iso8601(),
                "location": f"{fake.city()}, {fake.country()}",
            }
            producer.send("social-media-stream", post)
            logger.info("Post produced", extra={"post_id": post["user_id"]})
            time.sleep(2)
        except KeyboardInterrupt:
            logger.info("Stopping data production")
            break
        except Exception:
            logger.exception("Failed to produce message")
            time.sleep(5)
    producer.close()
