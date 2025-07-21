# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import asyncio
import atexit
import timeit
import warnings

import streamlit as st

from src.ragme import RagMe

# Suppress Pydantic deprecation and schema warnings from dependencies
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*PydanticDeprecatedSince211.*")
warnings.filterwarnings("ignore", category=UserWarning, message=".*PydanticJsonSchemaWarning.*")
warnings.filterwarnings("ignore", message=".*model_fields.*")
warnings.filterwarnings("ignore", message=".*not JSON serializable.*")

# Suppress ResourceWarnings from dependencies
warnings.filterwarnings("ignore", category=ResourceWarning, message=".*unclosed.*")
warnings.filterwarnings("ignore", category=ResourceWarning, message=".*Enable tracemalloc.*")

# Initialize RagMe
ragme = RagMe()

# Cleanup function
def cleanup():
    """Clean up resources when the application shuts down."""
    try:
        if ragme:
            ragme.cleanup()
    except Exception as e:
        st.error(f"Error during cleanup: {e}")

# Register cleanup handlers
atexit.register(cleanup)

# Set page configuration
st.set_page_config(
    page_title="RAGme Assistant",
    page_icon="🤖",
    layout="centered"
)

# Initialize session state for chat history
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Welcome to the RAGme.ai Assistant! I can help you RAG web pages and answer questions about them. How can I help you today?"}
    ]

# Page header
st.title("🤖 RAGme.ai Assistant")
st.markdown("Search and create reports through the collection of web pages (crawled or added manually)")

# Display chat messages
for message in st.session_state.messages:
    if message["role"] == "assistant":
        with st.chat_message(message["role"], avatar="🤖"):
            st.markdown(message["content"])
    else:
        with st.chat_message(message["role"], avatar="👤"):
            st.markdown(message["content"])

# Function to process user input
async def process_query(query):
    try:
        result = await ragme.run(query)
        return result
    except Exception as e:
        return f"An error occurred: {str(e)}"

# Chat input
if prompt := st.chat_input("Tell me web pages to RAG or ask me questions about previously RAGged pages"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)
    
    # Display assistant response
    with st.chat_message("assistant", avatar="🤖"):
        message_placeholder = st.empty()
        message_placeholder.markdown(f"Thinking... will take about 5-10 seconds")
        
        # Process the query
        time_start = timeit.default_timer()
        
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            response = loop.run_until_complete(process_query(prompt))
        finally:
            loop.close()
                
        # Update the placeholder with the response        
        message_placeholder.markdown(response)
    
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response}) 