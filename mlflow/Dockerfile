FROM python:3.11-slim

WORKDIR /mlflow

RUN pip install --no-cache-dir mlflow>=2.14.0 psycopg2-binary>=2.9.0 boto3>=1.34.0

EXPOSE 5000

CMD mlflow server --host 0.0.0.0 --port 5000 --backend-store-uri $BACKEND_STORE_URI --default-artifact-root $ARTIFACT_ROOT
