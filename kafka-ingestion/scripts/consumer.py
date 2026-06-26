import json
from kafka import KafkaConsumer

if __name__ == "__main__":
    # Initialize Kafka Consumer
    consumer = KafkaConsumer(
        "social-media-stream",
        bootstrap_servers=['localhost:9092'],
        auto_offset_reset='earliest', # Start reading at the earliest message
        group_id="misinformation-detectors-group-1", # Consumer group ID
        value_deserializer=lambda x: json.loads(x.decode('utf-8'))
    )

    print("Starting consumer... Listening for messages.")
    try:
        for message in consumer:
            # message.value is the deserialized JSON data
            print(f"Received: {message.value}")
    except KeyboardInterrupt:
        print("\nStopping consumer.")
    finally:
        consumer.close()