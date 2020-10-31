import argparse
import asyncio
import json
import logging
logging.basicConfig(level='DEBUG')
import os
import platform
import ssl
import math

import numpy
import cv2

# from aiohttp import web
from starlette.responses import HTMLResponse, JSONResponse, Response
from starlette.applications import Starlette
from starlette.routing import Route

from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from av import VideoFrame
from aiortc.contrib.media import MediaPlayer

ROOT = os.path.dirname(__file__)

from webcam import FlagVideoStreamTrack

async def index(request):
    content = open(os.path.join(ROOT, "index.html"), "r").read()
    return HTMLResponse(content, media_type="text/html")


async def javascript(request):
    content = open(os.path.join(ROOT, "client.js"), "r").read()
    return Response(content, media_type="application/javascript")


async def offer(request):
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    pc = RTCPeerConnection()
    pcs.add(pc)

    @pc.on("iceconnectionstatechange")
    async def on_iceconnectionstatechange():
        print("ICE connection state is %s" % pc.iceConnectionState)
        if pc.iceConnectionState == "failed":
            await pc.close()
            pcs.discard(pc)

    # open media source
    # if args.play_from:
    #     player = MediaPlayer(args.play_from)
    # else:
    #     options = {"framerate": "30", "video_size": "640x480"}
    #     if platform.system() == "Darwin":
    #         player = MediaPlayer("default:none", format="avfoundation", options=options)
    #     else:
    #         player = MediaPlayer("/dev/video0", format="v4l2", options=options)
    #     pass

    await pc.setRemoteDescription(offer)
    # for t in pc.getTransceivers():
    #     if t.kind == "audio" and player.audio:
    #         pc.addTrack(player.audio)
    #     elif t.kind == "video" and player.video:
    #         pc.addTrack(player.video)
        
    for t in pc.getTransceivers():
        if t.kind == "video":
            pc.addTrack(FlagVideoStreamTrack())
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return JSONResponse({"sdp": pc.localDescription.sdp, "type": pc.localDescription.type})


pcs = set()


async def on_shutdown(app):
    # close peer connections
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WebRTC webcam demo")
    parser.add_argument("--play-from", help="Read the media from a file and sent it."),
    parser.add_argument(
        "--host", default="127.0.0.1", help="Host for HTTP server (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port", type=int, default=8080, help="Port for HTTP server (default: 8080)"
    )
    parser.add_argument("--verbose", "-v", action="count")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    app = Starlette(debug=True, routes=[
        Route('/', index),
        Route("/client.js", javascript),
        Route("/offer", offer, methods=['GET', 'POST']),
    ], on_shutdown=[on_shutdown])
    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port)
