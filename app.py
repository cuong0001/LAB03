"""Lumen Travel assistant: Firebase sign-in (Lab 3) + RAG chat (Lab 5)."""
import streamlit as st

import rag
from firebase_client import FirebaseError, create_account, sign_in, validate_config

st.set_page_config(page_title="Lumen Travel Assistant")


# ---------- Session state (one visitor; never put these in a global cache) ----------
def init_state():
    st.session_state.setdefault("user", None)    # None = signed out
    st.session_state.setdefault("messages", [])  # chat history of this session only


def sign_out():
    for key in ("user", "messages"):            # history cleared at sign-out
        st.session_state.pop(key, None)


# ---------- Embed the guide ONCE (shared, contains no user data) ----------
@st.cache_resource(show_spinner="Embedding the travel guide (only once)...")
def load_rag():
    rag.check_server()
    guide = rag.load_guide()
    vectors = rag.build_index(guide)
    return guide, vectors


# ---------- Sign-in / sign-up page ----------
def auth_form(mode):
    with st.form(f"{mode}_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        label = "Sign in" if mode == "signin" else "Create account"
        submitted = st.form_submit_button(label)
    if not submitted:
        return
    try:
        if mode == "signup":
            create_account(email, password)
            st.success("Account created. Sign in on the Sign in tab with the same credentials.")
            return
        user = sign_in(email, password)
    except FirebaseError as err:
        st.error(str(err))                 # wrong sign-in, weak password, ...
        return
    st.session_state.user = user
    st.session_state.messages = []
    st.rerun()                             # redraw -> chat page


def auth_page():
    st.title("Lumen Travel")
    st.write(f"Sign in to chat with the {rag.CITY} travel assistant.")
    st.caption("Use a separate app password, not your Google password.")
    tab_in, tab_up = st.tabs(["Sign in", "Sign up"])
    with tab_in:
        auth_form("signin")
    with tab_up:
        auth_form("signup")


# ---------- Chat page ----------
def show_sources(hits):
    with st.expander(f"Retrieved guide entries ({len(hits)})"):
        for h in hits:
            st.markdown(f"**[{h['id']}] {h['title']}** — score `{h['score']:.3f}`")
            st.caption(f"{h['text']}  \nSource: {h['source']}")


def show_message(msg):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("unknown_ids"):
            st.warning(f"The answer cites IDs that were not retrieved: {msg['unknown_ids']}")
        if msg.get("hits"):
            show_sources(msg["hits"])


def chat_page():
    with st.sidebar:
        st.write(f"Signed in as **{st.session_state.user['email']}**")
        st.button("Sign out", on_click=sign_out)
        st.caption(f"top-k = {rag.TOP_K}, min score = {rag.MIN_SCORE}")

    st.title(f"{rag.CITY} travel assistant")

    try:
        guide, vectors = load_rag()
    except rag.OllamaError as err:
        st.error(str(err))
        st.info("Start the server notebook and Pinggy, update OLLAMA_URL in .env, then reload.")
        st.stop()
    except (FileNotFoundError, ValueError) as err:
        st.error(f"Problem with knowledge_base.json: {err}")
        st.stop()

    for msg in st.session_state.messages:   # replay history after each rerun
        show_message(msg)

    question = st.chat_input(f"Ask about {rag.CITY}...")
    if question is None:
        return
    question = question.strip()
    if not question:
        st.warning("Please type a question first.")   # empty question
        return

    user_msg = {"role": "user", "content": question}
    st.session_state.messages.append(user_msg)
    show_message(user_msg)

    with st.spinner("Searching the guide..."):
        try:
            reply, hits = rag.answer(question, guide, vectors)
        except rag.OllamaError as err:
            st.session_state.messages.pop()        # drop the unanswered question
            st.error(str(err))
            return

    bot_msg = {"role": "assistant", "content": reply, "hits": hits,
               "unknown_ids": rag.citation_check(reply, hits)["unknown_ids"]}
    st.session_state.messages.append(bot_msg)
    show_message(bot_msg)


# ---------- Router ----------
init_state()
try:
    validate_config()
except FirebaseError as err:
    st.info(str(err))
    st.stop()

if st.session_state.user is None:
    auth_page()     # chat is never drawn for signed-out users
else:
    chat_page()