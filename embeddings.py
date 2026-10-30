import re
import numpy as np
from sentence_transformers import SentenceTransformer
from pdf_processor import split_text_into_chunks

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
_model = None


STOP_WORDS = {
    "a",
    "an",
    "the",
    "is",
    "are",
    "was",
    "were",
    "what",
    "which",
    "who",
    "where",
    "when",
    "why",
    "how",
    "does",
    "do",
    "did",
    "explain",
    "describe",
    "define",
    "tell",
    "me",
    "about",
    "in",
    "on",
    "at",
    "to",
    "for",
    "of",
    "and",
    "or",
    "with",
    "by",
    "from",
    "it",
    "its",
    "this",
    "that",
    "be",
    "can",
    "could",
    "would",
    "should",
    "please",
    "give",
    "write",
    "short",
    "note",
    "notes",
    "list",
    "mention",
    "state",
    "discuss",
    "types",
    "type",
}


def get_embedding_model():
    global _model

    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)

    return _model


def create_embeddings(texts):
    if not texts:
        return np.empty((0, 384), dtype=np.float32)

    model = get_embedding_model()

    embeddings = model.encode(
        list(texts),
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    return np.asarray(embeddings, dtype=np.float32)


def prepare_document(pdf_text, chunk_size=800, overlap=150):
    if not pdf_text or not pdf_text.strip():
        raise ValueError("PDF text is empty. Upload a readable PDF.")

    chunks = split_text_into_chunks(pdf_text, chunk_size=chunk_size, overlap=overlap)

    chunks = [
        re.sub(r"\s+", " ", chunk).strip()
        for chunk in chunks
        if chunk and chunk.strip()
    ]

    if not chunks:
        raise ValueError("No readable text was found in the PDF.")

    embeddings = create_embeddings(chunks)

    return {"chunks": chunks, "embeddings": embeddings}


def get_keywords(text):
    words = re.findall(r"[a-zA-Z0-9]+", (text or "").lower())

    return {word for word in words if len(word) > 1 and word not in STOP_WORDS}


def search_relevant_chunks(question, chunks, chunk_embeddings, top_k=5):
    if not question or not question.strip():
        return []

    if not chunks or top_k <= 0:
        return []

    chunk_embeddings = np.asarray(chunk_embeddings, dtype=np.float32)

    if chunk_embeddings.ndim != 2 or chunk_embeddings.shape[0] != len(chunks):
        raise ValueError("Chunks and embeddings do not match.")

    question_embedding = create_embeddings([question])[0]
    semantic_scores = np.dot(chunk_embeddings, question_embedding)

    question_keywords = get_keywords(question)
    question_lower = question.lower()
    results = []

    for index, chunk in enumerate(chunks):
        chunk_keywords = get_keywords(chunk)
        matched = question_keywords.intersection(chunk_keywords)

        keyword_score = (
            len(matched) / len(question_keywords) if question_keywords else 0.0
        )

        semantic_score = float(semantic_scores[index])

        score = 0.65 * semantic_score + 0.35 * keyword_score

        if question_lower in chunk.lower():
            score += 0.15

        results.append(
            {
                "text": chunk,
                "score": score,
                "semantic_score": semantic_score,
                "keyword_score": keyword_score,
                "chunk_index": index,
            }
        )

    results.sort(key=lambda item: item["score"], reverse=True)

    selected_indices = []

    for result in results:
        index = result["chunk_index"]

        for nearby in (index - 1, index, index + 1):
            if 0 <= nearby < len(chunks) and nearby not in selected_indices:
                selected_indices.append(nearby)

        if len(selected_indices) >= top_k + 2:
            break

    selected_indices.sort()

    return [
        {
            "text": chunks[index],
            "chunk_index": index,
            "score": float(semantic_scores[index]),
        }
        for index in selected_indices
    ]


def retrieve_context(question, document_data, top_k=5):
    if not document_data:
        return ""

    chunks = document_data.get("chunks", [])
    embeddings = document_data.get("embeddings")

    if embeddings is None or not chunks:
        return ""

    results = search_relevant_chunks(question, chunks, embeddings, top_k=top_k)

    context_parts = []
    seen = set()

    for result in results:
        text = result["text"].strip()

        if text and text not in seen:
            context_parts.append(text)
            seen.add(text)

    return "\n\n".join(context_parts)


def clear_model_cache():
    global _model
    _model = None
