import os
from google import genai
from google.genai import types
from dotenv import load_dotenv
import streamlit as st
from streamlit_js_eval import streamlit_js_eval

# Load environment variables (.env file)
load_dotenv()

# Setting up the Streamlit page configuration
st.set_page_config(page_title="Streamlit Chat", page_icon="💬")
st.title("Chatbot")

# Initialize session state variable to track setup completion
if "setup_complete" not in st.session_state:
    st.session_state.setup_complete = False
if "user_message_count" not in st.session_state:
    st.session_state.user_message_count = 0
if "feedback_shown" not in st.session_state:
    st.session_state.feedback_shown = False
if "chat_completed" not in st.session_state:
    st.session_state.chat_completed = False

# Helper function to update session state
def complete_setup():
    st.session_state.setup_complete = True

def show_feedback():
    st.session_state.feedback_shown = True

# Setup stage for collecting user details
if not st.session_state.setup_complete:

    st.subheader('Personal information', divider='rainbow')

    if "name" not in st.session_state:
        st.session_state["name"] = ""
    if "experience" not in st.session_state:
        st.session_state["experience"] = ""
    if "skills" not in st.session_state:
        st.session_state["skills"] = ""

    # Test labels for personal information
    st.session_state["name"] = st.text_input(label="Name", max_chars = 40, value=st.session_state["name"], placeholder="Enter your name")

    st.session_state["experience"] = st.text_area(label="Experience", value=st.session_state["experience"], height=None, max_chars=200, placeholder="Describe your experience")

    st.session_state["skills"] = st.text_area(label="Skills", value=st.session_state["skills"], height=None, max_chars=200, placeholder="List your skills")


    st.subheader('Company and Position', divider='rainbow')

    if "level" not in st.session_state:
        st.session_state["level"] = "Junior"
    if "position" not in st.session_state:
        st.session_state["position"] = "Data Scientist"
    if "company" not in st.session_state:
        st.session_state["company"] = "Amazon"

    col1, col2 = st.columns(2)
    with col1:
        st.session_state["level"] = st.radio(
            "Choose level",
            key="visibility",
            options=["Junior", "Mid-level", "Senior"],
        )

    with col2:
        st.session_state["position"] = st.selectbox(
            "Choose a position",
            ("Data Scientist", "Data engineer", "ML Engineer", "BI Analyst", "Financial Analyst")
        )

    st.session_state["company"] = st.selectbox(
        "Choose a Company",
        ("Amazon", "Meta", "Udemy", "365 Company", "Nestle", "LinkedIn", "Spotify")
    )

    # A button to complete the setup stage and start the interview
    if st.button("Start Interview", on_click=complete_setup):
        st.write("Setup complete. Starting interview...")

# Interview stage
if st.session_state.setup_complete and not st.session_state.feedback_shown and not st.session_state.chat_completed:
    # Display a welcome message and prompt the user to introduce themselves
    st.info(
        """
        Start by introducing yourself.
        """,
        icon="👋"
    )

    # Initialize the Gemini client (reads GEMINI_API_KEY from .env automatically)
    client = genai.Client()

    if "gemini_model" not in st.session_state:
        st.session_state["gemini_model"] = "gemini-2.5-flash"

   # Initialize the 'messages' list and add a system message 
    if "messages" not in st.session_state:
        st.session_state.messages = [{
            "role": "system",
            "content": (f"You are an HR executive that interviews an interviewee called {st.session_state['name']} "
                        f"with experience {st.session_state['experience']} and skills {st.session_state['skills']}. "
                        f"You should interview him for the position {st.session_state['level']} {st.session_state['position']} "
                        f"at the company {st.session_state['company']}")
        }]


    # Display chat messages
    for message in st.session_state.messages:
        if message["role"] != "system":
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

# Input field for the user to send a new message
    if st.session_state.user_message_count < 5:
        if prompt := st.chat_input("Your answer.", max_chars=1000):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # Assistant's response
            with st.chat_message("assistant"):
                # Format history into Gemini format
                contents = []
                system_instruction = None
                for m in st.session_state.messages:
                    if m["role"] == "system":
                        system_instruction = m["content"]
                    else:
                        contents.append({
                            "role": "user" if m["role"] == "user" else "model",
                            "parts": [{"text": m["content"]}]
                        })

                response_stream = client.models.generate_content_stream(
                    model=st.session_state["gemini_model"],
                    contents=contents,
                    config=types.GenerateContentConfig(system_instruction=system_instruction) if system_instruction else None
                )
                response = st.write_stream(chunk.text for chunk in response_stream)

            st.session_state.messages.append({"role": "assistant", "content": response})
            st.session_state.user_message_count += 1

    if st.session_state.user_message_count >= 5:
        st.session_state.chat_completed = True
                
if st.session_state.chat_completed and not st.session_state.feedback_shown:
    if st.button("Provide Feedback", on_click=show_feedback):
        st.write("Fetching feedback...")

if st.session_state.feedback_shown:
    st.subheader("Feedback")

    conversation_history = "\n".join([f"{msg['role']}: {msg['content']}" for msg in st.session_state.messages])

    # Initialize new Gemini client instance for feedback
    feedback_client = genai.Client()

    # Define system instructions for the feedback
    feedback_system_instruction = """You are a helpful tool that provides feedback on an interviewee performance.
    Before the Feedback give a score of 1 to 10.
    Follow this format:
    Overal Score: //Your score
    Feedback: //Here you put your feedback
    Give only the feedback do not ask any additional questins."""

    # Generate feedback using the stored messages
    feedback_completion = feedback_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"This is the interview you need to evaluate. Keep in mind that you are only a tool. And you shouldn't engage in any converstation: {conversation_history}",
        config=types.GenerateContentConfig(
            system_instruction=feedback_system_instruction
        )
    )

    # To display or use the output:
    # st.write(feedback_completion.text)

    st.write(feedback_completion.text)

    if st.button("Restart Interview", type="primary"):
        streamlit_js_eval(js_expressions="parent.window.location.reload()")