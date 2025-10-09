# syntax=docker/dockerfile:1.4

FROM python:3.14-rc-alpine as builder

WORKDIR /app 
COPY requirements.txt /app

RUN apk --no-cache add jpeg-dev zlib-dev libjpeg libffi-dev && \
  apk add --no-cache --virtual .build-deps gcc python3-dev musl-dev && \
  pip3 install -r requirements.txt --no-cache-dir && \
  apk del .build-deps && \
  pip3 install gunicorn

COPY . /app

# get .env during build in case of baking config into image
# ARG ENV_FILE_CONTENT=""
# ENV ENV_FILE_CONTENT=$ENV_FILE_CONTENT
# RUN echo "$$ENV_FILE_CONTENT" > .env

# update entrypoint and cmd from docker compose
# this ensures we customization
# ENTRYPOINT ["gunicorn"]
