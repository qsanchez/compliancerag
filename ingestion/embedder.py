import litellm

from config import get_settings

_BATCH_SIZE = 10


def embed(texts: list[str]) -> list[list[float]]:
    settings = get_settings()
    model = settings.litellm_embedding_model
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), _BATCH_SIZE):
        batch = texts[i : i + _BATCH_SIZE]
        response = litellm.embedding(model=model, input=batch)
        all_embeddings.extend(item["embedding"] for item in response.data)

    return all_embeddings
