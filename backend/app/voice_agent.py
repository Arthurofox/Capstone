"""
Module: voice_agent.py
----------------------
This module implements a real-time voice agent using WebRTC and OpenAI's 
realtime API. It provides the following capabilities:

  - Capturing client audio frames via a custom MediaStreamTrack.
  - Establishing a WebRTC PeerConnection.
  - Performing an SDP exchange with OpenAI's realtime endpoint.
  - Handling data channels for session updates and incoming messages.
  - Exposing a FastAPI endpoint (/webrtc/voice) for initiating voice communication.

Key Components:
  - ClientAudioTrack: Custom audio track to buffer and supply audio frames.
  - VoiceAgentRTC: Class that encapsulates the initialization and connection logic for the RTC session.
  - FastAPI endpoint: Provides an SDP answer to client offers to set up the WebRTC connection.
"""

import os
import json
import logging
import asyncio
import aiohttp

from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack, RTCDataChannel
from aiortc.contrib.media import MediaRelay
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# Load environment variables (e.g., API keys)
load_dotenv()

# Configure logging for the voice agent module.
logger = logging.getLogger("VoiceAgentRTC")

# Import the prompt handler to access the voice instruction.
from app.prompt_handler import CareerAssistantPromptHandler

# Create a FastAPI instance for handling requests.
app = FastAPI()


class ClientAudioTrack(MediaStreamTrack):
    """
    Custom MediaStreamTrack to handle client-side audio.
    
    This track uses an asyncio.Queue to buffer incoming audio frames and
    supplies them when requested by the RTCPeerConnection.
    """
    kind = "audio"
    
    def __init__(self):
        super().__init__()
        self.queue = asyncio.Queue()
    
    async def recv(self):
        """
        Await and return the next audio frame from the queue.
        """
        frame = await self.queue.get()
        return frame

    async def push_frame(self, frame):
        """
        Push an audio frame into the queue.
        
        Args:
            frame: The audio frame to be queued.
        """
        await self.queue.put(frame)


class VoiceAgentRTC:
    """
    Handles the WebRTC connection for real-time voice interactions with OpenAI's API.

    This class sets up a peer connection, adds audio tracks, performs the SDP exchange
    (offer/answer), and handles communication via data channels. The session uses a specific
    voice model and configuration obtained from environment variables.

    Attributes:
        model (str): The realtime voice model used for the session.
        api_key (str): The OpenAI API key.
        base_url (str): Base URL for the OpenAI realtime endpoint.
        pc (RTCPeerConnection): The main peer connection instance.
        client_audio_track (ClientAudioTrack): Audio track for outgoing audio frames.
        relay (MediaRelay): Media relay object for handling media streams.
        remote_audio: Placeholder for the incoming audio track.
        on_message_callback: Callback function to process incoming data channel messages.
        data_channel (RTCDataChannel): Channel for exchanging events and session updates.
    """
    def __init__(self, model="gpt-4o-realtime-preview-2024-12-17"):
        self.model = model
        self.api_key = os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not set")
        
        # Base URL for the realtime API endpoint.
        self.base_url = "https://api.openai.com/v1/realtime"
        
        # Initialize the main RTCPeerConnection.
        self.pc = RTCPeerConnection()
        
        # Create and add the custom client audio track to the connection.
        self.client_audio_track = ClientAudioTrack()
        self.pc.addTrack(self.client_audio_track)
        
        # Media relay for handling media stream distribution.
        self.relay = MediaRelay()
        
        # Placeholder for storing the remote audio track.
        self.remote_audio = None
        
        # Callback for incoming data channel messages.
        self.on_message_callback = None
        
        # Create a data channel to send session updates and other events.
        self.data_channel = self.pc.createDataChannel("oai-events")

    async def connect(self):
        """
        Establish the WebRTC connection with OpenAI's realtime API.
        
        Steps performed:
          1. Create an SDP offer and set it as the local description.
          2. Request a session token from the local API endpoint (/session).
          3. Exchange the SDP offer with OpenAI to obtain an SDP answer.
          4. Set the SDP answer as the remote description.
          5. Define data channel callbacks for session updates and message handling.
          6. Handle incoming media tracks.
        """
        try:
            # Create and set the local SDP offer.
            offer = await self.pc.createOffer()
            await self.pc.setLocalDescription(offer)
            
            # Request session token and configuration from local server.
            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:8000/session") as resp:
                    if resp.status != 200:
                        logger.error("Failed to fetch token: %s", await resp.text())
                        raise Exception(f"Token fetch failed: {resp.status}")
                    token_data = await resp.json()
            
            # Extract ephemeral key from the session response.
            ephemeral_key = token_data["client_secret"]["value"]
            
            # Prepare parameters and headers for the SDP exchange with OpenAI.
            params = {"model": self.model}
            headers = {
                "Authorization": f"Bearer {ephemeral_key}",
                "Content-Type": "application/sdp"
            }
            
            # Post the local SDP to OpenAI's realtime endpoint and get the SDP answer.
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}",
                    params=params,
                    data=self.pc.localDescription.sdp,
                    headers=headers,
                ) as resp:
                    if resp.status != 200:
                        logger.error("SDP exchange failed: %s", await resp.text())
                        raise Exception(f"SDP exchange failed: {resp.status}")
                    answer_sdp = await resp.text()
            
            # Set the received SDP answer as the remote description.
            answer = RTCSessionDescription(sdp=answer_sdp, type="answer")
            await self.pc.setRemoteDescription(answer)
            
            # Setup data channel event callbacks.
            @self.data_channel.on("open")
            async def on_open():
                # NOTE: 'voice_instruction' should be obtained from the prompt handler.
                session_update = {
                    "type": "session.update",
                    "session": {
                        "instructions": voice_instruction,  # Use the prompt from handler.
                        "voice": "alloy",
                        "temperature": 0.8,
                        "input_audio_transcription": {"model": "whisper-1"}
                    }
                }
                self.data_channel.send(json.dumps(session_update))

            @self.data_channel.on("message")
            def on_message(message):
                # Invoke the provided callback when a message is received.
                if self.on_message_callback:
                    self.on_message_callback(message)

            @self.pc.on("track")
            def on_track(track):
                # Handle incoming media tracks.
                if track.kind == "audio":
                    self.remote_audio = track
                    # Here you might process remote audio or pass it to a callback.
                    if self.on_message_callback:
                        pass  # Placeholder for additional handling.
                        
        except Exception as e:
            logger.error("Critical error in connecting to OpenAI: %s", str(e))
            raise

    async def push_client_audio(self, frame):
        """
        Push a client audio frame into the custom audio track's queue.
        
        Args:
            frame: The audio frame to be pushed.
        """
        try:
            await self.client_audio_track.push_frame(frame)
        except Exception as e:
            logger.error("Error pushing client audio frame: %s", str(e))

    def set_on_message_callback(self, callback):
        """
        Set the callback function for processing messages received over the data channel.
        
        Args:
            callback: A function to be called with the incoming message.
        """
        self.on_message_callback = callback


# Instantiate the VoiceAgentRTC and begin the connection process.
voice_agent = VoiceAgentRTC()
asyncio.ensure_future(voice_agent.connect())


@app.post("/webrtc/voice")
async def webrtc_voice(request: Request):
    """
    FastAPI endpoint to handle WebRTC voice communication.

    Steps:
      1. Parse the incoming JSON request to retrieve the client's SDP offer.
      2. Create a new RTCPeerConnection for the client.
      3. Set up audio track handling from the client's connection.
      4. If remote audio is available from the voice agent, add it to the client's connection.
      5. Set the client's SDP offer as the remote description, create an SDP answer, and set it as local description.
      6. Return the SDP answer as a JSON response.
    
    Returns:
        JSONResponse containing the SDP answer or an error message.
    """
    try:
        data = await request.json()
        client_offer = data.get("sdp")
        if not client_offer:
            logger.error("No SDP provided in /webrtc/voice request")
            return JSONResponse({"error": "No SDP provided"}, status_code=400)
        
        # Create a new PeerConnection for the client.
        pc_client = RTCPeerConnection()
        
        @pc_client.on("track")
        async def on_client_track(track):
            if track.kind == "audio":
                try:
                    # Continuously receive audio frames and pass them to the voice agent.
                    while True:
                        frame = await track.recv()
                        await voice_agent.push_client_audio(frame)
                except Exception as e:
                    # End loop on exception (e.g., connection close).
                    pass
        
        # If the voice agent already has remote audio, add it to the client's connection.
        if voice_agent.remote_audio:
            pc_client.addTrack(voice_agent.remote_audio)
        
        # Set the client's SDP offer as the remote description.
        offer = RTCSessionDescription(sdp=client_offer, type="offer")
        await pc_client.setRemoteDescription(offer)
        
        # Create an SDP answer for the client.
        answer = await pc_client.createAnswer()
        await pc_client.setLocalDescription(answer)
        
        # Return the SDP answer to the client.
        return JSONResponse({"sdp": pc_client.localDescription.sdp})
    except Exception as e:
        logger.error("Critical error in /webrtc/voice endpoint: %s", str(e))
        return JSONResponse({"error": str(e)}, status_code=500)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
