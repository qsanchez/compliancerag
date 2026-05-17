FROM public.ecr.aws/lambda/python:3.12

WORKDIR ${LAMBDA_TASK_ROOT}

RUN pip install --no-cache-dir uv

# Build tools: gcc for native extensions, Rust for tiktoken (litellm dep)
RUN dnf install -y gcc gcc-c++ make && \
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal && \
    echo 'source $HOME/.cargo/env' >> /root/.bashrc
ENV PATH="/root/.cargo/bin:${PATH}"

# Install only what the Lambda API needs (not eval/ingestion deps).
# --prefer-binary: use pre-built wheels over source; avoids compiling numpy/matplotlib.
RUN pip install --no-cache-dir --prefer-binary \
    "fastapi>=0.111" \
    "mangum>=0.21" \
    "pydantic-settings>=2.3" \
    "structlog>=24.1" \
    "python-dotenv>=1.0" \
    "litellm>=1.0" \
    "langgraph>=0.2" \
    "psycopg[binary]>=3.1" \
    "pgvector>=0.3" \
    "pyathena>=3.0" \
    "boto3>=1.34" \
    "pyarrow>=17.0" \
    "matplotlib>=3.9" \
    "pillow>=10.0" \
    "httpx>=0.27" \
    "tenacity>=8.3"

COPY . .

CMD ["api.main.handler"]
