import os
import json
import threading
import logging
import time  # Import time at the module level for __main__ usage
from websocket import WebSocketApp
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class VoiceAgent:
    """
    A voice agent that connects to OpenAI's Realtime API using a
    speech-to-speech multimodal architecture. It is designed to provide
    real-time interview preparation and vocal advisory responses.
    """
    def __init__(self, model: str = "gpt-4o-realtime-preview-2024-12-17"):
        self.api_key = os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            logger.error("OPENAI_API_KEY environment variable not set.")
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
        self.on_connect_callback = None
        logger.info("VoiceAgent initialized with model: %s", self.model)

    def on_open(self, ws):
        self.connected = True
        logger.info("Connected to OpenAI Realtime API")
        if self.on_connect_callback:
            self.on_connect_callback()

    def set_on_connect_callback(self, callback):
        """
        Set a callback to be called when the connection is established.
        """
        self.on_connect_callback = callback
        logger.info("Connect callback set")
        
    def on_message(self, ws, message):
        """
        Handles incoming messages from the realtime API.
        The message may be a JSON payload or binary audio data.
        """
        if isinstance(message, bytes):
            logger.info("Received binary audio data from OpenAI, length: %d bytes", len(message))
            if self.on_message_callback:
                self.on_message_callback(message)
        else:
            try:
                data = json.loads(message)
                logger.info("Received JSON message from OpenAI: %s", json.dumps(data, indent=2))
                if self.on_message_callback:
                    self.on_message_callback(data)
            except json.JSONDecodeError:
                logger.warning("Received non-JSON message from OpenAI: %s", message)

    def on_error(self, ws, error):
        logger.error("WebSocket error: %s", error)

    def on_close(self, ws, close_status_code, close_msg):
        self.connected = False
        logger.info("WebSocket connection closed: %s %s", close_status_code, close_msg)

    def connect(self):
        """
        Establish the WebSocket connection to the Realtime API in a dedicated thread.
        This method creates a new asyncio event loop in the thread to avoid
        "no current event loop" errors and adds pings to keep the connection alive.
        """
        def run_ws():
            import asyncio
            # Create a new event loop for this thread.
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            while True:
                try:
                    # Run the WebSocket connection with automatic pings.
                    self.ws_app.run_forever(ping_interval=30, ping_timeout=10)
                except Exception as e:
                    logger.error("WebSocket connection failed: %s", e)
                logger.info("Reconnecting in 5 seconds...")
                time.sleep(5)

        self.ws_app = WebSocketApp(
            self.url,
            header=self.headers,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        self.thread = threading.Thread(target=run_ws, daemon=True)
        self.thread.start()
        logger.info("WebSocket connection thread started")

    def send_audio(self, audio_data: bytes):
        """
        Send binary audio data to the realtime API.
        """
        if self.connected and self.ws_app:
            logger.info("Sending audio data to OpenAI, length: %d bytes", len(audio_data))
            self.ws_app.send(audio_data, opcode=0x2)  # Binary opcode for audio
        else:
            logger.warning("WebSocket is not connected. Unable to send audio.")

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
            logger.info("Sent session.update with instructions to OpenAI: %s", text)
        else:
            logger.warning("WebSocket is not connected. Unable to send text.")

    def interrupt(self):
        """
        Interrupt the current AI voice response.
        """
        logger.info("Interrupting the current session...")
        self.stop()

    def stop(self):
        """
        Stop the voice agent by closing the WebSocket connection.
        """
        if self.ws_app:
            self.ws_app.close()
            logger.info("WebSocket connection closed")

    def set_on_message_callback(self, callback):
        """
        Set a callback to handle messages received from the realtime API.
        The callback should accept one argument (the received data).
        """
        self.on_message_callback = callback
        logger.info("Message callback set")

if __name__ == "__main__":
    import time

    def handle_message(data):
        logger.info("Callback received data: %s", data)

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
