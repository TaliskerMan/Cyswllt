# Copyright (C) 2026 Chuck Talk, Nordheim Online, LLC <chuck@nordheim.online>
# This file is part of Cyswllt.
# Released under the GNU GPL v3 license.

import sys
import threading
import logging
import os
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, Gio, GLib, Gdk

from cyswllt.auth_manager import AuthManager
from cyswllt.mount_manager import MountManager


class PerformanceDialog(Adw.PreferencesWindow):
    """
    A settings dialog that lets the user enter their own Google OAuth
    Client ID and Secret.  Using private credentials bypasses rclone's
    shared, heavily rate-limited Client ID and results in dramatically
    faster initial connections and directory renders.
    """

    def __init__(self, auth_manager: AuthManager, transient_for=None):
        """
        Initializes the PerformanceSettings dialog.

        Args:
            auth_manager (AuthManager): Authorization coordinator instance.
            transient_for (Gtk.Window): Parent transient window.
        """
        super().__init__(transient_for=transient_for, modal=True)
        self.auth_manager = auth_manager
        self.set_title("Performance Settings")
        self.set_default_size(480, -1)
        self.set_search_enabled(False)

        page = Adw.PreferencesPage()
        self.add(page)

        # ── Why section ──────────────────────────────────────────────
        why_group = Adw.PreferencesGroup(
            title="Custom Google Client ID",
            description=(
                "By default rclone uses a shared Client ID that is heavily "
                "rate-limited by Google because millions of people use it. "
                "Creating your own free Client ID in Google Cloud Console "
                "bypasses those limits and gives a noticeably faster connection.\n\n"
                "To get your credentials:\n"
                "1. Go to console.cloud.google.com\n"
                "2. Create a project → APIs & Services → Library → enable Google Drive API\n"
                "3. APIs & Services → OAuth consent screen → External (add yourself as test user)\n"
                "4. APIs & Services → Credentials → Create Credentials → OAuth client ID\n"
                "5. Choose Desktop app → copy the Client ID and Secret below"
            ),
        )
        page.add(why_group)

        # ── Credential entry rows ─────────────────────────────────────
        creds_group = Adw.PreferencesGroup()
        page.add(creds_group)

        self.client_id_row = Adw.EntryRow(title="Client ID")
        self.client_id_row.set_show_apply_button(False)
        creds_group.add(self.client_id_row)

        self.client_secret_row = Adw.PasswordEntryRow(title="Client Secret")
        creds_group.add(self.client_secret_row)

        # Pre-fill if credentials already exist
        existing = self.auth_manager.get_custom_credentials()
        if existing:
            self.client_id_row.set_text(existing.get("client_id", ""))
            self.client_secret_row.set_text(existing.get("client_secret", ""))

        # ── Status label ──────────────────────────────────────────────
        self.status_label = Gtk.Label(label="")
        self.status_label.set_margin_top(4)
        self.status_label.set_margin_bottom(4)
        self.status_label.set_wrap(True)
        self.status_label.set_xalign(0)
        creds_group.add(self.status_label)

        # ── Action buttons ────────────────────────────────────────────
        button_group = Adw.PreferencesGroup()
        page.add(button_group)

        save_row = Adw.ActionRow(title="Save credentials")
        save_row.set_subtitle("Credentials are stored in ~/.config/cyswllt/ with restricted permissions")
        save_btn = Gtk.Button(label="Save")
        save_btn.add_css_class("suggested-action")
        save_btn.set_valign(Gtk.Align.CENTER)
        save_btn.connect("clicked", self._on_save)
        save_row.add_suffix(save_btn)
        save_row.set_activatable_widget(save_btn)
        button_group.add(save_row)

        clear_row = Adw.ActionRow(title="Clear credentials")
        clear_row.set_subtitle("Revert to rclone's default shared Client ID")
        clear_btn = Gtk.Button(label="Clear")
        clear_btn.add_css_class("destructive-action")
        clear_btn.set_valign(Gtk.Align.CENTER)
        clear_btn.connect("clicked", self._on_clear)
        clear_row.add_suffix(clear_btn)
        clear_row.set_activatable_widget(clear_btn)
        button_group.add(clear_row)

        # ── Re-auth notice ────────────────────────────────────────────
        notice_group = Adw.PreferencesGroup()
        page.add(notice_group)

        notice_row = Adw.ActionRow(
            title="Changes take effect on next sign-in",
            subtitle=(
                "If you are already authenticated you will need to sign out "
                "and sign back in for the new Client ID to be used."
            ),
        )
        notice_row.set_icon_name("dialog-information-symbolic")
        notice_group.add(notice_row)

        self._refresh_status()

    def _refresh_status(self):
        """
        Refreshes status label based on the presence of custom OAuth credentials.
        """
        if self.auth_manager.has_custom_credentials():
            self.status_label.set_label("✓ Custom credentials are active")
            self.status_label.add_css_class("success")
            self.status_label.remove_css_class("error")
        else:
            self.status_label.set_label("Using rclone's default shared credentials")
            self.status_label.remove_css_class("success")
            self.status_label.remove_css_class("error")

    def _on_save(self, _button):
        """
        Saves the custom Client ID and Secret to disk when save is clicked.
        """
        client_id = self.client_id_row.get_text().strip()
        client_secret = self.client_secret_row.get_text().strip()

        if not client_id or not client_secret:
            self.status_label.set_label("⚠ Both Client ID and Client Secret are required")
            self.status_label.add_css_class("error")
            self.status_label.remove_css_class("success")
            return

        ok = self.auth_manager.save_custom_credentials(client_id, client_secret)
        if ok:
            self.status_label.set_label("✓ Credentials saved successfully")
            self.status_label.add_css_class("success")
            self.status_label.remove_css_class("error")
        else:
            self.status_label.set_label("✗ Failed to save credentials — check logs")
            self.status_label.add_css_class("error")
            self.status_label.remove_css_class("success")

    def _on_clear(self, _button):
        """
        Deletes custom OAuth credentials and resets dialog entry fields.
        """
        ok = self.auth_manager.clear_custom_credentials()
        if ok:
            self.client_id_row.set_text("")
            self.client_secret_row.set_text("")
            self.status_label.set_label("Credentials cleared — using rclone defaults")
            self.status_label.remove_css_class("success")
            self.status_label.remove_css_class("error")
        else:
            self.status_label.set_label("✗ Failed to clear credentials — check logs")
            self.status_label.add_css_class("error")
            self.status_label.remove_css_class("success")


class CyswlltWindow(Adw.ApplicationWindow):
    """
    Main application window of the Cyswllt client interface.

    Initializes layout components, toolbar headers, status displays, connect buttons, 
    and loading spinners.
    """
    def __init__(self, *args, **kwargs):
        """
        Initializes the application window.
        """
        super().__init__(*args, **kwargs)

        self.set_default_size(400, 350)
        self.set_title("Cyswllt")

        self.auth_manager = AuthManager()
        self.mount_manager = MountManager(AuthManager.REMOTE_NAME)

        # Toolbar View
        content = Adw.ToolbarView()
        self.set_content(content)

        # Header Bar
        header = Adw.HeaderBar()
        content.add_top_bar(header)

        # Help Button
        help_button = Gtk.Button(icon_name="help-about-symbolic")
        help_button.set_action_name("app.help")
        help_button.set_tooltip_text("Help & Usage")
        header.pack_end(help_button)

        # Menu Button in Header — now includes Performance Settings
        menu = Gio.Menu()
        menu.append("Performance Settings", "app.performance")
        menu.append("About Cyswllt", "app.about")

        menu_button = Gtk.MenuButton()
        menu_button.set_icon_name("open-menu-symbolic")
        menu_button.set_menu_model(menu)
        header.pack_end(menu_button)

        # Main content box
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(24)
        box.set_margin_bottom(24)
        box.set_margin_start(24)
        box.set_margin_end(24)
        box.set_valign(Gtk.Align.CENTER)
        content.set_content(box)

        # Drive Icon
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        icon_path = os.path.join(base_dir, "data", "icons", "cyswllt.png")

        if os.path.exists(icon_path):
            self.icon_image = Gtk.Image.new_from_file(icon_path)
        else:
            self.icon_image = Gtk.Image.new_from_icon_name("drive-harddisk-symbolic")

        self.icon_image.set_pixel_size(96)
        self.icon_image.add_css_class("drive-icon")
        box.append(self.icon_image)

        # Status Label
        self.status_label = Gtk.Label(label="Checking status...")
        self.status_label.add_css_class("title-2")
        box.append(self.status_label)

        # Sub-status label
        self.sub_status_label = Gtk.Label(label="")
        box.append(self.sub_status_label)

        # Connect/Disconnect Button
        self.connect_button = Gtk.Button(label="Connect")
        self.connect_button.add_css_class("suggested-action")
        self.connect_button.add_css_class("pill")
        self.connect_button.set_action_name("app.connect")
        box.append(self.connect_button)

        # Spinner
        self.spinner = Gtk.Spinner()
        box.append(self.spinner)

        # Initial check
        self.check_status()

    def check_status(self):
        """
        Inspects current Google Drive authentication and local mounting states,
        updating window status badges and labels.

        The underlying checks shell out to rclone, which can be slow to start, so
        they run on a worker thread; the UI is updated via ``GLib.idle_add`` to
        avoid stuttering the GTK main loop on launch.
        """
        self.update_ui_state(loading=True)

        def worker():
            is_auth = self.auth_manager.is_authenticated()
            is_mounted = self.mount_manager.is_mounted() if is_auth else False

            def apply():
                if is_auth and is_mounted:
                    self.update_ui_state(mounted=True)
                elif is_auth:
                    self.update_ui_state(authenticated=True, mounted=False)
                else:
                    self.update_ui_state(authenticated=False, mounted=False)
                return False

            GLib.idle_add(apply)

        threading.Thread(target=worker, daemon=True).start()

    def show_unmount_error(self, message):
        """Surfaces an unmount failure to the user via a modal dialog."""
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Could not disconnect",
            body=message,
        )
        dialog.add_response("ok", "OK")
        dialog.present()
        return False

    def update_ui_state(self, authenticated=False, mounted=False, loading=False):
        """
        Manipulates window layout elements (spinners, button states, drive icons) 
        according to the current connection progress.
        """
        if loading:
            self.spinner.start()
            self.connect_button.set_sensitive(False)
            self.status_label.set_label("Working...")
            self.sub_status_label.set_label("Please wait")
            return

        self.spinner.stop()
        self.connect_button.set_sensitive(True)

        if mounted:
            self.status_label.set_label("Connected")
            self.sub_status_label.set_label(f"Mounted at {self.mount_manager.mount_point}")
            self.connect_button.set_label("Disconnect")
            self.icon_image.get_style_context().remove_class("dim-label")
        elif authenticated:
            self.status_label.set_label("Ready to Connect")
            self.sub_status_label.set_label("Authenticated")
            self.connect_button.set_label("Connect")
            self.icon_image.get_style_context().add_class("dim-label")
        else:
            self.status_label.set_label("Disconnected")
            self.sub_status_label.set_label("Sign in to Google to start")
            self.connect_button.set_label("Sign in with Google")
            self.icon_image.get_style_context().add_class("dim-label")


class CyswlltApp(Adw.Application):
    """
    The Libadwaita Application manager coordinating application command-line arguments,
    activations, and action triggers.
    """
    def __init__(self):
        """
        Initializes the application instance.
        """
        super().__init__(
            application_id='com.taliskerman.cyswllt',
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
        )

    def do_command_line(self, command_line):
        """
        Handles command-line arguments by redirecting to standard activation.
        """
        self.activate()
        return 0

    def do_activate(self):
        """
        Triggers window instantiation when the application starts or is activated.
        """
        window = self.props.active_window
        if not window:
            window = CyswlltWindow(application=self)
        window.present()

    def do_startup(self):
        """
        Initializes application resources, mapping custom asset paths and registering
        global action callbacks (connect, about, help, performance settings).
        """
        Adw.Application.do_startup(self)

        # Add local icon directory to theme search path
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        icon_dir = os.path.join(base_dir, "data", "icons")

        if os.path.exists(icon_dir):
            display = Gdk.Display.get_default()
            if display:
                theme = Gtk.IconTheme.get_for_display(display)
                theme.add_search_path(icon_dir)

        # Actions
        connect_action = Gio.SimpleAction.new("connect", None)
        connect_action.connect("activate", self.on_connect)
        self.add_action(connect_action)

        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self.on_about)
        self.add_action(about_action)

        help_action = Gio.SimpleAction.new("help", None)
        help_action.connect("activate", self.on_help)
        self.add_action(help_action)

        performance_action = Gio.SimpleAction.new("performance", None)
        performance_action.connect("activate", self.on_performance)
        self.add_action(performance_action)

    def on_performance(self, action, param):
        """
        Action callback to display the Performance Settings dialog.
        """
        window = self.props.active_window
        if not window:
            return
        dialog = PerformanceDialog(auth_manager=window.auth_manager, transient_for=window)
        dialog.present()

    def on_help(self, action, param):
        """
        Action callback to display the How-to usage instructions dialog.
        """
        window = self.props.active_window
        if not window:
            return

        dialog = Adw.MessageDialog(
            transient_for=window,
            heading="How to use Cyswllt",
            body=(
                "1. Click 'Connect' or 'Sign in with Google' to start authentication.\n"
                "2. A browser window will open. Allow access to your Google Drive.\n"
                "3. Once authenticated, your Drive will be mounted locally.\n"
                "4. You can access your files through your file manager.\n"
                "5. Click 'Disconnect' when you are finished to unmount the drive.\n\n"
                "Tip: Open the menu and choose 'Performance Settings' to add your "
                "own Google Client ID for faster connections."
            ),
        )
        dialog.add_response("ok", "Got it")
        dialog.present()

    def on_about(self, action, param):
        """
        Action callback to display the application Credits / AboutWindow metadata.
        """
        window = self.props.active_window

        from cyswllt.version import __version__

        about = Adw.AboutWindow(
            transient_for=window,
            application_name="Cyswllt",
            application_icon="noln",
            developer_name="Chuck Talk",
            version=__version__,
            copyright="© 2026 Chuck Talk, Nordheim Online, LLC",
            license_type=Gtk.License.GPL_3_0,
            website="https://nordheim.online",
            issue_url="https://github.com/TaliskerMan/Cyswllt/issues",
        )
        about.present()

    def on_connect(self, action, param):
        """
        Action callback to run connect/disconnect workflows in a separate thread.
        
        Mounts existing remotes, unmounts mounted ones, or starts browser-based OAuth flows.
        """
        window = self.props.active_window
        if not window:
            return

        is_auth = window.auth_manager.is_authenticated()
        is_mounted = window.mount_manager.is_mounted()

        window.update_ui_state(loading=True)

        def worker():
            if is_mounted:
                GLib.idle_add(lambda: window.status_label.set_label("Disconnecting..."))
                success = window.mount_manager.unmount()
                if not success:
                    error_msg = window.mount_manager.last_unmount_error or "Unmount failed."
                    logging.error("Failed to unmount: %s", error_msg)
                    GLib.idle_add(lambda error=error_msg: window.show_unmount_error(error))
            elif is_auth:
                GLib.idle_add(lambda: window.status_label.set_label("Connecting..."))
                success = window.mount_manager.mount()
            else:
                GLib.idle_add(lambda: window.status_label.set_label("Waiting for browser auth..."))
                success = window.auth_manager.start_authentication()
                if success:
                    GLib.idle_add(lambda: window.status_label.set_label("Connecting..."))
                    success = window.mount_manager.mount()

            GLib.idle_add(window.check_status)

        threading.Thread(target=worker, daemon=True).start()


def setup_logging():
    """
    Sets up application file logging under ~/.cache/cyswllt/cyswllt.log,
    enforcing tight 0o600 file permission attributes.
    """
    log_dir = os.path.expanduser("~/.cache/cyswllt")
    os.makedirs(log_dir, mode=0o700, exist_ok=True)
    os.chmod(log_dir, 0o700) # Enforce tight permissions if already exists
    log_file = os.path.join(log_dir, "cyswllt.log")
    
    # Touch file securely if it doesn't exist to ensure permissions
    if not os.path.exists(log_file):
        try:
            fd = os.open(log_file, os.O_WRONLY | os.O_CREAT, 0o600)
            os.close(fd)
        except Exception:
            pass
    else:
        try:
            os.chmod(log_file, 0o600)
        except Exception:
            pass
            
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logging.info("Cyswllt Application Started")


def main():
    """
    The main execution entry point for the Cyswllt binary.
    """
    setup_logging()
    app = CyswlltApp()
    return app.run(sys.argv)


if __name__ == '__main__':
    sys.exit(main())
