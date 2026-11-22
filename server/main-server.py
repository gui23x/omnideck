#!/usr/bin/env python3
import sys
import os
import subprocess
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk

# Insere o diretório base para resolver os imports de forma universal
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from server.core import ServerThread, create_virtual_pad, get_local_ip


def check_root():
    if os.geteuid() != 0:
        cmd = [
            "pkexec",
            "env",
            f'DISPLAY={os.environ.get("DISPLAY", ":0")}',
            f'XAUTHORITY={os.environ.get("XAUTHORITY", "")}',
            sys.executable,
            os.path.abspath(sys.argv[0]),
        ]
        try:
            subprocess.check_call(cmd)
        except subprocess.CalledProcessError:
            pass
        sys.exit(0)


check_root()


class OmniDeckWindow(Gtk.Window):
    def __init__(self, virtual_pad):
        super().__init__()
        self.set_title("OmniDeck Server")
        self.set_default_size(380, 180)
        self.set_position(Gtk.WindowPosition.CENTER)

        self._status_label = Gtk.Label()
        self._status_label.set_justify(Gtk.Justification.CENTER)
        self._status_label.set_xalign(0.5)
        self._status_label.set_yalign(0.5)
        self._status_label.set_line_wrap(True)
        self.add(self._status_label)

        self._last_status = None
        self._ip_address = get_local_ip()
        self._set_status("Não conectado")
        self._server = ServerThread(self._queue_status, virtual_pad)
        self.connect("destroy", self._on_destroy)
        self._server.start()

    def _queue_status(self, status: str):
        GLib.idle_add(self._set_status, status)

    def _set_status(self, status: str):
        if status != self._last_status:
            self._last_status = status
            ip = GLib.markup_escape_text(f"IP: {self._ip_address}")
            state = GLib.markup_escape_text(status)
            if status == "Rodando...":
                state = f'<span foreground="#3584e4">{state}</span>'
            self._status_label.set_markup(f"{ip}\n{state}")
        return GLib.SOURCE_REMOVE

    def _on_destroy(self, _window):
        self._server.stop()
        self._server.join(timeout=3)


if __name__ == "__main__":
    virtual_pad = create_virtual_pad()
    win = OmniDeckWindow(virtual_pad)
    win.connect("destroy", lambda _window: Gtk.main_quit())
    win.show_all()
    Gtk.main()
    virtual_pad.close()
