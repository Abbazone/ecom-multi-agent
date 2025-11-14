# ui_gradio.py
import os
import uuid
import requests
import gradio as gr


API_URL = os.getenv("API_URL", "http://localhost:8000/chat")


def new_session_id():
    return str(uuid.uuid4())


def call_backend(message: str, history: list, session_id: str):
    """
    Gradio callback.
    - message: latest user message
    - history: list of [user, assistant] turns
    - session_id: stable id so your multi-agent memory works
    """
    if not session_id:
        session_id = new_session_id()

    payload = {
        "session_id": session_id,
        "message": message,
    }

    try:
        resp = requests.post(API_URL, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        bot_text = f"❗ Backend error: {e}"
    else:
        # ChatResponse schema: response, agent, tool_calls, handover, ...
        text = data.get("response", "")
        agent = data.get("agent", "assistant")
        handover = data.get("handover", "")
        # Show which agent handled it (optional)
        bot_text = f"{text}\n\n---\n_agent: **{agent}**  ·  handover: `{handover}`_"

    history.append((message, bot_text))
    # Clear input, return updated history & same session_id
    return "", history, session_id


with gr.Blocks() as demo:
    gr.Markdown("# 🧠 E-commerce Multi-Agent Chat")
    gr.Markdown("Talk to the multi-agent system (order tracking, cancellation, product QA).")

    chat = gr.Chatbot(height=500)
    msg = gr.Textbox(
        label="Your message",
        placeholder="E.g. 'Track ORD-1234' or 'Cancel it please'",
    )
    clear_btn = gr.Button("New conversation")

    # Keep a session_id per browser tab
    session_id_state = gr.State(new_session_id())

    msg.submit(
        fn=call_backend,
        inputs=[msg, chat, session_id_state],
        outputs=[msg, chat, session_id_state],
    )

    def reset_chat():
        return "", [], new_session_id()

    clear_btn.click(
        fn=reset_chat,
        inputs=None,
        outputs=[msg, chat, session_id_state],
    )

if __name__ == "__main__":
    demo.launch()
