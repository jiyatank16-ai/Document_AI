import re
import random
import streamlit as st
import torch

from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from embeddings import create_embeddings
from pdf_processor import split_text_into_chunks

# =====================================================
# DOCUMIND AI CONFIGURATION
# =====================================================

MODEL_NAME = "google/flan-t5-base"


# =====================================================
# LOAD MODEL
# =====================================================


@st.cache_resource
def get_model():

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME)

    model.to("cpu")
    model.eval()

    return tokenizer, model


def generate_text(prompt, max_new_tokens=180):

    tokenizer, model = get_model()

    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)

    with torch.inference_mode():

        output = model.generate(
            **inputs, max_new_tokens=max_new_tokens, num_beams=4, do_sample=False
        )

    return tokenizer.decode(output[0], skip_special_tokens=True).strip()


# =====================================================
# TEXT PROCESSING
# =====================================================


def normalize_text(text):

    text = str(text or "")

    text = re.sub(r"\s+", " ", text)

    return text.strip()


def split_sentences(text):

    text = normalize_text(text)

    sentences = re.split(r"(?<=[.!?])\s+", text)

    return [sentence.strip() for sentence in sentences if len(sentence.strip()) > 25]


# =====================================================
# DOCUMENT CHUNKS
# =====================================================


@st.cache_data(show_spinner=False)
def get_document_chunks(pdf_text):

    return split_text_into_chunks(pdf_text, chunk_size=800, overlap=120)


# =====================================================
# QUESTION KEYWORDS
# =====================================================


def question_keywords(question):

    stop_words = {
        "what",
        "is",
        "are",
        "the",
        "a",
        "an",
        "of",
        "in",
        "on",
        "to",
        "for",
        "and",
        "explain",
        "define",
        "describe",
        "how",
        "why",
        "which",
        "with",
        "from",
        "does",
    }

    words = re.findall(r"[a-zA-Z0-9]+", question.lower())

    return [word for word in words if word not in stop_words and len(word) > 2]


# =====================================================
# RETRIEVE CONTEXT
# =====================================================


def retrieve_context(pdf_text, question):

    chunks = get_document_chunks(pdf_text)

    if not chunks:
        return ""

    keywords = question_keywords(question)

    scored_chunks = []

    for chunk in chunks:

        lower_chunk = chunk.lower()

        score = sum(2 for word in keywords if word in lower_chunk)

        if score > 0:
            scored_chunks.append((score, chunk))

    scored_chunks.sort(key=lambda item: item[0], reverse=True)

    if scored_chunks:

        return "\n".join(chunk for score, chunk in scored_chunks[:3])

    return "\n".join(chunks[:2])


# =====================================================
# DIRECT ANSWER
# =====================================================


def direct_answer(context, question):

    sentences = split_sentences(context)

    keywords = question_keywords(question)

    scored = []

    for sentence in sentences:

        lower_sentence = sentence.lower()

        score = sum(1 for word in keywords if word in lower_sentence)

        if score > 0:
            scored.append((score, sentence))

    scored.sort(key=lambda item: item[0], reverse=True)

    if scored:

        return " ".join(sentence for score, sentence in scored[:3])

    return ""


# =====================================================
# PDF QUESTION ANSWERING
# =====================================================


def answer_question(pdf_text, question):

    if not pdf_text:
        return "Please upload a PDF first."

    if not question.strip():
        return "Please enter your question."

    context = retrieve_context(pdf_text, question)

    if not context:
        return "No readable text found in the PDF."

    prompt = f"""
Answer using only the document context.

If the answer is not available, say:
The answer is not available in the uploaded PDF.

Context:
{context[:1800]}

Question:
{question}

Answer:
"""

    try:

        answer = generate_text(prompt, max_new_tokens=180)

        if answer:
            return answer

    except Exception:
        pass

    fallback = direct_answer(context, question)

    if fallback:
        return fallback

    return "The answer is not available in the uploaded PDF."


# =====================================================
# SUMMARY GENERATOR
# =====================================================


def generate_summary(pdf_text, summary_length="Medium"):

    if not pdf_text:
        return "No PDF text available."

    settings = {"Short": (100, 1500), "Medium": (180, 2500), "Long": (300, 3500)}

    max_tokens, context_limit = settings.get(summary_length, settings["Medium"])

    prompt = f"""
Summarize this document in simple English.
Include important points.
Do not add outside information.

Document:
{pdf_text[:context_limit]}

Summary:
"""

    try:

        summary = generate_text(prompt, max_new_tokens=max_tokens)

        if summary:
            return summary

    except Exception:
        pass

    sentences = split_sentences(pdf_text)

    return " ".join(sentences[:8])


# =====================================================
# MCQ GENERATOR HELPERS
# =====================================================


def clean_candidate(text):

    text = normalize_text(text)

    text = re.sub(r"^[\-\*\d\.\)\s]+", "", text)

    return text.strip(" .,:;-")


def extract_candidates(pdf_text):

    candidates = []

    sentences = split_sentences(pdf_text)

    patterns = [
        r"\b(?:is|are|means|called|known as)\s+([^,.!?;]{3,65})",
        r"\b(?:consists of|includes|contains)\s+([^,.!?;]{3,65})",
        r"\b(?:such as|for example)\s+([^.!?]{3,65})",
    ]

    for sentence in sentences:

        for pattern in patterns:

            matches = re.findall(pattern, sentence, flags=re.IGNORECASE)

            for match in matches:

                candidate = clean_candidate(match)

                if 3 <= len(candidate) <= 65 and len(candidate.split()) <= 9:

                    candidates.append(candidate)

    # Collect technical terms and capitalized words
    words = re.findall(r"\b[A-Z][a-zA-Z0-9-]{2,25}\b", pdf_text)

    candidates.extend(words)

    unique_candidates = []
    seen = set()

    for candidate in candidates:

        key = candidate.lower()

        if key not in seen:

            seen.add(key)
            unique_candidates.append(candidate)

    return unique_candidates


# =====================================================
# CREATE MCQ QUESTION
# =====================================================


def make_question_from_sentence(sentence, answer):

    pattern = re.compile(re.escape(answer), flags=re.IGNORECASE)

    if not pattern.search(sentence):
        return None

    question_text = pattern.sub("________", sentence, count=1)

    if len(question_text) < 20:
        return None

    return "Complete the sentence: " + question_text


# =====================================================
# GENERATE MCQS
# =====================================================


def generate_mcqs(pdf_text, number_of_questions=5):

    if not pdf_text or not pdf_text.strip():
        return []

    try:
        number_of_questions = int(number_of_questions)
    except (TypeError, ValueError):
        number_of_questions = 5

    number_of_questions = max(1, min(number_of_questions, 20))

    sentences = split_sentences(pdf_text)

    candidates = extract_candidates(pdf_text)

    if len(candidates) < 4:
        return []

    mcqs = []
    used_questions = set()

    rng = random.Random()

    for answer in candidates:

        if len(mcqs) >= number_of_questions:
            break

        matching_sentence = None

        for sentence in sentences:

            if re.search(re.escape(answer), sentence, flags=re.IGNORECASE):

                matching_sentence = sentence
                break

        if not matching_sentence:
            continue

        question = make_question_from_sentence(matching_sentence, answer)

        if not question:
            continue

        if question.lower() in used_questions:
            continue

        distractors = [
            candidate
            for candidate in candidates
            if candidate.lower() != answer.lower()
            and candidate.lower() not in question.lower()
        ]

        if len(distractors) < 3:
            continue

        rng.shuffle(distractors)

        options = distractors[:3] + [answer]

        rng.shuffle(options)

        mcqs.append(
            {
                "question": question,
                "options": options,
                "answer": answer,
                "correct_answer": answer,
                "explanation": matching_sentence,
            }
        )

        used_questions.add(question.lower())

    return mcqs


# =====================================================
# CLEAR CACHE
# =====================================================


def clear_chatbot_cache():

    get_model.clear()
    get_document_chunks.clear()
