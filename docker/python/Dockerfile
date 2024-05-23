FROM python:3.11.8-slim AS builder

#needed
RUN apt-get -y update && apt-get -y upgrade \
    && apt-get install -y git awscli \
    --no-install-recommends && apt-get -y clean \
    && rm -rf /var/lib/apt/lists/*
# Set environment variables for configuration
WORKDIR /project
RUN echo ls
COPY stocks .
COPY .git .git
RUN pip install duckdb requests
ENV PATH="/project/.venv/bin:$PATH"
ENV DOCKER=true
RUN git config --global --add safe.directory /project/opt/local && git ls-files

WORKDIR /project/opt/local
RUN addgroup --system app && adduser --system --group app
CMD ["/bin/bash"]
