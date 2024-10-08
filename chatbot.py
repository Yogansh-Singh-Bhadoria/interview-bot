from characterai import aiocai
import asyncio
import streamlit as st
from streamlit_chat import message
import uuid
import pyttsx3
import speech_recognition as sr
import requests
import base64

st.title("InterviewBot - AI Interview Chatbot")

# JavaScript for tab switching alert
st.markdown(
    """
    <script>
    document.addEventListener('visibilitychange', function() {
      if (document.hidden) {
        alert("Warning: You have switched tabs. This is not allowed during the interview.");
        // Optionally, report the tab switch to the backend
        fetch('/report_tab_switch', { method: 'POST' });
      }
    });
    </script>
    """,
    unsafe_allow_html=True
)

# JavaScript for automatic screen sharing
st.markdown(
    """
    <script>
    async function startScreenShare() {
        try {
            const stream = await navigator.mediaDevices.getDisplayMedia({ video: true });
            console.log("Screen sharing started:", stream);
            // Here you would connect the stream to your WebRTC setup
            // This is just a placeholder for demonstration purposes
        } catch (err) {
            console.error("Error starting screen share:", err);
        }
    }

    // Automatically start screen share when the page loads
    window.onload = startScreenShare;
    </script>
    """,
    unsafe_allow_html=True
)

class InterviewBot:
    char = 'f4hEGbw8ywUrjsrye03EJxiBdooy--HiOWgU2EiRJ0s'  # Character ID
    token = '67c42f8f986f526fe33a8630b9bdbbf97b219783'  # API token
    tts_engine = pyttsx3.init()
    did_api_key = 'ew9nyw5zahniyxnretjaz21hawwuy29t:uLUZOCoiV5spKOw_hWegr'  # D-ID API key (username:password)

    def __init__(self) -> None:
        if 'questions' not in st.session_state:
            st.session_state['questions'] = []
        if 'answers' not in st.session_state:
            st.session_state['answers'] = []
        if 'interview_step' not in st.session_state:
            st.session_state['interview_step'] = 0

        self.session_state = st.session_state

    async def start_chat(self):
        """Connect to Character.AI and start a chat."""
        try:
            client = aiocai.Client(self.token)
            me = await client.get_me()  # Retrieve your user information
            async with client as conn:
                new_chat = await conn.create_chat(self.char)  # Create a new chat using the character ID
                return conn, new_chat
        except Exception as e:
            st.write(f"An error occurred during chat connection: {e}")
            return None, None

    async def prepare_questions(self) -> None:
        """Prepares a list of predefined questions."""
        questions = [
            "Hi! It's nice to meet you. What's your name?",
            "Why are you interested in this job?",
            "What skills do you bring to the table?",
            "What do you think is your greatest strength?",
        ]
        self.session_state['questions'] = [(question, self._generate_uuid()) for question in questions]

    def ask_question(self) -> None:
        """Ask the current interview question."""
        if self.session_state['interview_step'] < len(self.session_state['questions']):
            text, key = self.session_state['questions'][self.session_state['interview_step']]
            self._text_to_speech(text)
            message(text, key=f'message_{key}')
            st.session_state['current_question'] = text
            st.write(f"Bot: {text}")

    def _text_to_speech(self, text: str) -> None:
        """Convert text to speech and play it."""
        self.tts_engine.say(text)
        self.tts_engine.runAndWait()

    def get_audio_answer(self) -> None:
        """Get the user's response via audio."""
        r = sr.Recognizer()
        with sr.Microphone() as source:
            st.write("Listening for your answer...")
            audio = r.listen(source)

        try:
            answer = r.recognize_google(audio)
            st.write(f"You said: {answer}")
            self.session_state['answers'].append((answer, self._generate_uuid()))
            asyncio.run(self.ask_dynamic_question(answer))
            self.session_state['interview_step'] += 1
            st.experimental_rerun()

        except sr.UnknownValueError:
            st.write("Sorry, I could not understand the audio. Please try again.")
            self.get_audio_answer()
        except sr.RequestError as e:
            st.write(f"Could not request results; {e}")

    async def ask_dynamic_question(self, user_answer: str) -> None:
        """Ask a dynamic question based on the user's answer."""
        conn, new_chat = await self.start_chat()
        if conn and new_chat:
            try:
                past_interactions = "\n".join(
                    [f"Q: {q[0]}\nA: {a[0]}" for q, a in zip(self.session_state['questions'], self.session_state['answers'])]
                )
                prompt = f"{past_interactions}\nQ: {user_answer}\nA:"
                response = await new_chat.send_message(self.char, new_chat.id, prompt)

                if response and hasattr(response, 'text'):
                    follow_up = response.text.strip()
                    self.session_state['questions'].append((follow_up, self._generate_uuid()))
                    st.write(f"Bot: {follow_up}")
                    self._text_to_speech(follow_up)
                    await self.generate_avatar_video(follow_up)
                else:
                    st.write("No valid response from Character.AI.")
            except Exception as e:
                st.write(f"An error occurred while sending the message: {e}")
        else:
            st.write("Failed to connect to the chat.")

    async def generate_avatar_video(self, text: str) -> None:
        """Generate a video of the avatar speaking the given text."""
        api_key_bytes = base64.b64encode(self.did_api_key.encode()).decode()
        url = "https://api.d-id.com/talks"
        headers = {
            'Authorization': f'Basic {api_key_bytes}',
            'Content-Type': 'application/json'
        }
        data = {
            "source_url": "https://studio.d-id.com/agents/share?id=agt_LUCbkxOQ&key=WjI5dloyeGxMVzloZFhSb01ud3hNRGs0TmpJNU1EYzRNelkxTVRBME1EVXlNams2TVVFMU5VbHFNWEpUV1hSeU1rRnhialF3WkUwMA==",
            "text": text,
            "driver_url": "bank://default"
        }

        response = requests.post(url, json=data, headers=headers)

        if response.status_code == 200:
            video_url = response.json().get("result_url")
            st.write(f"Avatar video generated: {video_url}")
        else:
            st.write(f"Error generating avatar video: {response.text}")

    def display_past_questions_and_answers(self) -> None:
        """Displays the conversation so far."""
        for i in range(self.session_state['interview_step']):
            question_text, question_key = self.session_state['questions'][i]
            message(question_text, key=f'message_{question_key}')

            if i < len(self.session_state['answers']):
                answer_text, answer_key = self.session_state['answers'][i]
                message(answer_text, is_user=True, key=f'message_{answer_key}')
                st.write(f"You: {answer_text}")

    def execute_interview(self) -> None:
        """Run the interview by displaying past questions, asking the next one, and getting audio input."""
        self.display_past_questions_and_answers()
        if self.session_state['interview_step'] < len(self.session_state['questions']):
            self.ask_question()
            self.get_audio_answer()
        else:
            st.write("Interview complete!")

    @staticmethod
    def _generate_uuid() -> str:
        """Generate a UUID for unique identification."""
        return str(uuid.uuid4())

def create_bot() -> None:
    """Create and initialize the InterviewBot."""
    bot = InterviewBot()
    if len(bot.session_state['questions']) == 0:
        intro_text = "Hey there! I'm your friendly interviewer bot. Let’s get started!"
        bot._text_to_speech(intro_text)
        message(intro_text, key="greeting")
        st.write(intro_text)
        asyncio.run(bot.prepare_questions())

    bot.execute_interview()

def show_live_camera_feed():
    """Displays a live camera feed in the sidebar."""
    with st.sidebar:
        st.subheader("Live Camera Feed")
        st.markdown(
            '''
            <iframe src="http://127.0.0.1:5000/video_feed" width="320" height="240" frameborder="0"></iframe>
            ''',
            unsafe_allow_html=True
        )

# Streamlit UI
show_live_camera_feed()
create_bot()
