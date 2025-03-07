"""Streamlit frontend for AskTheDocs app."""
import requests
import streamlit as st


def main():
    """Run streamlit app main entrypoint."""
    st.title("AskTheDocs 🦆")

    # ---------------------------------------------------
    # Section 1: PDF File Upload & Document Ingestion
    # ---------------------------------------------------
    st.header("Upload PDF Files")

    # Let the user upload multiple PDF files:
    uploaded_files = st.file_uploader("Select PDF files", type="pdf", accept_multiple_files=True)
    current_file_names = [f.name for f in uploaded_files] if uploaded_files else []

    # We need to compare with the previous file list in session state.
    if "uploaded_file_names" not in st.session_state:
        st.session_state.uploaded_file_names = []

    # If the file list changed, we do the ingestion flow:
    if current_file_names != st.session_state.uploaded_file_names:
        with st.spinner("Updating documents database... Please wait ⏳"):
            # 1. Clean up database
            delete_url = "http://fastapi-backend:8000/v1/delete_all_chunks"
            try:
                delete_response = requests.delete(delete_url)
                delete_response.raise_for_status()  # Raise an error for non-2xx codes
            except requests.exceptions.RequestException as e:
                st.error(f"Error deleting all chunks: {e}")

            # 2. Ingest documents in database
            ingest_url = "http://fastapi-backend:8000/v1/ingest_document"
            try:
                for file_obj in uploaded_files:
                    # Note: file_obj is a Streamlit UploadedFile, not a local path
                    # but we can still pass its `read()` content to requests.
                    files = {"file": (file_obj.name, file_obj.getvalue(), "application/pdf")}
                    response = requests.post(ingest_url, files=files)
                    response.raise_for_status()
            except requests.exceptions.RequestException as e:
                st.error(f"Error ingesting {file_obj.name}: {e}")

        st.success(f"Successfully uploaded {len(uploaded_files)} files to database ✅")

        # Update session_state
        st.session_state.uploaded_file_names = current_file_names

        # Re-initialize the chat with a welcome message
        intro_message = (
            "Hello and welcome to AskTheDocs! 👋 \n"
            "You have uploaded these files:\n"
            + "".join(f"  • {name}\n" for name in current_file_names)
            + "Which question do you want to ask?"
        )
        st.session_state.messages = [{"role": "assistant", "content": intro_message}]

    # Ensure we have a messages list in state
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # ---------------------------------------------------
    # Section 2: ChatBot Interface
    # ---------------------------------------------------
    st.header("ChatBot")

    # Display chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.text(msg["content"])

    # Chat input field
    prompt = st.chat_input("Your question?")
    if prompt:
        # Add user message to session
        st.chat_message("user").text(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Send the query to the backend
        query_url = "http://fastapi-backend:8000/v1/query"
        payload = {"query": prompt, "top_k": 3}

        try:
            query_response = requests.post(query_url, json=payload)
            query_response.raise_for_status()

            response_json = query_response.json()
            # Extract relevant fields
            answer_text = response_json.get("answer_text", "No answer text found.")
            answer_sources = response_json.get("answer_sources", [])
            bot_answer = (
                "✅ ANSWER\n\n"
                + f"{answer_text}\n\n"
                + "ℹ️ SOURCES\n\n"
                + "\n".join(f"ℹ️ {source}" for source in answer_sources)
            )

        except requests.exceptions.RequestException as e:
            bot_answer = (
                f"Error calling the API: {e} --- Sent query: {prompt} ---- URL used: {query_url}"
            )

        # Display the assistant's response
        with st.chat_message("assistant"):
            st.text(bot_answer)

        st.session_state.messages.append({"role": "assistant", "content": bot_answer})


if __name__ == "__main__":
    main()
