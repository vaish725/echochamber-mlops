# echochamber-mlops
A real-time misinformation detection system using Kafka, LLMs, and Kubernetes.

## Phase 1: System Architecture

The initial data ingestion pipeline consists of three main components:

1.  **Python Producer**: A script that generates fake social media post data and sends it to a Kafka topic.
2.  **Kafka Cluster**: A single-node Kafka broker running in a Docker container to act as the message bus.
3.  **Python Consumer**: A script that subscribes to the Kafka topic and reads the data stream in real-time.

```mermaid
graph TD
    A[Python Producer] -- JSON messages --> B(Kafka Topic: social-media-stream);
    B -- JSON messages --> C[Python Consumer];