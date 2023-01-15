import imageio.v3 as iio
import asyncio

# /dev/videoN
VIDEO_DEVICE = "video1"


current_frame = None
current_frame_requests = 0


async def get_frames_forever():
    """
    Gets frames from the specified video device.
    Trys to shut down the webcam stream when possible by tracking the
    current number of requests that need frames (via @track_frame_requests).
    """
    global current_frame
    global current_frame_requests
    while True:
        if current_frame_requests > 0:
            for frame in iio.imiter(f"<{VIDEO_DEVICE}>"):
                if current_frame_requests <= 0:
                    # make sure that we dont underflow the counter
                    current_frame_requests = 0
                    # clear out the frame so that any future requests start fresh
                    current_frame = None
                    break
                current_frame = iio.imwrite("<bytes>", frame, extension=".jpeg")
                await asyncio.sleep(0.01)
        await asyncio.sleep(0.1)


async def get_frames():
    """
    Infinite generator that returns the current image produced by get_frames_forever
    """
    # wait for a frame to exist (if one doesnt already)
    while not current_frame:
        await asyncio.sleep(0.1)
    # yield frames as fast as we can
    # (some sleep to allow other tasks to run/not lock up the whole server)
    while True:
        yield current_frame
        await asyncio.sleep(0.01)


async def get_frame():
    """
    Returns a single frame from the webcam stream
    """
    async for frame in get_frames():
        return frame


def track_frame_requests(f):
    """
    Tracks the number of in-flight requests that need access to
    video device resources to try and optimize system resources/prevent overheating
    """

    async def wrap_request(request):
        """
        Inner coroutine to process the request, and inc/dec the counter
        """
        global current_frame_requests
        current_frame_requests += 1
        resp = await f(request)
        current_frame_requests -= 1
        return resp

    return wrap_request
