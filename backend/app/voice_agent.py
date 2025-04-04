import os
import json
import threading
import logging
import time
import asyncio
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
        
        # Add counters to track audio data
        self.audio_chunks_sent = 0
        self.audio_bytes_sent = 0
        self.last_audio_log_time = time.time()
        
        logger.info("VoiceAgent initialized with model: %s", self.model)

    def on_open(self, ws):
        """Called when the WebSocket connection is established"""
        self.connected = True
        logger.info("Connected to OpenAI Realtime API")
        
        # Call the connect callback if it exists
        if self.on_connect_callback:
            try:
                self.on_connect_callback()
            except Exception as e:
                logger.error(f"Error in on_connect_callback: {e}")

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
                # Check for session.created event to confirm successful connection
                if isinstance(data, dict) and data.get("type") == "session.created":
                    logger.info("Session created with ID: %s", data.get("session", {}).get("id", "unknown"))
                    # This is another good place to trigger the on_connect_callback
                    if self.on_connect_callback and not self.connected:
                        self.connected = True
                        self.on_connect_callback()
                
                # Check for conversation events to debug VAD
                if isinstance(data, dict) and data.get("type") == "conversation.item.created":
                    role = data.get("item", {}).get("role", "unknown")
                    content = data.get("item", {}).get("content", "unknown")
                    logger.info(f"Conversation item created - Role: {role}, Content: {content[:100]}...")
                
                # Check for error events
                if isinstance(data, dict) and "error" in data:
                    logger.error(f"Received error from OpenAI: {data}")
                        
                logger.info("Received JSON message from OpenAI: %s", json.dumps(data, indent=2))
                if self.on_message_callback:
                    self.on_message_callback(data)
            except json.JSONDecodeError:
                logger.warning("Received non-JSON message from OpenAI: %s", message)

    def on_error(self, ws, error):
        """Called when a WebSocket error occurs"""
        logger.error("WebSocket error: %s", error)

    def on_close(self, ws, close_status_code, close_msg):
        """Called when the WebSocket connection is closed"""
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
            
            reconnect_count = 0
            max_reconnects = 5
            
            while reconnect_count < max_reconnects:
                try:
                    logger.info(f"Connecting to OpenAI API (attempt {reconnect_count + 1})")
                    # Run the WebSocket connection with automatic pings.
                    self.ws_app.run_forever(ping_interval=30, ping_timeout=10)
                    
                    # If we're here, the connection closed normally
                    if not self.connected:
                        logger.info("Connection closed normally, exiting")
                        break
                        
                except Exception as e:
                    logger.error(f"WebSocket connection failed: {e}")
                
                # Only increment reconnect count for errors, not normal closures
                reconnect_count += 1
                
                if reconnect_count < max_reconnects:
                    wait_time = min(5 * reconnect_count, 30)  # Exponential backoff up to 30 seconds
                    logger.info(f"Reconnecting in {wait_time} seconds... (attempt {reconnect_count + 1}/{max_reconnects})")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Max reconnect attempts ({max_reconnects}) reached. Giving up.")

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
            try:
                self.audio_chunks_sent += 1
                self.audio_bytes_sent += len(audio_data)
                
                # Log audio stats periodically
                current_time = time.time()
                if current_time - self.last_audio_log_time > 5:
                    logger.info(f"Sent {self.audio_chunks_sent} audio chunks ({self.audio_bytes_sent} bytes) to OpenAI in the last 5 seconds")
                    self.audio_chunks_sent = 0
                    self.audio_bytes_sent = 0
                    self.last_audio_log_time = current_time
                
                # Actually send the audio data
                self.ws_app.send(audio_data, opcode=0x2)  # Binary opcode for audio
            except Exception as e:
                logger.error(f"Error sending audio data: {e}")
                self.connected = False  # Mark as disconnected on error
        else:
            logger.warning("WebSocket is not connected. Unable to send audio.")

    def send_text(self, text: str):
        """
        Send a text-based instruction to update the session.
        Uses 'session.update' with a session object containing the instructions.
        """
        if self.connected and self.ws_app:
            try:
                payload = json.dumps({
                    "type": "session.update",
                    "session": {
                        "instructions": text
                    }
                })
                self.ws_app.send(payload)
                logger.info("Sent session.update with instructions to OpenAI: %s", text)
            except Exception as e:
                logger.error(f"Error sending text instruction: {e}")
                self.connected = False  # Mark as disconnected on error
        else:
            logger.warning("WebSocket is not connected. Unable to send text.")
            
    def send_user_message(self, text: str):
        """
        Send a user message to the conversation.
        This can be used to manually trigger a response from the AI.
        """
        if self.connected and self.ws_app:
            try:
                # First create the conversation item
                conversation_payload = json.dumps({
                    "type": "conversation.item.create",
                    "item": {
                        "type": "message",
                        "role": "user",
                        "content": text
                    }
                })
                self.ws_app.send(conversation_payload)
                logger.info("Sent user message to conversation: %s", text)
                
                # Then force a response
                response_payload = json.dumps({
                    "type": "response.create"
                })
                self.ws_app.send(response_payload)
                logger.info("Requested response from OpenAI")
                
                return True
            except Exception as e:
                logger.error(f"Error sending user message: {e}")
                self.connected = False  # Mark as disconnected on error
                return False
        else:
            logger.warning("WebSocket is not connected. Unable to send user message.")
            return False
            
    def interrupt(self):
        """
        Interrupt the current AI voice response.
        """
        if self.connected and self.ws_app:
            try:
                payload = json.dumps({
                    "type": "interrupt"
                })
                self.ws_app.send(payload)
                logger.info("Sent interrupt command to OpenAI")
                return True
            except Exception as e:
                logger.error(f"Error sending interrupt: {e}")
                return False
        else:
            logger.warning("WebSocket is not connected. Unable to send interrupt.")
            return False

    def stop(self):
        """
        Stop the voice agent by closing the WebSocket connection.
        """
        if self.ws_app:
            try:
                self.ws_app.close()
                logger.info("WebSocket connection closed")
            except Exception as e:
                logger.error(f"Error closing WebSocket: {e}")
        self.connected = False

    def set_on_message_callback(self, callback):
        """
        Set a callback to handle messages received from the realtime API.
        The callback should accept one argument (the received data).
        """
        self.on_message_callback = callback
        logger.info("Message callback set")
        
    def set_on_connect_callback(self, callback):
        """
        Set a callback to be called when the connection is established.
        """
        self.on_connect_callback = callback
        logger.info("Connect callback set")

if __name__ == "__main__":
    import time

    def handle_message(data):
        logger.info("Callback received data: %s", data)
        
    def handle_connect():
        logger.info("Agent connected to OpenAI!")

    agent = VoiceAgent()
    agent.set_on_message_callback(handle_message)
    agent.set_on_connect_callback(handle_connect)
    agent.connect()

    # Allow time for the connection to establish.
    time.sleep(2)
    
    # Initialize the session with a prompt using session.update.
    initial_prompt = (
        "You are Sophia, a career assistant specializing in interview preparation. "
        "Provide real-time, actionable feedback as the user practices interview responses."
    )
    agent.send_text(initial_prompt)
    
    # Send a test message to verify the connection works
    time.sleep(2)
    agent.send_user_message("Hello Sophia, can you introduce yourself?")

    # Keep the program running to listen for responses.
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        agent.interrupt()
        agent.stop()