import asyncio
import websockets
import json
import sys


def build_message(type: str, payload: object = None):
    return json.dumps({
        "header": {
            "source": "slave",
            "type": type,
        },
        "payload": payload
    })


async def hello(uri, file):
    async with websockets.connect(uri) as socket:
        await socket.send(build_message("Register"))
        message = await socket.recv()
        print("Recieved message: {}".format(message))

        if file:
            await socket.send(build_message("Stream", {"path": file}))
            message = await socket.recv()
            print("Recieved message: {}".format(message))


if __name__ == "__main__":
    file = None if len(sys.argv) < 2 else sys.argv[1]
    asyncio.get_event_loop().run_until_complete(hello('ws://localhost:5678', file))
