import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')
from gi.repository import Gtk, Gdk, GLib, Gio
from gi.repository import GObject # Import GObject for custom sort functions
import os
from pathlib import Path
import datetime
import stat
import logging
import threading
import tempfile
import queue

from .settings import SettingsManager
from .keyring import KeyringManager
from .dialogs import InputDialog, PermissionsDialog, MessageDialog # MessageDialog for delete confirmation

# Attempt to import paramiko
IS_PARAMIKO_AVAILABLE = False
try:
    import paramiko
    IS_PARAMIKO_AVAILABLE = True
except ImportError:
    logging.warning("SFTP functionality is disabled. Please install 'paramiko' (`pip install paramiko`).")

# Placeholder for future internationalization (i18n)
_ = lambda s: s

# --- Constants for the local file list store ---
(
    COL_ICON,
    COL_NAME,
    COL_SIZE_STR,
    COL_SIZE_BYTES, # For sorting
    COL_PERMS_STR,
    COL_PERMS_MODE, # For chmod (integer mode)
    COL_MODIFIED_STR,
    COL_MODIFIED_TS, # For sorting
    COL_IS_DIR,
    COL_FULL_PATH
) = range(10)


class SftpWidget(Gtk.Box):
    """
    A dual-pane SFTP file manager widget.
    """
    def __init__(self, host_config):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.host_config = host_config
        self.settings = SettingsManager()

        # ✨ Set initial local path from settings
        default_path_str = self.settings.get("sftp.local_default_path")
        default_path = Path(default_path_str.replace("~", str(Path.home()))).resolve()
        if default_path.is_dir():
            self.current_local_path = str(default_path)
        else:
            self.current_local_path = str(Path.home())

        self.keyring = KeyringManager()

        # SFTP connection state
        self.ssh_client = None
        self.sftp_client = None
        self.current_remote_path = None
        self.ui_queue = queue.Queue() # For thread-safe UI updates

        # ✨ For remote file editing
        self.temp_dir = tempfile.mkdtemp(prefix="thongssh_sftp_")
        self.file_monitors = {} # {local_temp_path: (monitor, remote_path)}
        self._log_message(f"Created temporary directory for remote editing: {self.temp_dir}")

        # --- ABSOLUTELY FIXED 50/50 LAYOUT ---
        # A homogeneous Gtk.Box forces its children to be the same size. No sliders, no exceptions.
        # [ Homogeneous Box: [Frame: Local] | [Frame: Remote] ]
        # [ Box: Button > | Button < ]
        # [ Log Panel             ]

        # 1. A horizontal box that will hold the two panels.
        panels_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, vexpand=True, hexpand=True)
        panels_box.set_homogeneous(True) # This is the key: force equal size for all children.
        self.append(panels_box)

        # 2. The left panel (Local File Manager).
        local_panel = self._create_local_panel()
        panels_box.append(local_panel)

        # 3. The right panel (Remote).
        right_panel = self._create_remote_panel()
        panels_box.append(right_panel)
        
        # Initial load
        self._load_local_directory(self.current_local_path)

        # 4. A centered box for the transfer buttons.
        self.button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, vexpand=False, hexpand=False, halign=Gtk.Align.CENTER)
        self.button_box.set_sensitive(False) # Disabled until connection is established
        self.append(self.button_box)
        upload_button = Gtk.Button(label=">")
        upload_button.connect("clicked", self.on_upload_clicked)
        upload_button.set_tooltip_text(_("Upload selected to remote"))
        download_button = Gtk.Button(label="<")
        download_button.set_tooltip_text(_("Download selected to local"))
        download_button.connect("clicked", self.on_download_clicked)
        self.button_box.append(upload_button)
        self.button_box.append(download_button)

        # 5. The log panel at the bottom.
        # ✨ Remove the "Log" label from the frame.
        log_frame = Gtk.Frame(height_request=100, vexpand=False)
        log_scrolled = Gtk.ScrolledWindow()
        log_scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.log_view = Gtk.TextView(editable=False, cursor_visible=False)
        log_scrolled.set_child(self.log_view)
        log_frame.set_child(log_scrolled)
        self.append(log_frame)

        # Start the connection process
        self.setup_actions_and_popovers()
        self._connect_sftp()
        GLib.timeout_add(100, self._process_ui_queue)
        self.connect("unrealize", self.on_widget_destroy)

    def _create_local_panel(self):
        """Builds the entire local file manager widget."""
        frame = Gtk.Frame(label=_("Local"))
        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, margin_top=6, margin_bottom=6, margin_start=6, margin_end=6)
        frame.set_child(main_vbox)

        # Toolbar
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        up_button = Gtk.Button(icon_name="go-up-symbolic")
        up_button.connect("clicked", self.on_local_up_clicked)
        self.local_path_entry = Gtk.Entry()
        self.local_path_entry.set_hexpand(True) # Allow the entry to fill the space
        self.local_path_entry.connect("activate", self.on_local_path_activated)
        toolbar.append(up_button)
        toolbar.append(self.local_path_entry)
        main_vbox.append(toolbar)

        # TreeView for files
        scrolled_window = Gtk.ScrolledWindow(vexpand=True)
        scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        main_vbox.append(scrolled_window)

        # ✨ Correctly define the ListStore with all 9 columns for data and sorting.
        self.local_store = Gtk.ListStore(str, str, str, GObject.TYPE_INT64, str, int, str, GObject.TYPE_INT64, bool, str)
        # Wrap the store in a sortable model to enable column header clicking.
        self.local_sortable_model = Gtk.TreeModelSort(model=self.local_store)
        self.local_view = Gtk.TreeView(model=self.local_sortable_model)
        self.local_view.connect("row-activated", self.on_local_row_activated)

        scrolled_window.set_child(self.local_view)

        # Columns
        column_definitions = [
            (_("Name"), COL_NAME),
            (_("Size"), COL_SIZE_BYTES),
            (_("Date Modified"), COL_MODIFIED_TS),
            (_("Permissions"), None) # Permissions column is not directly sortable
        ]

        # ✨ Add Backspace key press handler for navigating up
        key_controller = Gtk.EventControllerKey.new()
        key_controller.connect("key-pressed", self.on_local_view_key_pressed)
        self.local_view.add_controller(key_controller)

        for i, (col_title, sort_col_id) in enumerate(column_definitions):
            column = Gtk.TreeViewColumn(col_title)
            column.set_resizable(True)
            column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)

            # Set up sorting for the column
            if sort_col_id is not None:
                column.set_sort_column_id(sort_col_id)

            if i == 0: # Name column with icon and text
                column.set_fixed_width(250)
                icon_renderer = Gtk.CellRendererPixbuf()
                text_renderer = Gtk.CellRendererText()
                column.pack_start(icon_renderer, False)
                column.pack_start(text_renderer, True) # Text renderer expands
                column.add_attribute(icon_renderer, "icon-name", COL_ICON) # Icon from COL_ICON
                column.add_attribute(text_renderer, "text", COL_NAME) # Text from COL_NAME
                column.set_expand(True) # Make this column fill available space
            else: # Other columns with only text
                text_renderer = Gtk.CellRendererText()
                column.pack_start(text_renderer, True)
                # Link renderer to the correct display column
                if i == 1: # Size
                    column.set_fixed_width(80)
                    column.add_attribute(text_renderer, "text", COL_SIZE_STR)
                elif i == 2: # Date
                    column.set_fixed_width(140)
                    column.add_attribute(text_renderer, "text", COL_MODIFIED_STR)
                elif i == 3: # Permissions
                    column.set_fixed_width(100)
                    column.add_attribute(text_renderer, "text", COL_PERMS_STR)

            self.local_view.append_column(column)

        # ✨ Set initial sort order from settings
        sort_col_map = {"name": COL_NAME, "size": COL_SIZE_BYTES, "date": COL_MODIFIED_TS}
        sort_dir_map = {"asc": Gtk.SortType.ASCENDING, "desc": Gtk.SortType.DESCENDING}
        sort_col = sort_col_map.get(self.settings.get("sftp.local_default_sort_column"), COL_NAME)
        sort_dir = sort_dir_map.get(self.settings.get("sftp.local_default_sort_direction"), Gtk.SortType.ASCENDING)
        self.local_sortable_model.set_sort_column_id(sort_col, sort_dir)

        # ✨ Connect right-click gesture
        right_click_gesture = Gtk.GestureClick.new()
        right_click_gesture.set_button(Gdk.BUTTON_SECONDARY)
        right_click_gesture.connect("pressed", self.on_view_right_click, self.local_view)
        self.local_view.add_controller(right_click_gesture)

        return frame

    def _create_remote_panel(self):
        """Builds the entire remote file manager widget."""
        frame = Gtk.Frame(label=_("Remote: {host}").format(host=self.host_config.get('name', '')))
        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, margin_top=6, margin_bottom=6, margin_start=6, margin_end=6)
        frame.set_child(main_vbox)

        # Toolbar
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        up_button = Gtk.Button(icon_name="go-up-symbolic")
        up_button.connect("clicked", self.on_remote_up_clicked)
        self.remote_path_entry = Gtk.Entry()
        self.remote_path_entry.set_hexpand(True)
        self.remote_path_entry.connect("activate", self.on_remote_path_activated)
        toolbar.append(up_button)
        toolbar.append(self.remote_path_entry)
        main_vbox.append(toolbar)

        # TreeView for files
        scrolled_window = Gtk.ScrolledWindow(vexpand=True)
        scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        main_vbox.append(scrolled_window)

        self.remote_store = Gtk.ListStore(str, str, str, GObject.TYPE_INT64, str, int, str, GObject.TYPE_INT64, bool, str)
        self.remote_sortable_model = Gtk.TreeModelSort(model=self.remote_store)
        self.remote_view = Gtk.TreeView(model=self.remote_sortable_model)
        self.remote_view.connect("row-activated", self.on_remote_row_activated)
        scrolled_window.set_child(self.remote_view)

        # ✨ Add Backspace key press handler for navigating up on remote panel
        key_controller = Gtk.EventControllerKey.new()
        key_controller.connect("key-pressed", self.on_remote_view_key_pressed)
        self.remote_view.add_controller(key_controller)

        # ✨ Connect right-click gesture
        right_click_gesture = Gtk.GestureClick.new()
        right_click_gesture.set_button(Gdk.BUTTON_SECONDARY)
        right_click_gesture.connect("pressed", self.on_view_right_click, self.remote_view)
        self.remote_view.add_controller(right_click_gesture)

        # Columns (identical to local panel)
        column_definitions = [
            (_("Name"), COL_NAME), (_("Size"), COL_SIZE_BYTES),
            (_("Date Modified"), COL_MODIFIED_TS), (_("Permissions"), None) # Permissions column is not sortable
        ]
        # ✨ Use a different variable name to avoid overwriting the _ function
        for i, (col_title, sort_col_id) in enumerate(column_definitions):
            column = Gtk.TreeViewColumn(col_title)
            column.set_resizable(True)
            column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
            if sort_col_id is not None:
                column.set_sort_column_id(sort_col_id)

            if i == 0: # Name column
                column.set_fixed_width(250)
                column.pack_start(Gtk.CellRendererPixbuf(), False)
                column.pack_start(Gtk.CellRendererText(), True)
                column.add_attribute(column.get_cells()[0], "icon-name", COL_ICON)
                column.add_attribute(column.get_cells()[1], "text", COL_NAME)
                column.set_expand(True) # Make this column fill available space
            else: # Other columns
                renderer = Gtk.CellRendererText()
                column.pack_start(renderer, True)
                if i == 1: # Size
                    column.set_fixed_width(80)
                    column.add_attribute(renderer, "text", COL_SIZE_STR)
                elif i == 2: # Date
                    column.set_fixed_width(140)
                    column.add_attribute(renderer, "text", COL_MODIFIED_STR)
                elif i == 3: # Permissions
                    column.set_fixed_width(100)
                    column.add_attribute(renderer, "text", COL_PERMS_STR)
            self.remote_view.append_column(column)

        # ✨ Set initial sort order from settings for remote panel
        sort_col_map = {"name": COL_NAME, "size": COL_SIZE_BYTES, "date": COL_MODIFIED_TS}
        sort_dir_map = {"asc": Gtk.SortType.ASCENDING, "desc": Gtk.SortType.DESCENDING}
        sort_col = sort_col_map.get(self.settings.get("sftp.remote_default_sort_column"), COL_NAME)
        sort_dir = sort_dir_map.get(self.settings.get("sftp.remote_default_sort_direction"), Gtk.SortType.ASCENDING)
        self.remote_sortable_model.set_sort_column_id(sort_col, sort_dir)

        return frame

    def _load_local_directory(self, path):
        """Populates the local file view with the contents of the given path."""
        self.local_store.clear()
        self.current_local_path = path
        self.local_path_entry.set_text(path)

        try:
            # ✨ No more pre-sorting. Just read all entries.
            for filename in os.listdir(path):
                full_path = os.path.join(path, filename)
                try:
                    st = os.stat(full_path)
                    if stat.S_ISDIR(st.st_mode):
                        self.local_store.append([ # Icon, Name, Size Str, Size Bytes, Perms Str, Perms Mode, Modified Str, Modified TS, Is Dir, Full Path (10 elements)
                            "folder-symbolic", filename, "<DIR>", -1, stat.filemode(st.st_mode), st.st_mode, self._format_date(st.st_mtime), int(st.st_mtime),
                            True, os.path.join(path, filename)
                        ])
                    else:
                        self.local_store.append([ # Icon, Name, Size Str, Size Bytes, Perms Str, Perms Mode, Modified Str, Modified TS, Is Dir, Full Path (10 elements)
                            "document-symbolic", filename, self._format_size(st.st_size), st.st_size, stat.filemode(st.st_mode), st.st_mode, self._format_date(st.st_mtime), int(st.st_mtime),
                            False, os.path.join(path, filename)
                        ])
                except (OSError, PermissionError):
                    continue

        except (PermissionError, FileNotFoundError) as e:
            logging.error(f"Error loading local directory '{path}': {e}")
            # Optionally, show an error in the UI

    def _load_remote_directory_threaded(self, path):
        """Wrapper to run _load_remote_directory in a background thread."""
        if not self.sftp_client:
            self._log_message(_("Error: SFTP client not connected."))
            return
        thread = threading.Thread(target=self._load_remote_directory, args=(path,))
        thread.daemon = True
        thread.start()

    def _load_remote_directory(self, path):
        """Populates the remote file view (runs in a thread)."""
        self._log_message(_("Reading remote directory: {path}...").format(path=path))
        try:
            items = self.sftp_client.listdir_attr(path)
            
            # Prepare data for UI update
            rows_to_add = []
            
            dirs, files = [], []
            for attr in items:
                if stat.S_ISDIR(attr.st_mode):
                    dirs.append(attr)
                else:
                    files.append(attr)
            
            dirs.sort(key=lambda x: x.filename.lower())
            files.sort(key=lambda x: x.filename.lower())

            for attr in dirs:
                rows_to_add.append([ # Icon, Name, Size Str, Size Bytes, Perms Str, Perms Mode, Modified Str, Modified TS, Is Dir, Full Path (10 elements)
                    "folder-symbolic", attr.filename, "<DIR>", -1, stat.filemode(attr.st_mode), attr.st_mode, self._format_date(attr.st_mtime), int(attr.st_mtime),
                    True, os.path.join(path, attr.filename)
                ])
            for attr in files:
                rows_to_add.append([ # Icon, Name, Size Str, Size Bytes, Perms Str, Perms Mode, Modified Str, Modified TS, Is Dir, Full Path (10 elements)
                    "document-symbolic", attr.filename, self._format_size(attr.st_size), attr.st_size, stat.filemode(attr.st_mode), attr.st_mode, self._format_date(attr.st_mtime), int(attr.st_mtime),
                    False, os.path.join(path, attr.filename)
                ])

            # Send data to the main thread for UI update
            def update_ui():
                self.remote_store.clear()
                for row in rows_to_add:
                    self.remote_store.append(row)
                self.current_remote_path = path
                self.remote_path_entry.set_text(path)
                self.remote_sortable_model.set_sort_column_id(COL_NAME, Gtk.SortType.ASCENDING)

            self.ui_queue.put(update_ui)
            self._log_message(_("Successfully listed remote directory: {path}").format(path=path))

        except Exception as e:
            self._log_message(_("Error reading remote directory '{path}': {e}").format(path=path, e=e), is_error=True)

    def _connect_sftp(self):
        """Connects to the SFTP server in a background thread."""
        if not IS_PARAMIKO_AVAILABLE:
            self._log_message(_("SFTP is disabled. Please install 'paramiko'."), is_error=True)
            return

        host_str = self.host_config.get("host", "")
        if not host_str:
            self._log_message(_("Error: host is not set in the config."), is_error=True)
            return

        # ✨ If no user is specified, prompt for one, just like in the terminal.
        if '@' not in host_str:
            dialog = InputDialog(
                self.get_root(),
                title=_("Username Required"),
                message=_("Enter username for {host_str}").format(host_str=host_str)
            )
            dialog.run_async(lambda username: self._start_sftp_worker_with_user(username))
        else:
            self._start_sftp_worker_with_user(None)

    def _start_sftp_worker_with_user(self, username_from_prompt, key_passphrase=None, auth_password=None):
        """Starts the connection thread after getting the username (if needed)."""
        if username_from_prompt is None and '@' not in self.host_config.get("host", ""):
            self._log_message(_("SFTP connection canceled (no username provided)."))
            return

        self._log_message(_("Connecting to {name}...").format(name=self.host_config.get("name")))
        thread = threading.Thread(target=self._sftp_connect_worker, args=(username_from_prompt, key_passphrase, auth_password))
        thread.daemon = True
        thread.start()

    def _sftp_connect_worker(self, username_from_prompt, key_passphrase=None, auth_password=None):
        """The actual connection logic that runs in a thread."""
        cfg = self.host_config
        host_str = cfg.get("host", "")
        
        # ✨ Correctly parse user and host
        if '@' in host_str:
            user, host = host_str.split('@', 1)
        elif username_from_prompt:
            user, host = username_from_prompt, host_str
        else:
            # This case should not be reached due to the prompt, but as a fallback:
            self._log_message(_("Authentication failed: Username is missing."), is_error=True)
            return

        port = int(cfg.get("port") or 22)
        key_filename = cfg.get("key_path")
        
        # --- ✨ New Connection Logic ---
        # 1. Try with provided auth_password (if any)
        if auth_password:
            try:
                self._log_message(_("Attempting connection with provided password..."))
                self.ssh_client = paramiko.SSHClient()
                self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                self.ssh_client.connect(host, port=port, username=user, password=auth_password, timeout=10, allow_agent=False, look_for_keys=False)
                self.sftp_client = self.ssh_client.open_sftp()
                self._log_message(_("SFTP connection established successfully with provided password."))
                # If successful, proceed to load remote directory and enable buttons
                initial_path = self.sftp_client.normalize('.')
                self._load_remote_directory(initial_path)
                self.ui_queue.put(lambda: self.button_box.set_sensitive(True))
                return # Connection successful, exit worker
            except Exception as e:
                self._log_message(_("Provided password authentication failed: {e}").format(e=e), is_error=True)
                # Fall through to other methods if provided password failed

        # 2. Try with key first, if it exists and no auth_password was successful.
        if key_filename and not self.sftp_client: # Only try key if not already connected
            try:
                self._log_message(_("Attempting connection with SSH key..."))
                self.ssh_client = paramiko.SSHClient()
                self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                self.ssh_client.connect(host, port=port, username=user, password=key_passphrase, key_filename=key_filename, timeout=10)
                self.sftp_client = self.ssh_client.open_sftp()
                self._log_message(_("SFTP connection established successfully with key."))
            except paramiko.PasswordRequiredException:
                self._log_message(_("SSH key is encrypted. Please enter the passphrase."))
                def prompt_for_key_password():
                    dialog = InputDialog(
                        self.get_root(),
                        title=_("SSH Key Passphrase"),
                        message=_("Enter passphrase for key '{key}'").format(key=os.path.basename(key_filename)),
                        is_password=True
                    )
                    dialog.run_async(lambda passphrase: self._start_sftp_worker_with_user(username_from_prompt, key_passphrase=passphrase, auth_password=None))
                GLib.idle_add(prompt_for_key_password)
                return # Stop this worker, a new one will be started.
            except paramiko.AuthenticationException:
                self._log_message(_("Key authentication failed. Falling back to password..."))
                # Let the code below handle password auth
                pass
            except Exception as e:
                self._log_message(_("SFTP connection failed with key: {e}").format(e=e), is_error=True)
                return # Stop on other errors

        # 3. If key auth was skipped or failed, and no auth_password was successful, try saved password from keyring.
        if not self.sftp_client:
            password_from_keyring = self.keyring.load_password(cfg.get("name"))
            if password_from_keyring:
                self._log_message(_("Attempting connection with saved password..."))
                try:
                    self.ssh_client = paramiko.SSHClient()
                    self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    self.ssh_client.connect(host, port=port, username=user, password=password_from_keyring, key_filename=None, timeout=10, allow_agent=False, look_for_keys=False)
                    self.sftp_client = self.ssh_client.open_sftp()
                    self._log_message(_("SFTP connection established successfully with password."))
                except Exception as e:
                    self._log_message(_("Saved password authentication failed: {e}").format(e=e), is_error=True)
            else:
                # 4. If no saved password, prompt for one.
                self._log_message(_("No key or saved password. Please enter password."))
                def prompt_for_password():
                    dialog = InputDialog(
                        self.get_root(),
                        title=_("Password Required"),
                        message=_("Enter password for {user}@{host}").format(user=user, host=host),
                        is_password=True
                    )
                    def on_password_entered(pwd):
                        if pwd is not None: # Check for None, as empty string is valid
                            self._start_sftp_worker_with_user(username_from_prompt, auth_password=pwd) # Re-run with password
                        else:
                            self._log_message(_("Connection canceled."), is_error=True)
                    dialog.run_async(on_password_entered)
                GLib.idle_add(prompt_for_password)
                return # Stop this worker

        # 3. If connection was successful (either by key or password)
        if self.sftp_client:
            initial_path = self.sftp_client.normalize('.')
            self._load_remote_directory(initial_path)
            self.ui_queue.put(lambda: self.button_box.set_sensitive(True))
        else:
            # If we reach here, it means all attempts failed.
            self._log_message(_("Authentication failed. Please check credentials and connection."), is_error=True)

    def _make_progress_callback(self, filename, total_size):
        """Creates a callback function for paramiko to track file transfer progress."""
        last_percent = -1

        def progress(bytes_transferred, _total_bytes):
            nonlocal last_percent
            if total_size == 0:
                return

            percent = int((bytes_transferred / total_size) * 100)

            # Log progress in increments of 10% to avoid spamming the log
            if percent >= last_percent + 10:
                last_percent = percent
                self._log_message(_("Transferring {filename}: {percent}%").format(filename=filename, percent=percent))

        return progress

    def on_upload_clicked(self, button):
        """Handles the click on the Upload (>) button."""
        selection = self.local_view.get_selection()
        model, paths = selection.get_selected_rows()
        if not paths:
            self._log_message(_("No local files selected for upload."), is_error=True)
            return

        for path in paths:
            tree_iter = model.get_iter(path)
            local_path = model.get_value(tree_iter, COL_FULL_PATH)
            is_dir = model.get_value(tree_iter, COL_IS_DIR)
            remote_dest_dir = self.current_remote_path

            self._log_message(_("Queueing upload for: {path}").format(path=local_path))
            thread = threading.Thread(target=self._upload_worker, args=(local_path, remote_dest_dir, is_dir))
            thread.daemon = True
            thread.start()

    def _upload_worker(self, local_path, remote_dest_dir, is_dir):
        """Uploads a file or directory recursively (runs in a thread)."""
        if not self.sftp_client: return
        basename = os.path.basename(local_path)
        remote_path = os.path.join(remote_dest_dir, basename).replace('\\', '/')

        try:
            if not is_dir: # It's a file
                file_size = os.path.getsize(local_path)
                progress_callback = self._make_progress_callback(basename, file_size)
                self._log_message(_("Uploading file {local} to {remote}...").format(local=local_path, remote=remote_path))
                self.sftp_client.put(local_path, remote_path, callback=progress_callback)
                self._log_message(_("File upload successful: {basename}").format(basename=basename))
            else: # It's a directory
                self._log_message(_("Uploading directory {local} to {remote}...").format(local=local_path, remote=remote_path))
                self.sftp_client.mkdir(remote_path)
                for dirpath, subdirs, filenames in os.walk(local_path):
                    relative_path = os.path.relpath(dirpath, local_path)
                    if relative_path == '.':
                        remote_dir = remote_path
                    else:
                        remote_dir = os.path.join(remote_path, relative_path).replace('\\', '/')

                    for sub_dir in subdirs:
                        try:
                            self.sftp_client.mkdir(os.path.join(remote_dir, sub_dir).replace('\\', '/'))
                        except Exception:
                            pass # Directory might already exist

                    for filename in filenames:
                        local_file = os.path.join(dirpath, filename)
                        remote_file = os.path.join(remote_dir, filename).replace('\\', '/')
                        file_size = os.path.getsize(local_file)
                        progress_callback = self._make_progress_callback(filename, file_size)
                        self.sftp_client.put(local_file, remote_file, callback=progress_callback)
                self._log_message(_("Directory upload successful: {basename}").format(basename=basename))

            # Refresh remote view on success
            self.ui_queue.put(lambda: self._load_remote_directory_threaded(self.current_remote_path))

        except Exception as e:
            self._log_message(_("Upload failed for {basename}: {e}").format(basename=basename, e=e), is_error=True)

    def on_download_clicked(self, button):
        """Handles the click on the Download (<) button."""
        selection = self.remote_view.get_selection()
        model, paths = selection.get_selected_rows()
        if not paths:
            self._log_message(_("No remote files selected for download."), is_error=True)
            return

        for path in paths:
            tree_iter = model.get_iter(path)
            remote_path = model.get_value(tree_iter, COL_FULL_PATH)
            is_dir = model.get_value(tree_iter, COL_IS_DIR)
            local_dest_dir = self.current_local_path

            self._log_message(_("Queueing download for: {path}").format(path=remote_path))
            thread = threading.Thread(target=self._download_worker, args=(remote_path, local_dest_dir, is_dir))
            thread.daemon = True
            thread.start()

    def _download_worker(self, remote_path, local_dest_dir, is_dir):
        """Downloads a file or directory recursively (runs in a thread)."""
        if not self.sftp_client: return
        basename = os.path.basename(remote_path)
        local_path = os.path.join(local_dest_dir, basename)

        try:
            if not is_dir: # It's a file
                file_attrs = self.sftp_client.stat(remote_path)
                progress_callback = self._make_progress_callback(basename, file_attrs.st_size)
                self._log_message(_("Downloading file {remote} to {local}...").format(remote=remote_path, local=local_path))
                self.sftp_client.get(remote_path, local_path, callback=progress_callback)
                self._log_message(_("File download successful: {basename}").format(basename=basename))
            else: # It's a directory
                self._log_message(_("Downloading directory {remote} to {local}...").format(remote=remote_path, local=local_path))
                os.makedirs(local_path, exist_ok=True)
                for item in self.sftp_client.listdir_attr(remote_path):
                    self._download_worker(os.path.join(remote_path, item.filename).replace('\\', '/'), local_path, stat.S_ISDIR(item.st_mode))
                self._log_message(_("Directory download successful: {basename}").format(basename=basename))

            # Refresh local view on success
            self.ui_queue.put(lambda: self._load_local_directory(self.current_local_path))

        except Exception as e:
            self._log_message(_("Download failed for {basename}: {e}").format(basename=basename, e=e), is_error=True)

    def _format_size(self, size_bytes):
        """Formats a size in bytes to a human-readable string."""
        if size_bytes == 0:
            return "0 B"
        size_name = ("B", "KiB", "MiB", "GiB", "TiB")
        i = int(size_bytes.bit_length() / 10)
        p = 1024 ** i
        s = round(size_bytes / p, 1)
        return f"{s} {size_name[i]}"

    def _format_date(self, timestamp):
        """Formats a UNIX timestamp to a human-readable string."""
        dt_object = datetime.datetime.fromtimestamp(timestamp)
        return dt_object.strftime("%Y-%m-%d %H:%M")

    def on_local_up_clicked(self, button):
        """Handles the 'Up' button click."""
        parent_path = os.path.dirname(self.current_local_path)
        if parent_path != self.current_local_path: # Avoid getting stuck at "/"
            self._load_local_directory(parent_path)

    def on_local_path_activated(self, entry):
        """Handles Enter press in the path entry."""
        new_path = entry.get_text().strip()
        if os.path.isdir(new_path):
            self._load_local_directory(new_path)
        else:
            # Maybe show an error tooltip
            entry.set_text(self.current_local_path)

    def on_local_row_activated(self, tree_view, path, column):
        """Handles double-click on a file or directory."""
        model = tree_view.get_model()
        tree_iter = model.get_iter(path)
        is_dir = model.get_value(tree_iter, COL_IS_DIR)
        full_path = model.get_value(tree_iter, COL_FULL_PATH)

        if is_dir:
            self._load_local_directory(full_path)
        else: # It's a file, open it with the default application
            try:
                gfile = Gio.File.new_for_path(full_path)
                # Use Gtk.FileLauncher for the modern, correct way to open files
                launcher = Gtk.FileLauncher.new()
                launcher.set_file(gfile)
                launcher.launch(self.get_root(), None, None, None)
            except Exception as e:
                self._log_message(_("Failed to open local file {path}: {e}").format(path=full_path, e=e), is_error=True)

    def on_remote_up_clicked(self, button):
        if not self.current_remote_path: return
        parent_path = os.path.dirname(self.current_remote_path)
        if parent_path != self.current_remote_path:
            self._load_remote_directory_threaded(parent_path)

    def on_remote_path_activated(self, entry):
        self._load_remote_directory_threaded(entry.get_text().strip())

    def on_remote_row_activated(self, tree_view, path, column):
        model = tree_view.get_model()
        tree_iter = model.get_iter(path)
        is_dir = model.get_value(tree_iter, COL_IS_DIR)
        full_path = model.get_value(tree_iter, COL_FULL_PATH)
        if is_dir:
            self._load_remote_directory_threaded(full_path)
        else: # It's a file, start the download-edit-upload cycle
            self._log_message(_("Opening remote file for editing: {path}").format(path=full_path))
            thread = threading.Thread(target=self._remote_edit_worker, args=(full_path,))
            thread.daemon = True
            thread.start()

    def _remote_edit_worker(self, remote_path):
        """Downloads a remote file to a temp location, opens it, and monitors for changes."""
        if not self.sftp_client: return

        basename = os.path.basename(remote_path)
        local_temp_path = os.path.join(self.temp_dir, basename)

        try:
            # 1. Download the file
            self._log_message(_("Downloading {basename} to temporary location...").format(basename=basename))
            self.sftp_client.get(remote_path, local_temp_path)

            # 2. Open the local temporary file (in the main thread)
            def open_and_monitor():
                try:
                    gfile = Gio.File.new_for_path(local_temp_path)
                    # Open with default app
                    launcher = Gtk.FileLauncher.new()
                    launcher.set_file(gfile)
                    launcher.launch(self.get_root(), None, None, None)

                    # 3. Monitor for changes
                    monitor = gfile.monitor_file(Gio.FileMonitorFlags.NONE, None)
                    monitor.connect("changed", self.on_temp_file_changed, local_temp_path, remote_path)
                    self.file_monitors[local_temp_path] = (monitor, remote_path)
                    self._log_message(_("Now monitoring {basename} for changes.").format(basename=basename))

                except Exception as e:
                    self._log_message(_("Failed to open or monitor temporary file: {e}").format(e=e), is_error=True)

            self.ui_queue.put(open_and_monitor)

        except Exception as e:
            self._log_message(_("Failed to download file for editing: {e}").format(e=e), is_error=True)

    def on_temp_file_changed(self, monitor, file, other_file, event_type, local_path, remote_path):
        """Callback when a monitored temporary file is changed."""
        # We are interested in actual content changes, not just closing.
        if event_type == Gio.FileMonitorEvent.CHANGES_DONE_HINT:
            self._log_message(_("Detected changes in {basename}. Uploading back to server...").format(basename=os.path.basename(local_path)))
            # Start the upload in a background thread to avoid blocking the UI
            # We can reuse the existing upload worker.
            thread = threading.Thread(target=self._upload_worker, args=(local_path, os.path.dirname(remote_path), False))
            thread.daemon = True
            thread.start()

    def on_local_view_key_pressed(self, controller, keyval, keycode, modifier):
        """Handles key presses on the local file list, specifically Backspace."""
        if keyval == Gdk.KEY_BackSpace:
            self.on_local_up_clicked(None)
            return True # Event handled
        return False # Event not handled

    def on_remote_view_key_pressed(self, controller, keyval, keycode, modifier):
        """Handles key presses on the remote file list, specifically Backspace."""
        if keyval == Gdk.KEY_BackSpace:
            self.on_remote_up_clicked(None)
            return True # Event handled
        return False # Event not handled

    def _log_message(self, message, is_error=False):
        """Appends a message to the log view in a thread-safe way."""
        def append_log():
            # ✨ Check if the user is scrolled to the bottom before appending.
            # This prevents auto-scrolling if the user is reading old logs.
            scroll_adj = self.log_view.get_parent().get_vadjustment()
            is_at_bottom = (scroll_adj.get_value() >= scroll_adj.get_upper() - scroll_adj.get_page_size() - 5) # 5px tolerance

            buf = self.log_view.get_buffer()
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            log_line = f"[{timestamp}] {message}\n"
            end_iter = buf.get_end_iter()
            buf.insert(end_iter, log_line)

            # ✨ Only scroll if the view was already at the bottom.
            if is_at_bottom:
                # ✨ To prevent invalid iterator warnings, we create a function that gets
                # the end iterator *at the moment of execution*, not when it's scheduled.
                def do_scroll():
                    end_iter = self.log_view.get_buffer().get_end_iter()
                    self.log_view.scroll_to_iter(end_iter, 0.0, True, 0.0, 1.0)
                GLib.idle_add(do_scroll)

            # TODO: Add color tags for errors
        self.ui_queue.put(append_log)

    def _process_ui_queue(self):
        """Process UI updates from background threads."""
        while not self.ui_queue.empty():
            callback = self.ui_queue.get()
            callback()
        return True # Keep the timeout running

    def on_widget_destroy(self, *args):
        """Clean up resources when the widget is destroyed."""
        if self.sftp_client: self.sftp_client.close()
        if self.ssh_client: self.ssh_client.close()

        # ✨ Clean up file monitors and temporary directory
        for monitor, _ in self.file_monitors.values():
            monitor.cancel()
        self.file_monitors.clear()
        try:
            shutil.rmtree(self.temp_dir)
            self._log_message(f"Cleaned up temporary directory: {self.temp_dir}")
        except Exception as e:
            self._log_message(f"Failed to clean up temporary directory {self.temp_dir}: {e}", is_error=True)

        self._log_message(_("SFTP connection closed."))

    def setup_actions_and_popovers(self):
        """Creates GActions and PopoverMenus for context menus."""
        # ✨ Create an action group for this widget and insert it with the "sftp" prefix.
        self.sftp_action_group = Gio.SimpleActionGroup()
        self.insert_action_group("sftp", self.sftp_action_group)

        action_rename = Gio.SimpleAction.new("rename-file", None)
        action_rename.connect("activate", self.on_rename_activated)
        self.sftp_action_group.add_action(action_rename)

        action_delete = Gio.SimpleAction.new("delete-file", None)
        action_delete.connect("activate", self.on_delete_activated)
        self.sftp_action_group.add_action(action_delete)

        action_transfer = Gio.SimpleAction.new("transfer-file", None)
        action_transfer.connect("activate", self.on_transfer_activated)
        self.sftp_action_group.add_action(action_transfer)

        action_chmod = Gio.SimpleAction.new("chmod-file", None)
        action_chmod.connect("activate", self.on_chmod_activated)
        self.sftp_action_group.add_action(action_chmod)

        menu = Gio.Menu()
        menu.append(_("Transfer"), "sftp.transfer-file")
        menu.append(_("Rename..."), "sftp.rename-file")
        menu.append(_("Change Permissions..."), "sftp.chmod-file")
        menu.append(_("Delete"), "sftp.delete-file")

        self.popover_file = Gtk.PopoverMenu.new_from_model(menu)
        self.popover_file.set_parent(self) # The popover is a child of the whole widget

    def on_view_right_click(self, gesture, n_press, x, y, view):
        """Shows the context menu for a file/directory. This is the final, correct implementation."""
        # Stop the event from propagating further to prevent selection issues.
        gesture.set_state(Gtk.EventSequenceState.CLAIMED)

        path_info = view.get_path_at_pos(int(x), int(y))
        if not path_info:
            view.get_selection().unselect_all()
            return

        path, col, _, _ = path_info
        # It's crucial to select the row *before* showing the menu.
        view.get_selection().select_path(path)
        self.last_clicked_view = view
        model = view.get_model()

        # ✨ Enable "Change Permissions" for any valid file/dir, but disable for ".."
        chmod_action = self.sftp_action_group.lookup_action("chmod-file")
        if model.get_value(model.get_iter(path), COL_NAME) == "..":
            if chmod_action: chmod_action.set_enabled(False)
        else:
            if chmod_action: chmod_action.set_enabled(True)

        # ✨ Translate coordinates from the clicked view's system to the parent widget's system.
        translated_x, translated_y = view.translate_coordinates(self, x, y)

        # Create a rectangle at the translated cursor position.
        rect = Gdk.Rectangle()
        rect.x = int(translated_x)
        rect.y = int(translated_y)
        rect.width = rect.height = 1
        self.popover_file.set_pointing_to(rect)
        self.popover_file.popup()

    def on_rename_activated(self, action, param):
        """Handles the 'Rename' action from the context menu."""
        if not self.last_clicked_view: return
        selection = self.last_clicked_view.get_selection()
        model, tree_iter = selection.get_selected()
        if not tree_iter: return

        old_full_path = model.get_value(tree_iter, COL_FULL_PATH)
        old_name = model.get_value(tree_iter, COL_NAME)

        dialog = InputDialog(self.get_root(), title=_("Rename"), message=_("New name for '{old_name}':").format(old_name=old_name), default_text=old_name)
        dialog.run_async(lambda new_name: self._execute_rename(old_full_path, new_name))

    def _execute_rename(self, old_path, new_name):
        """Performs the actual rename operation."""
        if not new_name or os.path.basename(old_path) == new_name: return

        new_path = os.path.join(os.path.dirname(old_path), new_name)
        is_local = (self.last_clicked_view == self.local_view)

        def rename_task():
            try:
                if is_local:
                    os.rename(old_path, new_path)
                    self.ui_queue.put(lambda: self._load_local_directory(self.current_local_path))
                else: # Remote
                    self.sftp_client.rename(old_path, new_path)
                    self.ui_queue.put(lambda: self._load_remote_directory_threaded(self.current_remote_path))
                self._log_message(_("Renamed '{old}' to '{new}'").format(old=os.path.basename(old_path), new=new_name))
            except Exception as e:
                self._log_message(_("Rename failed: {e}").format(e=e), is_error=True)

        thread = threading.Thread(target=rename_task)
        thread.daemon = True
        thread.start()

    def on_delete_activated(self, action, param):
        """Handles the 'Delete' action from the context menu."""
        if not self.last_clicked_view: return
        selection = self.last_clicked_view.get_selection()
        model, tree_iter = selection.get_selected()
        if not tree_iter: return

        full_path = model.get_value(tree_iter, COL_FULL_PATH)
        is_dir = model.get_value(tree_iter, COL_IS_DIR)
        is_local = (self.last_clicked_view == self.local_view)

        # Determine if the directory is empty (for local only, remote is harder to check without recursion)
        is_empty_dir = False
        if is_dir and is_local:
            try:
                if not os.listdir(full_path):
                    is_empty_dir = True
            except OSError:
                pass # Can't list, assume not empty or permission denied

        # Prepare dialog messages
        heading = _("Delete '{name}'?").format(name=os.path.basename(full_path))
        body = _("This action cannot be undone.")
        
        if is_dir and not is_empty_dir:
            heading = _("Delete non-empty directory '{name}'?").format(name=os.path.basename(full_path))
            body = _("This will recursively delete all its contents.\nThis action cannot be undone.")

        dialog = MessageDialog(
            self.get_root(),
            heading=heading,
            body=body,
            buttons=[(_("Cancel"), Gtk.ResponseType.CANCEL), (_("Delete"), Gtk.ResponseType.DESTRUCTIVE)]
        )

        def on_response(dialog, response_id):
            if response_id == Gtk.ResponseType.DESTRUCTIVE:
                self._execute_delete(full_path, is_dir, is_local)
            dialog.destroy()

        dialog.run_async(on_response)

    def _execute_delete(self, full_path, is_dir, is_local):
        """Performs the actual delete operation in a thread."""
        def delete_task():
            try:
                if is_local:
                    if is_dir:
                        shutil.rmtree(full_path) # Recursive delete for local directories
                    else:
                        os.remove(full_path)
                    self.ui_queue.put(lambda: self._load_local_directory(self.current_local_path))
                else: # Remote
                    if is_dir:
                        self._sftp_rm_recursive(full_path) # Recursive delete for remote directories
                    else:
                        self.sftp_client.remove(full_path)
                    self.ui_queue.put(lambda: self._load_remote_directory_threaded(self.current_remote_path))
                self._log_message(_("Deleted: {path}").format(path=full_path))
            except Exception as e:
                self._log_message(_("Delete failed: {e}").format(e=e), is_error=True)

        thread = threading.Thread(target=delete_task)
        thread.daemon = True
        thread.start()

    def _sftp_rm_recursive(self, path):
        """Recursively removes a directory and its contents on the remote server."""
        if not self.sftp_client: return
        
        for item in self.sftp_client.listdir_attr(path):
            full_remote_path = os.path.join(path, item.filename).replace('\\', '/')
            if stat.S_ISDIR(item.st_mode):
                self._sftp_rm_recursive(full_remote_path)
            else:
                self.sftp_client.remove(full_remote_path)
        self.sftp_client.rmdir(path)
        self._log_message(_("Recursively deleted remote directory: {path}").format(path=path))




    def on_transfer_activated(self, action, param):
        """Handles the 'Transfer' action from the context menu."""
        if not self.last_clicked_view: return
        if self.last_clicked_view == self.local_view:
            self.on_upload_clicked(None)
        else:
            self.on_download_clicked(None)

    def on_chmod_activated(self, action, param):
        """Handles the 'Change Permissions' action."""
        if not self.last_clicked_view: return

        selection = self.last_clicked_view.get_selection()
        model, tree_iter = selection.get_selected()
        if not tree_iter: return

        full_path = model.get_value(tree_iter, COL_FULL_PATH)
        current_mode = model.get_value(tree_iter, COL_PERMS_MODE)

        dialog = PermissionsDialog(self.get_root(), initial_mode=current_mode)
        dialog.run_async(lambda new_mode: self._execute_chmod(full_path, new_mode))

    def _execute_chmod(self, path, new_mode):
        """Applies new permissions to a remote file/directory."""
        if new_mode is None: return # Dialog was cancelled
        is_local = (self.last_clicked_view == self.local_view)

        def chmod_task():
            try:
                if is_local:
                    os.chmod(path, new_mode)
                    # Refresh local view
                    self.ui_queue.put(lambda: self._load_local_directory(self.current_local_path))
                else: # Remote
                    self.sftp_client.chmod(path, new_mode)
                    # Refresh remote view
                    self.ui_queue.put(lambda: self._load_remote_directory_threaded(self.current_remote_path))

                self._log_message(_("Permissions changed for {path} to {mode}").format(path=path, mode=oct(new_mode)[2:]))
            except Exception as e:
                self._log_message(_("Failed to change permissions for {path}: {e}").format(path=path, e=e), is_error=True)

        thread = threading.Thread(target=chmod_task)
        thread.daemon = True
        thread.start()