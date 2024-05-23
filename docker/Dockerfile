FROM python:3.11.8-slim AS builder

#needed
RUN apt-get -y update && apt-get -y upgrade \
    && apt-get install -y git awscli curl make  default-jre-headless \
    --no-install-recommends && apt-get -y clean \
    && rm -rf /var/lib/apt/lists/*
# Set environment variables for configuration

WORKDIR /project
RUN mkdir ./.git
COPY poetry.lock .pre-commit-config.yaml pyproject.toml ./
COPY .git ./.git
RUN pip install poetry && poetry config virtualenvs.in-project true
RUN poetry install
ENV PATH="/project/.venv/bin:$PATH"
RUN git config --global --add safe.directory /project/opt/local && git ls-files
RUN poetry run pre-commit install --install-hooks

WORKDIR /project/opt/local
RUN addgroup --system app && adduser --system --group app
RUN . /project/.venv/bin/activate

ENTRYPOINT ["/bin/bash"]
