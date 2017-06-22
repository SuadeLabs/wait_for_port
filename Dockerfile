FROM alpine:3.6
RUN mkdir /app
WORKDIR /app
ADD requirements.txt ./
RUN apk add --update python python-dev py-pip gcc musl-dev postgresql-dev && \
    pip install --upgrade pip && \
    pip install -r requirements.txt && \
    apk del gcc musl-dev python-dev py-pip && \
    rm -rf /var/cache/apk/*
ADD wait_for_port.py ./
ENTRYPOINT ["/app/wait_for_port.py"]
