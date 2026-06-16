import streamlit as st
import os
import json
from dotenv import load_dotenv

# Import database layer
from db import (
    init_db,
    create_chat,
    get_chats,
    rename_chat,
    delete_chat,
    get_chat_messages,
    add_message,
    get_setting,
    set_setting
)

# Import LLM provider registry
from llm_providers import get_provider, PROVIDERS

# Load environment variables (from .env file if it exists)
load_dotenv()

# Set Streamlit Page Configuration
st.set_page_config(
    page_title="Antigravity Chat",
    page_icon="🌌",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database
try:
    init_db()
except Exception as e:
    st.error("Database connection failed. Check your Supabase database URL in Streamlit Cloud secrets.")
    st.exception(e)
    st.stop()

# Define Custom Premium Styling
def apply_custom_style():
    st.markdown("""
        <style>
        /* Import Google Font */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;600;800&display=swap');
        
        /* Apply Typography */
        html, body, [class*="css"], .stApp {
            font-family: 'Inter', sans-serif;
        }
        
        h1, h2, h3, .title-text {
            font-family: 'Outfit', sans-serif;
            font-weight: 800;
        }
        
        /* Main background */
        .stApp {
            background-color: #0B0F19;
            color: #E2E8F0;
        }
        
        /* Custom sidebar styling */
        section[data-testid="stSidebar"] {
            background-color: #111827;
            border-right: 1px solid #1F2937;
        }
        
        /* Chat list buttons styling */
        div.stButton > button {
            border-radius: 8px;
            font-weight: 500;
            transition: all 0.2s ease-in-out;
        }
        
        /* Primary buttons (New Chat, Send etc.) */
        button[kind="primary"] {
            background: linear-gradient(135deg, #6366F1 0%, #3B82F6 100%) !important;
            border: none !important;
            color: white !important;
            box-shadow: 0 4px 14px 0 rgba(99, 102, 241, 0.4);
        }
        button[kind="primary"]:hover {
            transform: translateY(-1px);
            box-shadow: 0 6px 20px 0 rgba(99, 102, 241, 0.6);
        }
        
        /* Chat bubbles */
        div[data-testid="chatAvatarIcon-user"] {
            background-color: #6366F1 !important;
        }
        div[data-testid="chatAvatarIcon-assistant"] {
            background-color: #10B981 !important;
        }
        
        /* Code block container */
        code {
            color: #38BDF8 !important;
        }
        
        /* Custom Card container for welcome screen */
        .welcome-card {
            background: rgba(30, 41, 59, 0.7);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 16px;
            backdrop-filter: blur(10px);
            transition: border 0.3s ease;
        }
        .welcome-card:hover {
            border-color: rgba(99, 102, 241, 0.5);
        }
        
        /* Settings expander styling */
        .streamlit-expanderHeader {
            background-color: #1F2937 !important;
            border-radius: 8px !important;
            border: 1px solid #374151 !important;
            margin-bottom: 8px;
        }
        </style>
    """, unsafe_allow_html=True)

apply_custom_style()

# --- Initialize Session State Variables ---
if "active_chat_id" not in st.session_state:
    st.session_state.active_chat_id = None
if "rename_chat_id" not in st.session_state:
    st.session_state.rename_chat_id = None
if "error_message" not in st.session_state:
    st.session_state.error_message = None

# Helper to save API key in database settings and environment variables
def save_api_key(provider_name: str, key_val: str):
    db_key = f"api_key_{provider_name}"
    set_setting(db_key, key_val)
    # Also set env var for current session
    os.environ[db_key.upper()] = key_val

# Helper to get API key (checks environment variable first, then SQLite settings)
def load_api_key(provider_name: str) -> str:
    env_name = f"API_KEY_{provider_name.upper()}"
    # 1. Check env vars
    if os.getenv(env_name):
        return os.getenv(env_name)
    # 2. Check settings db
    return get_setting(f"api_key_{provider_name}", "")

# --- SIDEBAR IMPLEMENTATION ---
st.sidebar.markdown(
    "<h1 style='text-align: center; background: linear-gradient(135deg, #6366F1 0%, #10B981 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 2.2rem;'>🌌 Antigravity</h1>", 
    unsafe_allow_html=True
)
st.sidebar.markdown("<p style='text-align: center; color: #9CA3AF; margin-bottom: 20px;'>Premium Python AI Chat Client</p>", unsafe_allow_html=True)

# 1. New Chat Button
if st.sidebar.button("➕ New Chat", use_container_width=True, type="primary"):
    new_id = create_chat(title="New Chat Session")
    st.session_state.active_chat_id = new_id
    st.session_state.rename_chat_id = None
    st.rerun()

st.sidebar.markdown("### Chats")

# Load chats list
chats = get_chats()

# If there's a rename request, show rename input at the top of the chat list
if st.session_state.rename_chat_id:
    current_chat = next((c for c in chats if c["id"] == st.session_state.rename_chat_id), None)
    if current_chat:
        st.sidebar.markdown("---")
        st.sidebar.markdown(f"**Rename:** *{current_chat['title']}*")
        new_title = st.sidebar.text_input("New title name:", value=current_chat["title"])
        col_r1, col_r2 = st.sidebar.columns(2)
        with col_r1:
            if st.button("Save", key="save_rename", use_container_width=True):
                rename_chat(st.session_state.rename_chat_id, new_title)
                st.session_state.rename_chat_id = None
                st.rerun()
        with col_r2:
            if st.button("Cancel", key="cancel_rename", use_container_width=True):
                st.session_state.rename_chat_id = None
                st.rerun()
        st.sidebar.markdown("---")

# Render active chats list
if not chats:
    st.sidebar.info("No chats yet. Click 'New Chat' above.")
else:
    for chat in chats:
        # Highlight active chat
        is_active = (chat["id"] == st.session_state.active_chat_id)
        btn_label = f"💬 {chat['title']}"
        
        # Grid layout for chat options: [Chat Title (70%), Rename (15%), Delete (15%)]
        col_c1, col_c2, col_c3 = st.sidebar.columns([0.7, 0.15, 0.15])
        with col_c1:
            btn_style = "primary" if is_active else "secondary"
            if st.button(btn_label, key=f"chat_select_{chat['id']}", use_container_width=True, type=btn_style):
                st.session_state.active_chat_id = chat["id"]
                st.session_state.rename_chat_id = None
                st.rerun()
        with col_c2:
            if st.button("✏️", key=f"chat_rename_{chat['id']}", help="Rename Chat"):
                st.session_state.rename_chat_id = chat["id"]
                st.rerun()
        with col_c3:
            if st.button("🗑️", key=f"chat_delete_{chat['id']}", help="Delete Chat"):
                delete_chat(chat["id"])
                if st.session_state.active_chat_id == chat["id"]:
                    st.session_state.active_chat_id = None
                st.rerun()

# 2. MODEL SELECTION & API KEYS
st.sidebar.markdown("---")
st.sidebar.markdown("### Settings")

# Model configuration
provider_options = {
    "gemini": "Google Gemini",
    "groq": "Groq",
    "deepseek": "DeepSeek",
    "huggingface": "Hugging Face Inference",
    "custom": "Custom OpenAI Provider"
}

# Select Provider
saved_provider = get_setting("selected_provider", "gemini")
selected_provider_key = st.sidebar.selectbox(
    "AI Provider",
    options=list(provider_options.keys()),
    format_func=lambda x: provider_options[x],
    index=list(provider_options.keys()).index(saved_provider) if saved_provider in provider_options else 0
)
if selected_provider_key != saved_provider:
    set_setting("selected_provider", selected_provider_key)

# Dynamic list of models depending on provider selection
if selected_provider_key == "custom":
    # Custom provider configurations
    custom_name = get_setting("custom_provider_name", "Custom Provider")
    custom_base_url = get_setting("custom_provider_base_url", "https://api.openai.com/v1")
    custom_models_str = get_setting("custom_provider_models", "gpt-4o, gpt-3.5-turbo")
    
    custom_config = {
        "name": custom_name,
        "base_url": custom_base_url,
        "models": custom_models_str
    }
    
    provider_inst = get_provider(selected_provider_key, custom_config)
    model_options = provider_inst.list_default_models()
else:
    provider_inst = get_provider(selected_provider_key)
    model_options = provider_inst.list_default_models()

# Load saved model or default to the first model in the list
saved_model = get_setting("selected_model", model_options[0] if model_options else "")
if saved_model in model_options:
    model_index = model_options.index(saved_model)
else:
    model_index = 0

selected_model = st.sidebar.selectbox(
    "Model Selection",
    options=model_options,
    index=model_index
)
if selected_model != saved_model:
    set_setting("selected_model", selected_model)

# Expanders for API Keys and Custom Settings
with st.sidebar.expander("🔑 API Keys", expanded=False):
    # Gemini
    gemini_key = st.text_input(
        "Google Gemini API Key",
        value=load_api_key("gemini"),
        type="password",
        placeholder="AIzaSy..."
    )
    if gemini_key != load_api_key("gemini"):
        save_api_key("gemini", gemini_key)
        
    # Groq
    groq_key = st.text_input(
        "Groq API Key",
        value=load_api_key("groq"),
        type="password",
        placeholder="gsk_..."
    )
    if groq_key != load_api_key("groq"):
        save_api_key("groq", groq_key)
        
    # DeepSeek
    deepseek_key = st.text_input(
        "DeepSeek API Key",
        value=load_api_key("deepseek"),
        type="password",
        placeholder="sk-..."
    )
    if deepseek_key != load_api_key("deepseek"):
        save_api_key("deepseek", deepseek_key)
        
    # HuggingFace
    hf_key = st.text_input(
        "Hugging Face Token",
        value=load_api_key("huggingface"),
        type="password",
        placeholder="hf_..."
    )
    if hf_key != load_api_key("huggingface"):
        save_api_key("huggingface", hf_key)

with st.sidebar.expander("⚙️ Custom Provider Settings", expanded=False):
    c_name = st.text_input("Provider Name", value=get_setting("custom_provider_name", "Custom Provider"))
    if c_name != get_setting("custom_provider_name", "Custom Provider"):
        set_setting("custom_provider_name", c_name)
        
    c_url = st.text_input("Base URL", value=get_setting("custom_provider_base_url", "https://api.openai.com/v1"))
    if c_url != get_setting("custom_provider_base_url", "https://api.openai.com/v1"):
        set_setting("custom_provider_base_url", c_url)
        
    c_models = st.text_input("Model List (comma separated)", value=get_setting("custom_provider_models", "gpt-4o, gpt-3.5-turbo"))
    if c_models != get_setting("custom_provider_models", "gpt-4o, gpt-3.5-turbo"):
        set_setting("custom_provider_models", c_models)
        
    c_key = st.text_input(
        "Custom API Key",
        value=load_api_key("custom"),
        type="password"
    )
    if c_key != load_api_key("custom"):
        save_api_key("custom", c_key)


# --- MAIN PANEL IMPLEMENTATION ---

# Error Box (if any error is present in session state)
if st.session_state.error_message:
    st.error(st.session_state.error_message)
    # Clear error message after displaying once
    st.session_state.error_message = None

# If no active chat is selected, show a premium welcome landing page
if st.session_state.active_chat_id is None:
    st.markdown(
        "<h1 style='text-align: center; margin-top: 50px; background: linear-gradient(135deg, #6366F1 0%, #10B981 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 3.5rem;'>🌌 Antigravity Chat</h1>", 
        unsafe_allow_html=True
    )
    st.markdown(
        "<p style='text-align: center; color: #9CA3AF; font-size: 1.2rem; max-width: 600px; margin: 0 auto 50px auto;'>Welcome to your personal AI chat companion. Setup your API keys in the sidebar, select a model, and start chatting.</p>", 
        unsafe_allow_html=True
    )
    
    # Showcase Cards Grid
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(
            """
            <div class='welcome-card'>
                <h3 style='color: #6366F1; margin-top:0;'>✨ Multiple LLMs</h3>
                <p style='color: #9CA3AF; font-size: 0.95rem;'>Seamlessly switch between Google Gemini, Groq, DeepSeek, Hugging Face, or add your own custom API endpoint.</p>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
    with col2:
        st.markdown(
            """
            <div class='welcome-card'>
                <h3 style='color: #10B981; margin-top:0;'>💾 SQLite Database</h3>
                <p style='color: #9CA3AF; font-size: 0.95rem;'>All chat sessions, prompts, responses, settings, and histories are securely saved in a local SQLite file.</p>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
    with col3:
        st.markdown(
            """
            <div class='welcome-card'>
                <h3 style='color: #F59E0B; margin-top:0;'>⚡ Streamlit Power</h3>
                <p style='color: #9CA3AF; font-size: 0.95rem;'>A rapid, beautifully styled web client designed in pure Python with support for Markdown rendering, code highlighting, and streaming.</p>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
    st.markdown("<div style='text-align: center; margin-top: 30px;'>", unsafe_allow_html=True)
    if st.button("🚀 Start a New Chat Session", type="primary", use_container_width=False):
        new_id = create_chat(title="New Chat Session")
        st.session_state.active_chat_id = new_id
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

else:
    # 1. Active Chat Header
    chat_id = st.session_state.active_chat_id
    active_chat = next((c for c in chats if c["id"] == chat_id), None)
    chat_title = active_chat["title"] if active_chat else "Chat"
    
    st.markdown(f"<h2 style='margin-bottom: 2px;'>{chat_title}</h2>", unsafe_allow_html=True)
    st.markdown(
        f"<p style='color: #9CA3AF; margin-bottom: 25px; font-size:0.9rem;'>Active model: <span style='color: #6366F1; font-weight:600;'>{selected_model}</span> ({provider_options[selected_provider_key]})</p>", 
        unsafe_allow_html=True
    )
    st.markdown("---")
    
    # 2. Render Previous Messages from DB
    messages = get_chat_messages(chat_id)
    
    for msg in messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("model_name") and msg["role"] == "assistant":
                st.markdown(
                    f"<div style='text-align: right; color: #4B5563; font-size: 0.75rem; margin-top: 4px;'>Generated by {msg['model_name']} ({msg['provider']})</div>",
                    unsafe_allow_html=True
                )
                
    # 3. Handle Chat Input
    prompt = st.chat_input("Ask anything...")
    
    if prompt:
        # Render User Message
        with st.chat_message("user"):
            st.markdown(prompt)
            
        # Store user message in Database
        add_message(chat_id, "user", prompt)
        
        # Get active API Key
        api_key = load_api_key(selected_provider_key)
        
        # Retrieve active provider instance
        if selected_provider_key == "custom":
            provider_cfg = {
                "name": get_setting("custom_provider_name", "Custom Provider"),
                "base_url": get_setting("custom_provider_base_url", "https://api.openai.com/v1"),
                "models": get_setting("custom_provider_models", "gpt-4o, gpt-3.5-turbo")
            }
            active_provider = get_provider(selected_provider_key, provider_cfg)
        else:
            active_provider = get_provider(selected_provider_key)
            
        # Call provider and stream response
        with st.chat_message("assistant"):
            # Prepare full history for the provider
            # Load messages from DB to include the user message we just saved
            full_messages = get_chat_messages(chat_id)
            
            try:
                # Use st.write_stream to output incoming chunks in real-time
                response_generator = active_provider.generate_stream(
                    model_name=selected_model,
                    messages=full_messages,
                    api_key=api_key,
                    temperature=0.7
                )
                
                full_response = st.write_stream(response_generator)
                
                # Save assistant response to DB
                add_message(
                    chat_id=chat_id,
                    role="assistant",
                    content=full_response,
                    model_name=selected_model,
                    provider=provider_options[selected_provider_key]
                )
                
                # If the chat has a default "New Chat Session" title, auto-rename based on prompt
                if chat_title == "New Chat Session":
                    # Simple auto-rename: first 5 words of the prompt
                    words = prompt.split()
                    auto_title = " ".join(words[:5]) + ("..." if len(words) > 5 else "")
                    rename_chat(chat_id, auto_title)
                    
                st.rerun()
                
            except Exception as e:
                # Store error message in session state and reload to display nicely
                st.session_state.error_message = f"Error generating response: {str(e)}"
                st.rerun()
