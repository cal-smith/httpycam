from aiohttp import web, MultipartWriter
import asyncio
import webcam
import configparser
import os
import shutil

config = configparser.ConfigParser(allow_no_value=True)
# borrowing from https://stackoverflow.com/a/53222876
configpath = os.path.join(
    os.environ.get('APPDATA') or
    os.environ.get('XDG_CONFIG_HOME') or
    os.path.join(os.environ['HOME'], '.config'),
    "httpycam"
)
os.makedirs(configpath, exist_ok=True)
config.read(os.path.join(configpath, "config.ini"))

# no config yet, write a default one
if len(config.sections()) == 0:
    shutil.copy("config.ini", configpath)
    config.read(os.path.join(configpath, "config.ini"))

async def root(_request):
    """
    ~= index.html
    """

    def get_camera_html(id):
        return f"""
            <p>
                <code>{id}</code>
                (<a href="/{id}/frame">frame</a> | <a href="/{id}/stream">stream</a>)
            </p>
            <img src="/{id}/frame" style="max-width: 500px;"/>
        """

    camera_ids = [id for id, _ in config.items("cameras")]
    response = web.Response(headers={"Content-Type": "text/html"})
    response.body = f"""
        <!DOCTYPE html>
        <html>
            <title>httpycam</title>
        <head>
        </head>
        <body>
            {"".join([get_camera_html(id) for id in camera_ids])}
        </body>
        </html>
    """

    return response


@webcam.track_frame_requests
async def frame(request):
    """
    Renders a single frame
    """
    response = web.Response()
    response.body = await webcam.get_frame(request.match_info["video_device"])
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

    async for frame in webcam.get_frames(request.match_info["video_device"]):
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
    frames_task = asyncio.create_task(webcam.get_all_frames_forever())
    # prevent it from being garbage collected
    asyncio.shield(frames_task)

    app = web.Application()
    app.add_routes(
        [
            web.get("/", root),
            web.get("/{video_device}/frame", frame),
            web.get("/{video_device}/stream", stream),
        ]
    )
    return app


web.run_app(main())
