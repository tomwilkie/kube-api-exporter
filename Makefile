all: .uptodate

IMAGE_VERSION := $(shell git rev-parse --abbrev-ref HEAD)-$(shell git rev-parse --short HEAD)

.uptodate: Dockerfile main.py
	docker build -t tomwilkie/kube-api-exporter .
	docker tag tomwilkie/kube-api-exporter:latest tomwilkie/kube-api-exporter:$(IMAGE_VERSION)
	touch $@

clean:
	rm .uptodate
