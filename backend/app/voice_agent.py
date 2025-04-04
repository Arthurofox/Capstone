import os
import json
import logging
import asyncio
import aiohttp

from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack
from aiortc.contrib.media import MediaRelay
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# Load environment variables
load_dotenv()
logger = logging.getLogger("VoiceAgentRTC")

app = FastAPI()
logging.getLogger().setLevel(logging.CRITICAL)
# A custom MediaStreamTrack that we can push audio frames into.
class ClientAudioTrack(MediaStreamTrack):
    kind = "audio"
    
    def __init__(self):
        super().__init__()
        self.queue = asyncio.Queue()
    
    async def recv(self):
        frame = await self.queue.get()
        return frame

    async def push_frame(self, frame):
        await self.queue.put(frame)

class VoiceAgentRTC:
    """
    This class establishes a WebRTC connection with OpenAI’s Realtime API.
    It creates a peer connection (pc_openai) and adds a custom audio track which
    will be fed audio coming from the client.
    """
    def __init__(self, model="gpt-4o-realtime-preview-2024-12-17"):
        self.model = model
        self.api_key = os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not set")
        self.base_url = "https://api.openai.com/v1/realtime"
        self.pc = RTCPeerConnection()
        self.client_audio_track = ClientAudioTrack()
        # Add the custom audio track to the connection to OpenAI.
        self.pc.addTrack(self.client_audio_track)
        self.relay = MediaRelay()
        self.remote_audio = None  # Will be set when a remote track arrives.
        self.on_message_callback = None

    async def connect(self):
        try:
            # Create an SDP offer for the connection with OpenAI.
            offer = await self.pc.createOffer()
            await self.pc.setLocalDescription(offer)
            logger.info("Created local SDP offer for OpenAI connection")
            
            # Fetch an ephemeral token from your token server.
            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:3000/session") as resp:
                    token_data = await resp.json()
            ephemeral_key = token_data["client_secret"]["value"]
            
            # Send the SDP offer to OpenAI’s Realtime API.
            params = {"model": self.model}
            headers = {
                "Authorization": f"Bearer {ephemeral_key}",
                "Content-Type": "application/sdp"
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}",
                    params=params,
                    data=self.pc.localDescription.sdp,
                    headers=headers,
                ) as resp:
                    answer_sdp = await resp.text()
            
            answer = RTCSessionDescription(sdp=answer_sdp, type="answer")
            await self.pc.setRemoteDescription(answer)
            logger.info("Set remote SDP from OpenAI, connection established")
            
            @self.pc.on("track")
            def on_track(track):
                if track.kind == "audio":
                    logger.info("Received remote audio track from OpenAI")
                    self.remote_audio = track
                    if self.on_message_callback:
                        # You can process events/messages here if needed.
                        pass
        except Exception as e:
            logger.error("Error in connecting to OpenAI: %s", str(e))

    async def push_client_audio(self, frame):
        try:
            await self.client_audio_track.push_frame(frame)
        except Exception as e:
            logger.error("Error pushing client audio frame: %s", str(e))
        
    def set_on_message_callback(self, callback):
        self.on_message_callback = callback

# Create a global VoiceAgentRTC instance that connects to OpenAI.
voice_agent = VoiceAgentRTC()
asyncio.ensure_future(voice_agent.connect())

# This endpoint handles SDP exchange from the client.
@app.post("/webrtc/voice")
async def webrtc_voice(request: Request):
    try:
        data = await request.json()
        client_offer = data.get("sdp")
        if not client_offer:
            return JSONResponse({"error": "No SDP provided"}, status_code=400)
        
        # Create a new RTCPeerConnection for the client.
        pc_client = RTCPeerConnection()
        
        @pc_client.on("track")
        async def on_client_track(track):
            if track.kind == "audio":
                logger.info("Received audio track from client")
                try:
                    while True:
                        frame = await track.recv()
                        await voice_agent.push_client_audio(frame)
                except Exception as e:
                    logger.info("Audio track ended or error occurred in receiving frame: %s", str(e))
        
        # If the VoiceAgentRTC has already received remote audio from OpenAI,
        # add it to the client connection so the client can hear the AI.
        if voice_agent.remote_audio:
            pc_client.addTrack(voice_agent.remote_audio)
        
        # Process the client’s SDP offer.
        offer = RTCSessionDescription(sdp=client_offer, type="offer")
        await pc_client.setRemoteDescription(offer)
        
        # Create and set an answer.
        answer = await pc_client.createAnswer()
        await pc_client.setLocalDescription(answer)
        
        # (In a complete implementation, you would also exchange ICE candidates.)
        return JSONResponse({"sdp": pc_client.localDescription.sdp})
    except Exception as e:
        logger.error("Error in /webrtc/voice endpoint: %s", str(e))
        return JSONResponse({"error": str(e)}, status_code=500)
