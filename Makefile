.PHONY: deploy-local secrets clean-local

IMAGES = kafka-ingestion:producer detection-service:detection-service storage-sink:storage-sink mlflow:mlflow

deploy-local:
	minikube addons enable ingress
	minikube addons enable metrics-server
	eval $$(minikube docker-env) && \
	for pair in $(IMAGES); do \
		ctx=$${pair%%:*}; name=$${pair##*:}; \
		docker build -t echochamber/$$name:local ./$$ctx; \
	done
	kubectl apply -f k8s/namespace.yaml
	$(MAKE) secrets
	kubectl apply -f k8s/
	kubectl -n echochamber rollout status deployment/zookeeper --timeout=180s
	kubectl -n echochamber rollout status deployment/kafka --timeout=180s
	kubectl -n echochamber rollout status deployment/postgres --timeout=180s
	kubectl -n echochamber rollout status deployment/minio --timeout=180s
	kubectl -n echochamber wait --for=condition=complete job/minio-init --timeout=180s
	kubectl -n echochamber rollout status deployment/mlflow --timeout=180s
	kubectl -n echochamber rollout status deployment/producer --timeout=180s
	kubectl -n echochamber rollout status deployment/detection-service --timeout=180s
	kubectl -n echochamber rollout status deployment/storage-sink --timeout=180s

secrets:
	kubectl create namespace echochamber --dry-run=client -o yaml | kubectl apply -f -
	kubectl create secret generic echochamber-secrets -n echochamber \
		--from-env-file=.env --dry-run=client -o yaml | kubectl apply -f -

clean-local:
	kubectl delete namespace echochamber --ignore-not-found
