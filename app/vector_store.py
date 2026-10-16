from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

from .config import settings


Path(settings.vector_db_dir).mkdir(
    parents=True,
    exist_ok=True
)


chroma_client = chromadb.PersistentClient(
    path=settings.vector_db_dir
)


embedding_model = SentenceTransformer(
    settings.embedding_model
)


policy_collection = chroma_client.get_or_create_collection(
    name="claimiq_policy_chunks",
    metadata={
        "hnsw:space": "cosine"
    }
)


claim_collection = chroma_client.get_or_create_collection(
    name="claimiq_claim_chunks",
    metadata={
        "hnsw:space": "cosine"
    }
)


def generate_embeddings(
    chunks: list[str]
) -> list[list[float]]:
    embeddings = embedding_model.encode(
        chunks,
        normalize_embeddings=True
    )

    return embeddings.tolist()


def delete_policy_document_vectors(
    document_id: int
) -> None:
    policy_collection.delete(
        where={
            "document_id": document_id
        }
    )


def delete_claim_document_vectors(
    document_id: int
) -> None:
    claim_collection.delete(
        where={
            "document_id": document_id
        }
    )


def index_policy_chunks(
    document_id: int,
    policy_id: int,
    filename: str,
    chunks: list[str]
) -> int:
    delete_policy_document_vectors(
        document_id
    )

    embeddings = generate_embeddings(
        chunks
    )

    vector_ids = []
    metadatas = []

    for index in range(len(chunks)):
        vector_ids.append(
            f"policy-{document_id}-chunk-{index}"
        )

        metadatas.append(
            {
                "document_type": "policy",
                "document_id": document_id,
                "policy_id": policy_id,
                "filename": filename,
                "chunk_number": index
            }
        )

    policy_collection.add(
        ids=vector_ids,
        documents=chunks,
        embeddings=embeddings,
        metadatas=metadatas
    )

    return len(chunks)


def index_claim_chunks(
    document_id: int,
    claim_id: int,
    filename: str,
    chunks: list[str]
) -> int:
    delete_claim_document_vectors(
        document_id
    )

    embeddings = generate_embeddings(
        chunks
    )

    vector_ids = []
    metadatas = []

    for index in range(len(chunks)):
        vector_ids.append(
            f"claim-{document_id}-chunk-{index}"
        )

        metadatas.append(
            {
                "document_type": "claim",
                "document_id": document_id,
                "claim_id": claim_id,
                "filename": filename,
                "chunk_number": index
            }
        )

    claim_collection.add(
        ids=vector_ids,
        documents=chunks,
        embeddings=embeddings,
        metadatas=metadatas
    )

    return len(chunks)


def search_policy_chunks(
    question: str,
    policy_id: int | None = None
) -> list[dict]:
    query_embedding = generate_embeddings(
        [question]
    )[0]

    query_args = {
        "query_embeddings": [
            query_embedding
        ],
        "n_results": settings.retrieval_top_k,
        "include": [
            "documents",
            "metadatas",
            "distances"
        ]
    }

    if policy_id is not None:
        query_args["where"] = {
            "policy_id": policy_id
        }

    results = policy_collection.query(
        **query_args
    )

    documents = (
        results.get("documents")
        or [[]]
    )[0]

    metadatas = (
        results.get("metadatas")
        or [[]]
    )[0]

    distances = (
        results.get("distances")
        or [[]]
    )[0]

    matches = []

    for document, metadata, distance in zip(
        documents,
        metadatas,
        distances
    ):
        matches.append(
            {
                "text": document,
                "metadata": metadata,
                "distance": float(distance)
            }
        )

    return matches