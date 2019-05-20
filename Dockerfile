FROM alpine:3.6
RUN mkdir /app
WORKDIR /app
COPY requirements.txt ./
RUN apk add --update python3 python3-dev gcc musl-dev postgresql-dev && \
    pip3 install --upgrade pip && \
    pip3 install -r requirements.txt && \
    apk del gcc musl-dev python3-dev py-pip && \
    rm -rf /var/cache/apk/*
COPY wait_for_port.py ./
ENTRYPOINT ["/app/wait_for_port.py"]
