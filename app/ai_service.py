from fastapi import HTTPException
from openai import AzureOpenAI

from .config import settings


def azure_openai_configured() -> bool:
    return all(
        [
            settings.azure_openai_endpoint,
            settings.azure_openai_api_key,
            settings.azure_openai_chat_deployment,
        ]
    )


def get_azure_client():
    if not azure_openai_configured():
        raise HTTPException(
            status_code=503,
            detail=(
                "Azure OpenAI is not configured. "
                "Set the Azure OpenAI values in .env."
            ),
        )

    return AzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
    )


def build_context(matches: list[dict]) -> str:
    context_parts = []

    for index, match in enumerate(
        matches,
        start=1
    ):
        metadata = match["metadata"]

        filename = metadata.get(
            "filename",
            "unknown"
        )

        chunk_number = metadata.get(
            "chunk_number",
            0
        )

        context_parts.append(
            (
                f"[Source {index}]\n"
                f"File: {filename}\n"
                f"Chunk: {chunk_number}\n"
                f"{match['text']}"
            )
        )

    return "\n\n".join(context_parts)


def generate_rag_answer(
    question: str,
    matches: list[dict]
) -> str:
    if not matches:
        return (
            "I could not find relevant information "
            "in the indexed ClaimIQ policy documents."
        )

    client = get_azure_client()

    context = build_context(
        matches
    )

    system_prompt = (
        "You are ClaimIQ, an insurance policy "
        "knowledge assistant. "
        "Answer only from the supplied policy context. "
        "Do not invent policy provisions. "
        "If the supplied context is insufficient, "
        "state that the answer cannot be determined "
        "from the available documents. "
        "Reference the supplied source numbers when "
        "answering."
    )

    user_prompt = (
        f"Policy context:\n\n{context}\n\n"
        f"Question:\n{question}"
    )

    response = client.chat.completions.create(
        model=settings.azure_openai_chat_deployment,
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
    )

    answer = response.choices[0].message.content

    return answer or (
        "No answer was generated."
    )