
from vlc import Instance as VLC
from pathlib import Path
from sys import argv


if len(argv) > 1:
    file = Path(argv[1])
    if file.is_file():
        cmd = [
            "file://{}".format(file.absolute()),
            "sout=#duplicate{dst=rtp{dst=127.0.0.1,port=1234}}",
            "no-sout-rtp-sap",
            "no-sout-standard-sap",
            "sout-keep"
        ]
        print("start streaming with arguments: {}".format(cmd))
        vlc = VLC()
        media = vlc.media_new(*cmd)
        print(media.get_mrl())

        player = vlc.media_player_new()
        player.set_media(media)
        player.play()

