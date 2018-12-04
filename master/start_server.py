from asyncio import get_event_loop, sleep
from logging import debug as d, basicConfig, DEBUG, StreamHandler
from json import loads, dumps
from uuid import uuid4, UUID

from aiogram.utils import executor, context
from aiogram.utils.executor import _startup
from websockets import \
    WebSocketClientProtocol as Connection, \
    ConnectionClosed, \
    serve
from vlc import Instance as VLC
from pathlib import Path

from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher


# t.me/hobgoblin_testbot
bot = Bot(token='592793492:AAH92wmIF-_hN2k9DoHlWjyAGlKpbEqEcrY')
dp = Dispatcher(bot)


@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    await message.reply("Hi!\nI'm Hobgoblin!\nType /audio <path_to_file> for streaming.")


@dp.message_handler(commands=['startstream', 'stream', 'audio'])
async def start_stream(message: types.Message):
    path = message.get_args()
    for client in clients:
        await client.start_stream(path)
    await message.reply("Starting audio stream... file:{}".format(path))


def create_base_message(source: str, type: str, payload: object):
    return dumps({
        "header": {
            "source": source,
            "action": type
        },
        "payload": payload
    }, indent=4)


def from_master(type: str, payload: object = None):
    return create_base_message("master", type, payload)


def registered_message(uuid: UUID):
    return from_master("Registered", {
        "id": str(uuid)
    })


def start_streaming_message(url):
    return from_master("StartStreaming", {
        "mrl": url
    })


def error_message():
    return from_master("UnexpectedMessage")


def get_element(message: object, element: str, tag: str):
    return None \
        if not element in message or not tag in message[element] \
        else message[element][tag]


def get_header_element(message: object, tag: str):
    return get_element(message, "header", tag)


def get_payload_element(message: object, tag: str):
    return get_element(message, "payload", tag)


def message_type(message: object):
    return get_header_element(message, "action")


def message_source(message: object):
    return get_header_element(message, "source")


def message_payload(message: object):
    return None if "payload" not in message else message["payload"]


def start_streaming_player(port: int, file: str):
    cmd = [
        "file://{}".format(file),
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

    return player


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
                    port = start_port
                    start_port += 1
                    self.player = start_streaming_player(port, file.absolute())
                    await self.connection.send(start_streaming_message("rtp://127.0.0.1:{}".format(port)))
                else:
                    await self.connection.send(error_message())
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

    async def start_stream(self, path):
        file = Path(path)
        if file.is_file():
            global start_port
            port = start_port
            start_port += 1
            self.player = start_streaming_player(port, file.absolute())
            await self.connection.send(start_streaming_message("rtp://127.0.0.1:{}".format(port)))
        else:
            await self.connection.send(error_message())


clients = []


async def client_connected(connection: Connection, path):
    try:
        cl = Client(connection)
        clients.append(cl)
        await cl.run()
    except ConnectionClosed:
        d("Client {} closed the connection".format(connection.remote_address))


if __name__ == '__main__':
    basicConfig(level=DEBUG, handlers=[StreamHandler()])

    get_event_loop().set_task_factory(context.task_factory)
    host = ""
    port = 5678

    try:

        get_event_loop().run_until_complete(_startup(dp, None, None))
        d("Started telegram bot")

        get_event_loop().create_task(dp.start_polling(reset_webhook=True))

        get_event_loop().run_until_complete(serve(client_connected, host, port))
        d("Started master instance at {}:{}".format(host, port))

        get_event_loop().run_forever()
    except KeyboardInterrupt:
        d("The master instance was shut")
