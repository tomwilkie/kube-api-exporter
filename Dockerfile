FROM  frolvlad/alpine-python3
WORKDIR /
# RUN apk add --update python python-dev py-pip && \
#	rm -rf /var/cache/apk/*
RUN pip install pykube prometheus_client
COPY main.py /
ENTRYPOINT ["/usr/bin/python3", "/main.py"]
