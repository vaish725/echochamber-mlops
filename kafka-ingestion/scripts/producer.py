import json
import os
import time

from faker import Faker
from kafka import KafkaProducer

fake = Faker()

_bootstrap = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")


def json_serializer(data):
    return json.dumps(data).encode("utf-8")


producer = KafkaProducer(
    bootstrap_servers=[_bootstrap],
    value_serializer=json_serializer,
)

if __name__ == "__main__":
    print("Starting data production... Press Ctrl+C to stop.")
    while True:
        try:
            # Generate a fake social media post
            post = {
                "user_id": fake.uuid4(),
                "username": fake.user_name(),
                "post_text": fake.text(max_nb_chars=140),
                "created_at": fake.iso8601(),
                "location": f"{fake.city()}, {fake.country()}"
            }

            # Send the message to the 'social-media-stream' topic
            print(f"Sending: {post}")
            producer.send("social-media-stream", post)

            # Wait for a short interval before sending the next message
            time.sleep(2)

        except KeyboardInterrupt:
            print("\nStopping data production.")
            break
        except Exception as e:
            print(f"An error occurred: {e}")
            time.sleep(5) # Wait before retrying

    producer.close()