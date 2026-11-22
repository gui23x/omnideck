import asyncio
import json
import logging
import socket
import sys
import threading
from collections.abc import Callable

from evdev import AbsInfo, UInput, ecodes as e
import websockets

BROADCAST_PORT = 5000
WEBSOCKET_PORT = 8080
DEVICE_NAME = "Microsoft X-Box 360 pad"
logger = logging.getLogger(__name__)

ABS_RANGE_STICK = AbsInfo(
    value=0, min=-32768, max=32767, fuzz=16, flat=128, resolution=0
)
ABS_RANGE_TRIGGER = AbsInfo(value=0, min=0, max=255, fuzz=0, flat=0, resolution=0)
ABS_RANGE_DPAD = AbsInfo(value=0, min=-1, max=1, fuzz=0, flat=0, resolution=0)

CAPABILITIES = {
    e.EV_KEY: [
        e.BTN_SOUTH,
        e.BTN_EAST,
        e.BTN_NORTH,
        e.BTN_WEST,
        e.BTN_TL,
        e.BTN_TR,
        e.BTN_SELECT,
        e.BTN_START,
        e.BTN_MODE,
        e.BTN_THUMBL,
        e.BTN_THUMBR,
    ],
    e.EV_ABS: [
        (e.ABS_X, ABS_RANGE_STICK),
        (e.ABS_Y, ABS_RANGE_STICK),
        (e.ABS_RX, ABS_RANGE_STICK),
        (e.ABS_RY, ABS_RANGE_STICK),
        (e.ABS_Z, ABS_RANGE_TRIGGER),
        (e.ABS_RZ, ABS_RANGE_TRIGGER),
        (e.ABS_HAT0X, ABS_RANGE_DPAD),
        (e.ABS_HAT0Y, ABS_RANGE_DPAD),
    ],
}

BUTTON_MAP = {
    "BTN_A": e.BTN_SOUTH,
    "BTN_B": e.BTN_EAST,
    "BTN_X": e.BTN_WEST,
    "BTN_Y": e.BTN_NORTH,
    "BTN_NORTH": e.BTN_NORTH,
    "BTN_SOUTH": e.BTN_SOUTH,
    "BTN_EAST": e.BTN_EAST,
    "BTN_WEST": e.BTN_WEST,
    "BTN_TL": e.BTN_TL,
    "BTN_TR": e.BTN_TR,
    "BTN_SELECT": e.BTN_SELECT,
    "BTN_START": e.BTN_START,
    "BTN_MODE": e.BTN_MODE,
    "BTN_THUMBL": e.BTN_THUMBL,
    "BTN_THUMBR": e.BTN_THUMBR,
}


def create_virtual_pad():
    try:
        return UInput(
            CAPABILITIES,
            name=DEVICE_NAME,
            vendor=0x045E,
            product=0x028E,
            version=0x110,
            bustype=0x03,
        )
    except Exception as ex:
        print(f"UInput error: {ex}")
        sys.exit(1)


def get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 1))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


class ServerThread(threading.Thread):
    def __init__(self, on_status: Callable[[str], None], virtual_pad: UInput):
        super().__init__(name="OmniDeckServer", daemon=True)
        self._on_status = on_status
        self.ui = virtual_pad
        self._running = threading.Event()
        self._running.set()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._stop_event: asyncio.Event | None = None

    def run(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._stop_event = asyncio.Event()
        if not self._running.is_set():
            self._stop_event.set()

        threading.Thread(
            target=self._broadcast_presence,
            name="OmniDeckPresence",
            daemon=True,
        ).start()
        try:
            self._loop.run_until_complete(self._run_server())
        except Exception:
            logger.exception("The OmniDeck server stopped unexpectedly")
        finally:
            self._loop.close()

    async def _run_server(self):
        async with websockets.serve(self._handle_client, "0.0.0.0", WEBSOCKET_PORT):
            await self._stop_event.wait()

    def _broadcast_presence(self):
        udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        payload = json.dumps(
            {
                "name": "Xbox 360 Controller",
                "ip": get_local_ip(),
                "port": WEBSOCKET_PORT,
                "type": "volant_server",
            }
        ).encode()
        while self._running.is_set():
            try:
                udp.sendto(payload, ("<broadcast>", BROADCAST_PORT))
                self._running.wait(2)
            except OSError:
                logger.exception("Unable to broadcast server presence")
                self._running.wait(5)
        udp.close()

    async def _handle_client(self, websocket):
        self._on_status("Sucesso")
        is_running = False
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    code_str = data.get("code")
                    value = int(data.get("value", 0))
                    msg_type = data.get("type")
                except (json.JSONDecodeError, TypeError, ValueError) as ex:
                    logger.warning("Ignoring invalid controller input: %s", ex)
                    continue

                if not isinstance(code_str, str):
                    continue

                if msg_type == "key":
                    code = BUTTON_MAP.get(code_str) or getattr(e, code_str, None)
                    if code is None:
                        continue
                    self.ui.write(e.EV_KEY, code, value)
                elif msg_type == "abs":
                    code = getattr(e, code_str, None)
                    if code is None:
                        continue
                    self.ui.write(
                        e.EV_ABS,
                        code,
                        (
                            int((value / 255.0) * 32767)
                            if code in (e.ABS_X, e.ABS_Y, e.ABS_RX, e.ABS_RY)
                            else value
                        ),
                    )
                else:
                    continue

                self.ui.syn()
                if not is_running:
                    is_running = True
                    self._on_status("Rodando...")
        except Exception:
            logger.exception("Controller connection failed")
        finally:
            self._on_status("Não conectado")

    def stop(self):
        self._running.clear()
        if self._loop and self._stop_event:
            if self._loop.is_running():
                self._loop.call_soon_threadsafe(self._stop_event.set)
            elif not self._loop.is_closed():
                self._stop_event.set()
