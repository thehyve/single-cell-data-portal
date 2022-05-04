FROM ubuntu:21.10

ENV APP_NAME=corpora-api
ENV DEPLOYMENT_STAGE=test
ENV EXPORT_ENV_VARS_TO_LAMBDA="APP_NAME DEPLOYMENT_STAGE"
ENV LC_ALL=C.UTF-8
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y python3 libhdf5-dev python3-h5py gettext moreutils build-essential libxml2-dev python3-dev python3-pip zlib1g-dev python3-requests python3-aiohttp llvm jq && \
    rm -rf /var/lib/apt/lists/*

# Make python3 the default 'python' executable.
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 1

# Don't re-run pip install unless either requirements.txt has changed.
WORKDIR /corpora-data-portal
ADD requirements.txt /corpora-data-portal/requirements.txt
ADD backend/corpora/api_server/requirements.txt /corpora-data-portal/requirements-api.txt
RUN grep -v requirements.txt requirements.txt > reqs.txt \
    && cat requirements-api.txt >> reqs.txt \
    && python3 -m pip install -r reqs.txt
EXPOSE 5050

# Install utilities to /corpora-data-portal so we can run db migrations.
ADD tests /corpora-data-portal/tests
ADD scripts /corpora-data-portal/scripts
ADD backend /corpora-data-portal/backend

ARG HAPPY_BRANCH="unknown"
ARG HAPPY_COMMIT=""
LABEL branch=${HAPPY_BRANCH}
LABEL commit=${HAPPY_COMMIT}
ENV COMMIT_SHA=${HAPPY_COMMIT}
ENV COMMIT_BRANCH=${HAPPY_BRANCH}

# Note: Using just 1 worker for dev/test env. Multiple workers are used in deployment envs, as defined in Terraform code.
CMD gunicorn --worker-class gevent --workers 1 --bind 0.0.0.0:5050 backend.corpora.api_server.app:app --max-requests 10000 --timeout 180 --keep-alive 5 --log-level info
