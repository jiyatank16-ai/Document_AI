
import streamlit as st
import os
from datetime import datetime

from pdf_processor import extract_pdf_text
from chatbot import generate_summary, generate_mcqs, answer_question
from database import init_db, save_chat, get_chat_history

# --------------------------------------------------
# DOCUMIND AI - MAIN APPLICATION
# --------------------------------------------------

st.set_page_config(
    page_title="DocuMind AI",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --------------------------------------------------
# CUSTOM CSS
# --------------------------------------------------

st.markdown("""
<style>
    .stApp {
        background-color: #F5F7FB;
        color: #172033;
    }

    [data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid #E5E7EB;
    }

    .main-title {
        font-size: 38px;
        font-weight: 800;
        color: #172554;
        margin-bottom: 0;
    }

    .subtitle {
        color: #64748B;
        font-size: 16px;
        margin-bottom: 24px;
    }

    .hero-card {
        background: linear-gradient(120deg, #E0EAFF, #F0E7FF);
        padding: 26px;
        border-radius: 18px;
        border: 1px solid #D8DFFF;
        margin-bottom: 22px;
    }

    .hero-card h2 {
        color: #172554;
        margin-bottom: 8px;
    }

    .hero-card p {
        color: #475569;
        font-size: 16px;
    }

    .info-card {
        background: #FFFFFF;
        padding: 20px;
        border-radius: 15px;
        border: 1px solid #E2E8F0;
        min-height: 135px;
    }

    .info-card h3 {
        color: #1E3A8A;
        font-size: 19px;
    }

    .info-card p {
        color: #64748B;
        font-size: 14px;
    }

    .stButton > button {
        border-radius: 10px;
        font-weight: 600;
        min-height: 42px;
    }

    [data-testid="stMetric"] {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        padding: 16px;
        border-radius: 12px;
    }

    .footer {
        text-align: center;
        color: #64748B;
        padding: 20px 0;
        font-size: 13px;
    }
</style>
""", unsafe_allow_html=True)


# --------------------------------------------------
# INITIALIZATION
# --------------------------------------------------

init_db()

if "page" not in st.session_state:
    st.session_state.page = "Home"

if "pdf_text" not in st.session_state:
    st.session_state.pdf_text = ""

if "pdf_name" not in st.session_state:
    st.session_state.pdf_name = ""

if "messages" not in st.session_state:
    st.session_state.messages = []

if "summary" not in st.session_state:
    st.session_state.summary = ""

if "mcqs" not in st.session_state:
    st.session_state.mcqs = None


# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def set_page(page_name):
    st.session_state.page = page_name


def load_pdf(uploaded_file):
    """Extract text from an uploaded PDF."""
    try:
        text = extract_pdf_text(uploaded_file)

        if not text or not text.strip():
            st.error(
                "PDF mathi text extract thayu nathi. "
                "PDF scanned image hoy to OCR ni jarur padi shake."
            )
            return

        st.session_state.pdf_text = text
        st.session_state.pdf_name = uploaded_file.name
        st.session_state.messages = []
        st.session_state.summary = ""
        st.session_state.mcqs = None

        st.success(f"PDF successfully loaded: {uploaded_file.name}")

    except Exception as e:
        st.error(f"PDF read karta error aavyo: {e}")


def require_pdf():
    if not st.session_state.pdf_text.strip():
        st.warning("Pehla PDF upload karo.")
        return False
    return True


# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

with st.sidebar:
    st.markdown("## 📚 DocuMind AI")
    st.caption("Your intelligent document assistant")

    st.divider()

    pages = [
        "Home",
        "AI Chat",
        "PDF Summary",
        "MCQ Generator",
        "Chat History",
        "About"
    ]

    for page_name in pages:
        if st.button(
            page_name,
            key=f"nav_{page_name}",
            use_container_width=True,
            type=(
                "primary"
                if st.session_state.page == page_name
                else "secondary"
            )
        ):
            set_page(page_name)

    st.divider()

    st.markdown("### 📄 Current Document")

    if st.session_state.pdf_name:
        st.success(st.session_state.pdf_name)
        st.caption(
            f"{len(st.session_state.pdf_text.split())} words extracted"
        )
    else:
        st.info("No PDF uploaded yet.")

    uploaded_file = st.file_uploader(
        "Upload your PDF",
        type=["pdf"],
        key="sidebar_pdf_upload"
    )

    if uploaded_file is not None:
        if st.button(
            "Process PDF",
            key="process_pdf",
            use_container_width=True
        ):
            load_pdf(uploaded_file)

    if st.button(
        "Clear Current Document",
        use_container_width=True
    ):
        st.session_state.pdf_text = ""
        st.session_state.pdf_name = ""
        st.session_state.messages = []
        st.session_state.summary = ""
        st.session_state.mcqs = None
        st.rerun()


# --------------------------------------------------
# HOME PAGE
# --------------------------------------------------

if st.session_state.page == "Home":

    st.markdown(
        '<div class="main-title">DocuMind AI</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="subtitle">'
        'Read smarter. Learn faster. Ask your documents.'
        '</div>',
        unsafe_allow_html=True
    )

    st.markdown("""
    <div class="hero-card">
        <h2>Welcome to your AI Document Assistant 👋</h2>
        <p>
            Upload your PDF notes, study material or documents.
            Ask questions, generate summaries and create practice MCQs
            from your document.
        </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        <div class="info-card">
            <h3>💬 AI Chat</h3>
            <p>Ask questions about your uploaded document.</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="info-card">
            <h3>📝 Smart Summary</h3>
            <p>Turn lengthy documents into easy-to-read summaries.</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div class="info-card">
            <h3>🎯 MCQ Generator</h3>
            <p>Create practice questions from your study material.</p>
        </div>
        """, unsafe_allow_html=True)

    st.write("")

    st.subheader("🚀 Get Started")

    if not st.session_state.pdf_text:
        st.info(
            "Step 1: Sidebar ma PDF upload karo. "
            "Step 2: Process PDF par click karo. "
            "Step 3: AI Chat, Summary athva MCQ Generator open karo."
        )
    else:
        st.success(f"Ready to explore: {st.session_state.pdf_name}")

        if st.button(
            "Start Asking Questions →",
            type="primary"
        ):
            set_page("AI Chat")
            st.rerun()

    st.markdown(
        '<div class="footer">DocuMind AI | Intelligent PDF Assistant</div>',
        unsafe_allow_html=True
    )


# --------------------------------------------------
# AI CHAT PAGE
# --------------------------------------------------

elif st.session_state.page == "AI Chat":

    st.title("💬 AI Document Chat")
    st.caption("Ask questions based on your uploaded PDF.")

    if require_pdf():

        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        prompt = st.chat_input(
            "Ask something about your PDF..."
        )

        if prompt:
            st.session_state.messages.append(
                {"role": "user", "content": prompt}
            )

            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Finding your answer..."):
                    try:
                        answer = answer_question(
                            st.session_state.pdf_text,
                            prompt
                        )

                        st.markdown(answer)

                        st.session_state.messages.append(
                            {
                                "role": "assistant",
                                "content": answer
                            }
                        )

                        save_chat(
                            st.session_state.pdf_name,
                            prompt,
                            answer
                        )

                    except Exception as e:
                        st.error(f"Answer generate karta error: {e}")

            st.rerun()


# --------------------------------------------------
# PDF SUMMARY PAGE
# --------------------------------------------------

elif st.session_state.page == "PDF Summary":

    st.title("📝 PDF Summary")
    st.caption("Generate a concise summary from your document.")

    if require_pdf():

        st.write(f"**Document:** {st.session_state.pdf_name}")

        summary_length = st.selectbox(
            "Choose summary length",
            ["Short", "Medium", "Detailed"]
        )

        if st.button(
            "Generate Summary",
            type="primary"
        ):
            with st.spinner("Generating summary..."):
                try:
                    st.session_state.summary = generate_summary(
                        st.session_state.pdf_text,
                        summary_length
                    )
                except Exception as e:
                    st.error(f"Summary generate karta error: {e}")

        if st.session_state.summary:
            st.subheader("Your Summary")
            st.markdown(st.session_state.summary)

            st.download_button(
                "Download Summary",
                data=st.session_state.summary,
                file_name="documind_summary.txt",
                mime="text/plain"
            )


# --------------------------------------------------
# MCQ GENERATOR PAGE
# --------------------------------------------------

elif st.session_state.page == "MCQ Generator":

    st.title("🎯 MCQ Generator")
    st.caption("Create practice questions from your PDF.")

    if require_pdf():

        number_of_questions = st.slider(
            "Number of questions",
            min_value=3,
            max_value=15,
            value=5
        )

        if st.button(
            "Generate MCQs",
            type="primary"
        ):
            with st.spinner("Creating practice questions..."):
                try:
                    st.session_state.mcqs = generate_mcqs(
                        st.session_state.pdf_text,
                        number_of_questions
                    )
                except Exception as e:
                    st.error(f"MCQ generate karta error: {e}")

        if st.session_state.mcqs:

            st.subheader("Practice Questions")

            for index, question in enumerate(
                st.session_state.mcqs
            ):
                if isinstance(question, dict):
                    st.markdown(
                        f"**Q{index + 1}. {question.get('question', '')}**"
                    )

                    options = question.get("options", [])

                    if options:
                        st.radio(
                            "Select your answer",
                            options,
                            key=f"mcq_answer_{index}"
                        )

                    with st.expander("Show Answer"):
                        st.write(
                            question.get(
                                "answer",
                                "Answer not available"
                            )
                        )
                        explanation = question.get("explanation", "")
                        if explanation:
                            st.caption(explanation)

                    st.divider()

                else:
                    st.write(question)

            st.download_button(
                "Download MCQs",
                data=str(st.session_state.mcqs),
                file_name="documind_mcqs.txt",
                mime="text/plain"
            )


# --------------------------------------------------
# CHAT HISTORY PAGE
# --------------------------------------------------

elif st.session_state.page == "Chat History":

    st.title("🕘 Chat History")
    st.caption("Review your previous document questions and answers.")

    try:
        history = get_chat_history()

        if history:
            for item in history:
                with st.expander(
                    f"📄 {item.get('pdf_name', 'Document')} — "
                    f"{item.get('timestamp', '')}"
                ):
                    st.markdown("**Question:**")
                    st.write(item.get("question", ""))

                    st.markdown("**Answer:**")
                    st.write(item.get("answer", ""))
        else:
            st.info("No chat history available yet.")

    except Exception as e:
        st.error(f"History load karta error: {e}")


# --------------------------------------------------
# ABOUT PAGE
# --------------------------------------------------

elif st.session_state.page == "About":

    st.title("ℹ️ About DocuMind AI")

    st.markdown("""
    **DocuMind AI** is a Python and Streamlit-based document assistant.

    ### Main Features
    - PDF upload and text extraction
    - Document question answering
    - Automatic summarization
    - Practice MCQ generation
    - Chat history storage

    ### Technology Stack
    - Python
    - Streamlit
    - PDF text extraction
    - AI / NLP
    - SQLite database

    This application is designed for learning and educational use.
    """)
