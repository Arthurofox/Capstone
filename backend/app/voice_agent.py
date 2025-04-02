import os
import json
import threading
from websocket import WebSocketApp
from dotenv import load_dotenv
# Load environment variables
load_dotenv()

class VoiceAgent:
    """
    A voice agent that connects to OpenAI's Realtime API using a
    speech-to-speech multimodal architecture. It is designed to provide
    real-time interview preparation and vocal advisory responses.
    """
    def __init__(self, model: str = "gpt-4o-realtime-preview-2024-12-17"):
        self.api_key = os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set.")
        
        self.model = model
        self.url = f"wss://api.openai.com/v1/realtime?model={self.model}"
        self.headers = [
            "Authorization: Bearer " + self.api_key,
            "OpenAI-Beta: realtime=v1"
        ]
        self.ws_app = None
        self.thread = None
        self.connected = False
        self.on_message_callback = None

    def on_open(self, ws):
        self.connected = True
        print("Connected to OpenAI Realtime API.")

    def on_message(self, ws, message):
        """
        Handles incoming messages from the realtime API.
        The message may be a JSON payload or binary audio data.
        """
        try:
            data = json.loads(message)
            print("Received JSON message:", json.dumps(data, indent=2))
            if self.on_message_callback:
                self.on_message_callback(data)
        except json.JSONDecodeError:
            # If not JSON, assume binary audio data.
            print("Received non-JSON message (possibly audio data).")
            if self.on_message_callback:
                self.on_message_callback(message)

    def on_error(self, ws, error):
        print("WebSocket error:", error)

    def on_close(self, ws, close_status_code, close_msg):
        self.connected = False
        print("WebSocket connection closed:", close_status_code, close_msg)

    def connect(self):
        """
        Establish the WebSocket connection to the Realtime API in a dedicated thread.
        """
        self.ws_app = WebSocketApp(
            self.url,
            header=self.headers,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        self.thread = threading.Thread(target=self.ws_app.run_forever)
        self.thread.daemon = True
        self.thread.start()

    def send_audio(self, audio_data: bytes):
        """
        Send binary audio data to the realtime API.
        """
        if self.connected and self.ws_app:
            # Opcode 0x2 signifies binary data.
            self.ws_app.send(audio_data, opcode=0x2)
        else:
            print("WebSocket is not connected. Unable to send audio.")

    def send_text(self, text: str):
        """
        Send a text-based instruction to update the session.
        Uses 'session.update' with a session object containing the instructions.
        """
        if self.connected and self.ws_app:
            payload = json.dumps({
                "type": "session.update",
                "session": {
                    "instructions": text
                }
            })
            self.ws_app.send(payload)
        else:
            print("WebSocket is not connected. Unable to send text.")

    def interrupt(self):
        """
        Interrupt the current AI voice response.
        """
        print("Interrupting the current session...")
        self.stop()

    def stop(self):
        """
        Stop the voice agent by closing the WebSocket connection.
        """
        if self.ws_app:
            self.ws_app.close()

    def set_on_message_callback(self, callback):
        """
        Set a callback to handle messages received from the realtime API.
        The callback should accept one argument (the received data).
        """
        self.on_message_callback = callback

if __name__ == "__main__":
    # Example test run of the VoiceAgent
    import time

    def handle_message(data):
        print("Callback received data:", data)

    agent = VoiceAgent()
    agent.set_on_message_callback(handle_message)
    agent.connect()

    # Allow time for the connection to establish.
    time.sleep(2)
    
    # Initialize the session with a prompt using session.update.
    initial_prompt = (
        "You are Sophia, a career assistant specializing in interview preparation. "
        "Provide real-time, actionable feedback as the user practices interview responses."
    )
    agent.send_text(initial_prompt)

    # Keep the program running to listen for responses.
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        agent.interrupt()
