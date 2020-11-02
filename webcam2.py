import argparse
import asyncio
import logging
logging.basicConfig(level='DEBUG')
import os

import numpy as np

from starlette.responses import HTMLResponse, JSONResponse, Response
from starlette.applications import Starlette
from starlette.routing import Route

from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from av import VideoFrame

ROOT = os.path.dirname(__file__)

class DemoVideoStreamTrack(VideoStreamTrack):
    """
    A video track that returns a demo.
    """

    def __init__(self):
        super().__init__()  # don't forget this!
        self.counter = 0
        height, width = 480, 640

        # generate flag
        self.nframes = 60
        data_bgr = np.zeros((height, width, 3), dtype=np.uint8)
        yy, xx = np.indices(data_bgr.shape[:2])
        xx = 2 * np.pi * xx / width

        self.frames = []
        for i in range(self.nframes):
            phase = (i / self.nframes) * 2 * np.pi
            data_bgr[:,:,0] = 255 * (np.cos(xx + phase) / 2)
            data_bgr[:,:,1] = 255 * (np.cos(xx + phase) / 2)
            data_bgr[:,:,2] = 255 * (np.cos(xx + phase) / 2)
            self.frames.append(VideoFrame.from_ndarray(data_bgr, format="bgr24"))

    async def recv(self):
        pts, time_base = await self.next_timestamp()

        frame = self.frames[self.counter % self.nframes]
        frame.pts = pts
        frame.time_base = time_base
        self.counter += 1
        return frame


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
    print(pcs)

    @pc.on("iceconnectionstatechange")
    async def on_iceconnectionstatechange():
        print("ICE connection state is %s" % pc.iceConnectionState)
        if pc.iceConnectionState == "failed":
            await pc.close()
            pcs.discard(pc)

    await pc.setRemoteDescription(offer)

    for t in pc.getTransceivers():
        if t.kind == "video":
            pc.addTrack(DemoVideoStreamTrack())
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return JSONResponse({"sdp": pc.localDescription.sdp, "type": pc.localDescription.type})


pcs = set()


async def on_shutdown(app):
    # close peer connections
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()

app = Starlette(debug=True, routes=[
    Route('/', index),
    Route("/client.js", javascript),
    Route("/offer", offer, methods=['GET', 'POST']),
], on_shutdown=[on_shutdown])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WebRTC webcam demo")
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

    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port)
