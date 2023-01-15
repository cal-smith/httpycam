from aiohttp import web, MultipartWriter
import asyncio
import webcam


async def root(_request):
    """
    ~= index.html
    """
    response = web.Response(headers={"Content-Type": "text/html"})
    response.body = """
        <!DOCTYPE html>
        <html>
            <title>httpycam</title>
        <head>
        </head>
        <body>
            <img src="/frame"/>
        </body>
        </html>
    """

    return response


@webcam.track_frame_requests
async def frame(_request):
    """
    Renders a single frame
    """
    response = web.Response()
    response.body = await webcam.get_frame()
    response.content_type = "image/jpeg"
    return response


@webcam.track_frame_requests
async def stream(request):
    """
    Renders a jpeg multipart stream
    """
    response = web.StreamResponse(
        status=200,
        reason="OK",
        headers={
            "Content-Type": "multipart/x-mixed-replace;boundary=frame",
            "Age": "0",
            "Cache-Control": "no-cache, private",
            "Pragma": "no-cache",
        },
    )
    await response.prepare(request)

    async for frame in webcam.get_frames():
        with MultipartWriter("image/jpeg", boundary="frame") as mpwriter:
            mpwriter.append(
                frame, {"Content-Type": "image/jpeg", "Content-Length": len(frame)}
            )
            try:
                await mpwriter.write(response, close_boundary=False)
            except (ConnectionResetError, BrokenPipeError) as e:
                print(f"error: {e}")
                break
    return response


async def main():
    # create a task to run "in the background"
    frames_task = asyncio.create_task(webcam.get_frames_forever())
    # prevent it from being garbage collected
    asyncio.shield(frames_task)

    app = web.Application()
    app.add_routes(
        [
            web.get("/", root),
            web.get("/frame", frame),
            web.get("/stream", stream),
        ]
    )
    return app


web.run_app(main())
