import sys
import threading
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, Gio, GLib

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
                         flags=Gio.ApplicationFlags.FLAGS_NONE)

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = CyswlltWindow(application=self)
        win.present()

    def do_startup(self):
        Adw.Application.do_startup(self)
        
        # Actions
        connect_action = Gio.SimpleAction.new("connect", None)
        connect_action.connect("activate", self.on_connect)
        self.add_action(connect_action)
        
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self.on_about)
        self.add_action(about_action)

    def on_about(self, action, param):
        win = self.props.active_window
        
        # Create Adw.AboutWindow (or gtk.AboutDialog if Adw 1.0 doesn't have AboutWindow easily accessible, 
        # but Adw has Adw.AboutWindow in newer versions. Let's stick to generic Adw.AboutWindow if possible or Gtk.AboutDialog)
        # Checking gi versions... Adw 1 usually has AboutWindow.
        
        about = Adw.AboutWindow(
            transient_for=win,
            application_name="Cyswllt",
            application_icon="com.taliskerman.cyswllt", # Or file path if not installed
            developer_name="Chuck Talk",
            version="0.1.0",
            copyright="© 2026 Chuck Talk <cwtalk1@gmail.com>",
            license_type=Gtk.License.GPL_3_0,
            website="https://github.com/TaliskerMan/Cyswllt",
            issue_url="https://github.com/TaliskerMan/Cyswllt/issues"
        )
        
        # If the icon isn't installed in the system theme, AdwAboutWindow might show broken icon.
        # We can try to set the logo paintable to our file.
        icon_path = "/home/freecode/antigrav/Cyswllt/data/icons/cyswllt.png"
        if GLib.file_test(icon_path, GLib.FileTest.EXISTS):
             texture = Gdk.Texture.new_from_filename(icon_path)
             about.set_application_icon("cyswllt") # Fallback
             # Adw.AboutWindow uses application_icon property which is a string name.
             # It doesn't easy support a paintable unless we subclass or hack it.
             # However, we can use Gtk.AboutDialog which supports logo.
             # But Adw.AboutWindow is nicer. 
             # Let's stick with Adw.AboutWindow and assume we install the icon properly in install.sh.
             pass

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
