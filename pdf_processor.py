import re
import fitz


def clean_pdf_page_text(page_text):
    if not page_text:
        return ""

    clean_lines = []

    for line in page_text.splitlines():
        line = line.strip()

        if not line:
            continue

        if re.fullmatch(r"Page\s+\d+", line, re.I):
            continue

        if re.search(r"503\s*[-–—]?\s*NETWORK\s+TECHNOLOGY", line, re.I):
            continue

        if re.fullmatch(r"Introduction\s+to\s+Networks?", line, re.I):
            continue

        clean_lines.append(line)

    return "\n".join(clean_lines).strip()


def extract_pdf_text(uploaded_file):
    if uploaded_file is None:
        raise ValueError("Please upload a PDF file.")

    if not uploaded_file.name.lower().endswith(".pdf"):
        raise ValueError("Only PDF files are supported.")

    pdf_bytes = uploaded_file.getvalue()

    if not pdf_bytes:
        raise ValueError("The uploaded PDF is empty.")

    try:
        pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as error:
        raise ValueError("Invalid PDF file. Please upload a valid PDF.") from error

    extracted_pages = []

    try:
        if pdf_document.page_count == 0:
            raise ValueError("The PDF contains no pages.")

        for page_number, page in enumerate(pdf_document, start=1):
            page_text = page.get_text("text", sort=True)
            page_text = clean_pdf_page_text(page_text)

            if page_text:
                extracted_pages.append(f"[Page {page_number}]\n{page_text}")

    finally:
        pdf_document.close()

    full_text = "\n\n".join(extracted_pages).strip()

    if not full_text:
        raise ValueError(
            "Readable text was not found. "
            "This may be a scanned PDF that requires OCR."
        )

    return full_text


def get_pdf_info(uploaded_file):
    if uploaded_file is None:
        raise ValueError("Please upload a PDF file.")

    pdf_bytes = uploaded_file.getvalue()

    if not pdf_bytes:
        raise ValueError("The PDF file is empty.")

    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as pdf_document:
            return {
                "file_name": uploaded_file.name,
                "file_size_kb": round(len(pdf_bytes) / 1024, 2),
                "total_pages": pdf_document.page_count,
            }

    except Exception as error:
        raise ValueError("Could not read PDF information.") from error


def split_text_into_chunks(text, chunk_size=1000, overlap=150):
    if not text or not text.strip():
        return []

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero.")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be non-negative and smaller " "than chunk_size.")

    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + chunk_size, text_length)

        if end < text_length:
            paragraph_boundary = text.rfind("\n\n", start, end)

            if paragraph_boundary > start + chunk_size // 2:
                end = paragraph_boundary
            else:
                sentence_boundary = max(
                    text.rfind(". ", start, end),
                    text.rfind("? ", start, end),
                    text.rfind("! ", start, end),
                )

                if sentence_boundary > start + chunk_size // 2:
                    end = sentence_boundary + 1
                else:
                    word_boundary = text.rfind(" ", start, end)

                    if word_boundary > start:
                        end = word_boundary

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= text_length:
            break

        start = max(end - overlap, start + 1)

    return chunks
