import asyncio
import json
from enum import Enum
import vlc

import websockets

register_msg = {'header': {'source': 'slave',
                           'action': 'Register'},
                'payload': {}}


class AppState(Enum):
    REGISTERED = 0
    NOT_REGISTERED = 1


app_state = AppState.REGISTERED


def handle_register(data):
    print('HANDLE_REGISTER')


def handle_stream_started(data):
    print('HANDLE_STREAM_STARTED')
    i = vlc.Instance('--verbose 2'.split())
    player = i.media_player_new()
    media = i.media_new(data['payload']['mrl'])
    player.set_media(media)
    player.play()


def consumer(_message):
    print("< {}".format(_message))
    json_data = json.loads(_message)

    if json_data['header']['action'] == 'Register':
        handle_register(json_data)

    if json_data['header']['action'] == 'StreamStarted':
        handle_stream_started(json_data)


async def receiver(_ws):
    async with websockets.connect(_ws) as websocket:
        str = json.dumps(register_msg)
        await websocket.send(str)
        print("> {}".format(str))

        while True:
            message = await websocket.recv()
            consumer(message)


ws = input("ws: ")
if len(ws) == 0:
    ws = "ws://localhost:8765"

asyncio.get_event_loop().run_until_complete(receiver(ws))
