import os
import uuid
from datetime import datetime
import streamlit as st
from groq import Groq
from dotenv import load_dotenv

# importing SYSTEM_PROMPT
try:
    from config import SYSTEM_PROMPT
except ImportError:
    SYSTEM_PROMPT = "You are a helpful, precise, and intelligent AI assistant."

# Load environment variables
load_dotenv()
my_api_key = os.getenv("GROQ_API_KEY")

def ask_groq_stream(client, messages, system_instructions, temperature, max_tokens):
    """Streams responses from Groq with custom injection parameters."""
    full_messages = [{"role": "system", "content": system_instructions}] + messages
    
    chat_completion = client.chat.completions.create(
        messages=full_messages,
        model="llama-3.3-70b-versatile",
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True
    )
    
    for chunk in chat_completion:
        if chunk.choices[0].delta.content is not None:
            yield chunk.choices[0].delta.content

def main(client):
    st.set_page_config(page_title="Advanced AI Chatbot", layout="wide")

    # -----------------------------------------------------------------
    # 1. SESSION STATE INITIALIZATION
    # -----------------------------------------------------------------
    if "all_sessions" not in st.session_state:
        st.session_state.all_sessions = {}
        
    if "current_session_id" not in st.session_state:
        first_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime("%I:%M %p")
        st.session_state.all_sessions[first_id] = {
            "title": f"Chat {timestamp}",
            "messages": []
        }
        st.session_state.current_session_id = first_id

    # Reference helper shortcuts
    current_id = st.session_state.current_session_id
    current_session = st.session_state.all_sessions[current_id]
    active_history = current_session["messages"]

    # -----------------------------------------------------------------
    # 2. SIDEBAR INTERFACE
    # -----------------------------------------------------------------
    with st.sidebar:
        st.title("Chat Central")
        
        # session management
        if st.button("New Chat Thread", use_container_width=True, type="primary"):
            new_id = str(uuid.uuid4())
            new_time = datetime.now().strftime("%I:%M %p")
            st.session_state.all_sessions[new_id] = {
                "title": f"Chat {new_time}",
                "messages": []
            }
            st.session_state.current_session_id = new_id
            st.rerun()

        st.write("---")
        
        # chat custom personas
        st.subheader("AI Persona")
        persona_choice = st.selectbox(
            "Change chatbot behavior:",
            ["Standard Assistant", "Code Architect", "Sarcastic Buddy", "Academic Editor"],
            label_visibility="collapsed"
        )
        
        # mapping selected personas 
        if persona_choice == "Code Architect":
            active_prompt = "You are an expert software architect. Analyze code strictly, prioritize security, performance, and best practices."
        elif persona_choice == "Sarcastic Buddy":
            active_prompt = "You are a helpful assistant but speak with lighthearted sarcasm, jokes, and modern witty banter."
        elif persona_choice == "Academic Editor":
            active_prompt = "You are an elite academic editor. Critique structure, clarify phrasing, and correct academic tone precisely."
        else:
            active_prompt = SYSTEM_PROMPT

        st.write("---")

        # --- Feature C: Hyperparameter Sliders ---
        st.subheader("Model Tuning")
        api_temp = st.slider("Creativity (Temperature)", 0.0, 1.0, 0.6, step=0.1)
        api_tokens = st.slider("Max Response Length", 256, 4096, 2048, step=256)

        st.write("---")

        # quick Prompts
        st.subheader("Quick Prompts")
        suggestions = [
            "Explain Quantum Computing simply.",
            "Review this code for vulnerabilities:",
            "Draft a polite resignation email:"
        ]
        
        # We handle quick prompt execution below by updating target variables
        triggered_quick_prompt = None
        for hint in suggestions:
            if st.button(hint, use_container_width=True):
                triggered_quick_prompt = hint

        st.write("---")

        # past chat ---
        st.subheader("History & Logs")
        
        # history session switcher buttons
        for sess_id, data in list(st.session_state.all_sessions.items()):
            is_active = (sess_id == current_id)
            if st.button(
                f"{data['title']}", 
                key=sess_id, 
                use_container_width=True,
                type="secondary" if not is_active else "primary"
            ):
                st.session_state.current_session_id = sess_id
                st.rerun()

        st.write("")
        
        # download Logs Button
        if active_history:
            log_payload = ""
            for msg in active_history:
                speaker = "User" if msg["role"] == "user" else "AI"
                log_payload += f"[{speaker}]:\n{msg['content']}\n\n"
                
            st.download_button(
                label="Export Current Logs",
                data=log_payload,
                file_name=f"chat_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain",
                use_container_width=True
            )

        # clear active messages list
        if st.button("Wipe Current History", use_container_width=True):
            current_session["messages"] = []
            st.rerun()

    # -----------------------------------------------------------------
    # 3. MAIN CHAT CONTAINER VIEW
    # -----------------------------------------------------------------
    st.title("Ask Chatbot")
    st.caption(f"Active Profile: **{persona_choice}** | Temperature: **{api_temp}**")

    # render history to view window
    for msg in active_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # collect input via standard bar or triggered sidebar shortcut
    user_input = st.chat_input("Ask something...")
    if triggered_quick_prompt:
        user_input = triggered_quick_prompt

    if user_input:
        # dynamic naming structure for new chat windows
        if len(active_history) == 0:
            short_title = " ".join(user_input.split()[:4])
            current_session["title"] = short_title + "..." if len(user_input.split()) > 4 else short_title

        # store human prompt
        with st.chat_message("user"):
            st.write(user_input)
        active_history.append({"role": "user", "content": user_input})

        # stream machine response
        with st.chat_message("assistant"):
            assistant_response = st.write_stream(
                ask_groq_stream(client, active_history, active_prompt, api_temp, api_tokens)
            )
        active_history.append({"role": "assistant", "content": assistant_response})
        
        st.rerun()

if __name__ == "__main__":
    if not my_api_key:
        st.error("Missing GROQ_API_KEY environment variable. Please check your `.env` configuration file.")
    else:
        groq_client = Groq(api_key=my_api_key)
        main(groq_client)