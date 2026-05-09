FROM public.ecr.aws/lambda/python:3.11

WORKDIR ${LAMBDA_TASK_ROOT}

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./

# Export lockfile to requirements.txt, then install CPU-only torch separately
# to avoid pulling the ~2GB CUDA build that uv would select by default.
RUN uv export --frozen --no-dev --no-emit-project -o /tmp/requirements.txt && \
    grep -v "^torch==" /tmp/requirements.txt > /tmp/requirements-notorch.txt

RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r /tmp/requirements-notorch.txt

# Bake the reranker model into the image so cold starts don't hit the network.
RUN python -c "from sentence_transformers import CrossEncoder; CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')"

COPY . .

CMD ["api.lambda_handler.handler"]
