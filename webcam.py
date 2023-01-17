import imageio.v3 as iio
import asyncio
import configparser
from collections import defaultdict

current_frame = defaultdict(lambda: None)
current_frame_requests = defaultdict(int)

async def get_all_frames_forever():
    """
    Set up background workers for all configured cameras
    """
    config = configparser.ConfigParser(allow_no_value=True)
    config.read("config.ini")
    camera_ids = [id for id, _ in config.items("cameras")]
    for id in camera_ids:
        # create a task to run "in the background"
        frames_task = asyncio.create_task(get_frames_forever(id))
        # prevent it from being garbage collected
        asyncio.shield(frames_task)


async def get_frames_forever(video_device):
    """
    Gets frames from the specified video device.
    Trys to shut down the webcam stream when possible by tracking the
    current number of requests that need frames (via @track_frame_requests).
    """
    global current_frame
    global current_frame_requests
    while True:
        if current_frame_requests[video_device] > 0:
            for frame in iio.imiter(f"<{video_device}>"):
                if current_frame_requests[video_device] <= 0:
                    # make sure that we dont underflow the counter
                    current_frame_requests[video_device] = 0
                    # clear out the frame so that any future requests start fresh
                    current_frame[video_device] = None
                    break
                current_frame[video_device] = iio.imwrite("<bytes>", frame, extension=".jpeg")
                await asyncio.sleep(0.01)
        await asyncio.sleep(0.1)


async def get_frames(video_device):
    """
    Infinite generator that returns the current image produced by get_frames_forever
    """
    # wait for a frame to exist (if one doesnt already)
    while not current_frame[video_device]:
        await asyncio.sleep(0.1)
    # yield frames as fast as we can
    # (some sleep to allow other tasks to run/not lock up the whole server)
    while True:
        yield current_frame[video_device]
        await asyncio.sleep(0.01)


async def get_frame(video_device):
    """
    Returns a single frame from the webcam stream
    """
    async for frame in get_frames(video_device):
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
        current_frame_requests[request.match_info["video_device"]] += 1
        resp = await f(request)
        current_frame_requests[request.match_info["video_device"]] -= 1
        return resp

    return wrap_request
