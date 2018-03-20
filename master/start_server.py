from asyncio import get_event_loop
from logging import debug as d, basicConfig, DEBUG, StreamHandler
from json import loads, dumps
from uuid import uuid4, UUID
from websockets import \
    WebSocketClientProtocol as Connection, \
    ConnectionClosed, \
    serve
from vlc import Instance as VLC
from pathlib import Path


def create_base_message(source: str, type: str, payload: object):
    return dumps({
        "header": {
            "source": source,
            "type": type
        },
        "payload": payload
    }, indent=4)


def from_master(type: str, payload: object):
    return create_base_message("master", type, payload)


def registered_message(uuid: UUID):
    return from_master("Registered", {
        "id": str(uuid)
    })


def start_streaming_message(url):
    return from_master("StartStreaming", {
        "url": url
    })


def get_element(message: object, element: str, tag: str):
    return None \
        if not element in message or not tag in message[element] \
        else message[element][tag]


def get_header_element(message: object, tag: str):
    return get_element(message, "header", tag)


def get_payload_element(message: object, tag: str):
    return get_element(message, "payload", tag)


def message_type(message: object):
    return get_header_element(message, "type")


def message_source(message: object):
    return get_header_element(message, "source")


def message_payload(message: object):
    return None if "payload" not in message else message["payload"]


start_port = 1234

class Client:

    def __init__(self, connection: Connection):
        d("Client connected: {}".format(connection.remote_address))
        self.connection = connection
        self.registered = False
        self.player = None

    async def on_message(self, message: object):
        d("New message: {} from {}".format(message, self.connection.remote_address))
        type = message_type(message)
        if not self.registered:
            if type != "Register":
                await self.connection.close()
                raise ConnectionClosed
            await self.connection.send(registered_message(uuid4()))
            self.registered = True
        else:
            if type == "Stream":
                file = Path(get_payload_element(message, "path"))
                if file.is_file():
                    global start_port
                    port = start_port
                    start_port += 1
                    cmd = [
                        "file://{}".format(file.absolute()),
                        "sout=#duplicate{dst=rtp{dst=127.0.0.1,port=" + str(port) + "}}",
                        "no-sout-rtp-sap",
                        "no-sout-standard-sap",
                        "sout-keep"
                    ]
                    d("start streaming with arguments: {}".format(cmd))
                    vlc = VLC()
                    media = vlc.media_new(*cmd)
                    media.get_mrl()

                    player = vlc.media_player_new()
                    player.set_media(media)
                    player.play()

                    self.player = player
                    await self.connection.send(start_streaming_message("rtp://127.0.0.1:{}".format(port)))
            else:
                # just echo
                await self.connection.send(message)

    async def run(self):
        async for message in self.connection:
            decoded = loads(message)

            if message_source(decoded) != "slave" or not message_type(decoded):
                await self.connection.close()
                raise ConnectionClosed
            await self.on_message(decoded)


async def client_connected(connection: Connection, path):
    try:
        await Client(connection).run()
    except ConnectionClosed:
        d("Client {} closed the connection".format(connection.remote_address))


if __name__ == "__main__":
    basicConfig(level=DEBUG, handlers=[StreamHandler()])

    host = ""
    port = 5678

    try:
        get_event_loop().run_until_complete(serve(client_connected, host, port))
        d("Started game server: {}:{}".format(host, port))
        get_event_loop().run_forever()
    except KeyboardInterrupt:
        d("The game server was shut")
