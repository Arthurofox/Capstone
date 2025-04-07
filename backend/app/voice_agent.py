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

load_dotenv()
logger = logging.getLogger("VoiceAgentRTC")
from app.prompt_handler import CareerAssistantPromptHandler
app = FastAPI()

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
    def __init__(self, model="gpt-4o-realtime-preview-2024-12-17"):
        self.model = model
        self.api_key = os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not set")
        self.base_url = "https://api.openai.com/v1/realtime"
        self.pc = RTCPeerConnection()
        self.client_audio_track = ClientAudioTrack()
        self.pc.addTrack(self.client_audio_track)
        self.relay = MediaRelay()
        self.remote_audio = None
        self.on_message_callback = None
        self.data_channel = self.pc.createDataChannel("oai-events")

    async def connect(self):
        try:
            offer = await self.pc.createOffer()
            await self.pc.setLocalDescription(offer)
            
            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:8000/session") as resp:
                    if resp.status != 200:
                        logger.error("Failed to fetch token: %s", await resp.text())
                        raise Exception(f"Token fetch failed: {resp.status}")
                    token_data = await resp.json()
            ephemeral_key = token_data["client_secret"]["value"]
            
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
                    if resp.status != 200:
                        logger.error("SDP exchange failed: %s", await resp.text())
                        raise Exception(f"SDP exchange failed: {resp.status}")
                    answer_sdp = await resp.text()
            
            answer = RTCSessionDescription(sdp=answer_sdp, type="answer")
            await self.pc.setRemoteDescription(answer)
            
            @self.data_channel.on("open")
            async def on_open():
                session_update = {
                    "type": "session.update",
                    "session": {
                        "instructions": voice_instruction,  # Use the prompt from handler
                        "voice": "alloy",
                        "temperature": 0.8,
                        "input_audio_transcription": {"model": "whisper-1"}
                    }
                }
                self.data_channel.send(json.dumps(session_update))

            @self.data_channel.on("message")
            def on_message(message):
                if self.on_message_callback:
                    self.on_message_callback(message)

            @self.pc.on("track")
            def on_track(track):
                if track.kind == "audio":
                    self.remote_audio = track
                    if self.on_message_callback:
                        pass
        except Exception as e:
            logger.error("Critical error in connecting to OpenAI: %s", str(e))
            raise

    async def push_client_audio(self, frame):
        try:
            await self.client_audio_track.push_frame(frame)
        except Exception as e:
            logger.error("Error pushing client audio frame: %s", str(e))

    def set_on_message_callback(self, callback):
        self.on_message_callback = callback

voice_agent = VoiceAgentRTC()
asyncio.ensure_future(voice_agent.connect())

@app.post("/webrtc/voice")
async def webrtc_voice(request: Request):
    try:
        data = await request.json()
        client_offer = data.get("sdp")
        if not client_offer:
            logger.error("No SDP provided in /webrtc/voice request")
            return JSONResponse({"error": "No SDP provided"}, status_code=400)
        
        pc_client = RTCPeerConnection()
        
        @pc_client.on("track")
        async def on_client_track(track):
            if track.kind == "audio":
                try:
                    while True:
                        frame = await track.recv()
                        await voice_agent.push_client_audio(frame)
                except Exception as e:
                    pass
        
        if voice_agent.remote_audio:
            pc_client.addTrack(voice_agent.remote_audio)
        
        offer = RTCSessionDescription(sdp=client_offer, type="offer")
        await pc_client.setRemoteDescription(offer)
        
        answer = await pc_client.createAnswer()
        await pc_client.setLocalDescription(answer)
        
        return JSONResponse({"sdp": pc_client.localDescription.sdp})
    except Exception as e:
        logger.error("Critical error in /webrtc/voice endpoint: %s", str(e))
        return JSONResponse({"error": str(e)}, status_code=500)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)