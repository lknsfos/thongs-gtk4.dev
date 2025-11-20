import gi
import sys
import os
import signal
import atexit
import logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')
# --- Strict version check ---
try:
    gi.require_version('Gtk', '4.0')
    gi.require_version('Adw', '1')
    gi.require_version('Vte', '3.91')
    gi.require_version('Secret', '1') # ✨ For secure password storage
except ValueError as e:
    logging.basicConfig(level=logging.CRITICAL)
    logging.critical(f"Error: Required libraries not found. {e}")
    logging.critical("Please ensure you have gir1.2-gtk-4.0, gir1.2-adw-1, and gir1.2-vte-3.91 installed.")
    logging.shutdown() # Ensure logs are flushed before exit
    sys.exit(1)

from gi.repository import Adw, Gio, Gtk, GdkPixbuf
from .window import ThongSSHWindow # Keep relative import
from .constants import APP_ID, resource_path # Import our new function

# --- Application Class ---
class ThongSSHApp(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(application_id=APP_ID, **kwargs)
        # ✨ Register resources in the constructor, BEFORE creating the window
        try:
            res_path = resource_path("thongssh.gresource") # Use the helper function
            Gio.resources_register(Gio.Resource.load(res_path))
        except gi.repository.GLib.GError:
            logging.debug("Resources already registered, skipping.")
        self.connect('activate', self.on_activate)

    def on_activate(self, app):
        # If the window doesn't exist yet, create it.
        if not self.props.active_window:
            self.win = ThongSSHWindow(application=self)
        # Present the window. This ensures it's shown correctly on subsequent activations.
        self.props.active_window.present()


def main():
    # ✨ Configure logging
    # Use DEBUG level to see everything, or INFO for important messages only
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s - %(levelname)s - %(message)s')

    @atexit.register
    def kill_all_sessions():
        logging.info("Exiting... Killing all active sessions.")
        for term, pid in ThongSSHWindow.open_sessions.values():
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            except TypeError:
                logging.warning(f"Cannot kill PID: {pid}, it's not an int")

    app = ThongSSHApp()
    return app.run(sys.argv)

if __name__ == '__main__':
    exit_status = main()
    sys.exit(exit_status)