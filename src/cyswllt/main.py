# Copyright (C) 2026 Chuck Talk, Nordheim Online, LLC
# This file is part of Cyswllt.
# Released under the GNU GPL v3 license.

import sys
import threading
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, Gio, GLib, Gdk

from cyswllt.auth_manager import AuthManager
from cyswllt.mount_manager import MountManager

class CyswlltWindow(Adw.ApplicationWindow):
    def __init__(self, *args, **kwargs):
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

        # Menu Button in Header
        menu = Gio.Menu()
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
        
        # Add box to a clamp or scroll view if needed, but for now direct is fine
        # We wrap it in a window content to be safe
        content.set_content(box)

        # Drive Icon
        # Locate icon relative to this script
        # structure is src/cyswllt/main.py -> need ../../data/icons/cyswllt.png
        import os
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        icon_path = os.path.join(base_dir, "data", "icons", "cyswllt.png")
        
        if os.path.exists(icon_path):
             self.icon_image = Gtk.Image.new_from_file(icon_path)
        else:
             # Fallback to theme icon if file not found
             self.icon_image = Gtk.Image.new_from_icon_name("drive-harddisk-symbolic")
             # Try to set pixel size just in case
             
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
        """Checks authentication and mount status and updates UI."""
        is_auth = self.auth_manager.is_authenticated()
        if is_auth:
            if self.mount_manager.is_mounted():
                self.update_ui_state(mounted=True)
            else:
                self.update_ui_state(authenticated=True, mounted=False)
        else:
            self.update_ui_state(authenticated=False, mounted=False)

    def update_ui_state(self, authenticated=False, mounted=False, loading=False):
        """Updates labels and button text based on state."""
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
    def __init__(self):
        super().__init__(application_id='com.taliskerman.cyswllt',
                         flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)

    def do_command_line(self, command_line):
        self.activate()
        return 0

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = CyswlltWindow(application=self)
        win.present()

    def do_startup(self):
        Adw.Application.do_startup(self)
        
        # Add local icon directory to theme search path so "cyswllt" icon name resolves
        # This works for both dev (relative) and installed (/usr/share/icons/...) if we set it up right
        # For installed, it should be in standard path, but for dev or if cache is broken, this helps.
        import os
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

    def on_help(self, action, param):
        win = self.props.active_window
        if not win:
            return
            
        dialog = Adw.MessageDialog(
            transient_for=win,
            heading="How to use Cyswllt",
            body="1. Click 'Connect' or 'Sign in with Google' to start authentication.\n"
                 "2. A browser window will open. Allow access to your Google Drive.\n"
                 "3. Once authenticated, your Drive will be mounted locally.\n"
                 "4. You can access your files through your file manager.\n"
                 "5. Click 'Disconnect' when you are finished to unmount the drive."
        )
        dialog.add_response("ok", "Got it")
        dialog.present()

    def on_about(self, action, param):
        win = self.props.active_window
        
        from cyswllt.version import __version__
        
        # Create Adw.AboutWindow
        about = Adw.AboutWindow(
            transient_for=win,
            application_name="Cyswllt",
            application_icon="noln",
            developer_name="Chuck Talk",
            version=__version__,
            copyright="© 2026 Chuck Talk, Nordheim Online, LLC",
            license_type=Gtk.License.GPL_3_0,
            website="https://nordheim.online",
            issue_url="https://github.com/TaliskerMan/Cyswllt/issues"
        )
        
        # We rely on Gtk.IconTheme finding "cyswllt" now.
        
        about.present()

        about.present()

    def on_connect(self, action, param):
        win = self.props.active_window
        if not win:
            return

        # Determine current state to know what action to take
        is_auth = win.auth_manager.is_authenticated()
        is_mounted = win.mount_manager.is_mounted()
        
        win.update_ui_state(loading=True)

        def worker():
            if is_mounted:
                # Disconnect -> Unmount
                GLib.idle_add(lambda: win.status_label.set_label("Disconnecting..."))
                success = win.mount_manager.unmount()
                if not success:
                    print("Failed to unmount")
            elif is_auth:
                # Authenticated but not mounted -> Mount
                GLib.idle_add(lambda: win.status_label.set_label("Connecting..."))
                success = win.mount_manager.mount()
            else:
                # Not authenticated -> Authenticate
                GLib.idle_add(lambda: win.status_label.set_label("Waiting for browser auth..."))
                success = win.auth_manager.start_authentication()
                if success:
                     GLib.idle_add(lambda: win.status_label.set_label("Connecting..."))
                     success = win.mount_manager.mount()

            GLib.idle_add(win.check_status)

        threading.Thread(target=worker, daemon=True).start()

def main():
    app = CyswlltApp()
    return app.run(sys.argv)

if __name__ == '__main__':
    sys.exit(main())
