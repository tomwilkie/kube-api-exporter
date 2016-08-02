FROM alpine:3.4
WORKDIR /
RUN apk add --update python python-dev py-pip && \
	rm -rf /var/cache/apk/*
RUN pip install pykube
COPY main.py /
ENTRYPOINT ["/main.py"]
