"""
Sublime asdf
A Sublime Text plugin to automatically load asdf tool versions
"""

import os
import subprocess
import sublime
import sublime_plugin

__version__ = "0.1.0"
__author__ = "Agustin"

def get_settings():
    """Get plugin settings"""
    return sublime.load_settings('sublime-asdf.sublime-settings')

def debug_print(message):
    """Print debug message if debug is enabled"""
    if get_settings().get('debug', False):
        print(f"[sublime-asdf] {message}")

def find_tool_versions(start_path):
    """Search for .tool-versions file in current and parent directories"""
    current = os.path.abspath(start_path)

    while True:
        tool_versions = os.path.join(current, ".tool-versions")
        if os.path.exists(tool_versions):
            debug_print(f"Found .tool-versions at: {tool_versions}")
            return tool_versions

        parent = os.path.dirname(current)
        if parent == current:  # Reached root
            break
        current = parent

    return None

def parse_tool_versions(tool_versions_path):
    """Parse all tools and versions from .tool-versions file"""
    tools = {}
    if not tool_versions_path or not os.path.exists(tool_versions_path):
        return tools

    with open(tool_versions_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                parts = line.split()
                if len(parts) >= 2:
                    tool_name = parts[0]
                    version = parts[1]
                    tools[tool_name] = version

    return tools

def get_tool_version(tool_name):
    """Get version for a specific tool following asdf's resolution order"""
    home = os.path.expanduser("~")
    asdf_dir = os.path.join(home, ".asdf")

    current_window = sublime.active_window()
    if current_window:
        # First: Check based on current file location
        view = current_window.active_view()
        if view and view.file_name():
            file_dir = os.path.dirname(view.file_name())
            tool_versions_path = find_tool_versions(file_dir)
            if tool_versions_path:
                tools = parse_tool_versions(tool_versions_path)
                if tool_name in tools:
                    return tools[tool_name]

        # Fallback: Check window folders
        folders = current_window.folders()
        deepest_match = None
        deepest_depth = -1

        for folder in folders:
            tool_versions_path = find_tool_versions(folder)
            if tool_versions_path:
                tools = parse_tool_versions(tool_versions_path)
                if tool_name in tools:
                    depth = len(tool_versions_path.split(os.sep))
                    if depth > deepest_depth:
                        deepest_depth = depth
                        deepest_match = tools[tool_name]

        if deepest_match:
            return deepest_match

    # Check home directory .tool-versions
    home_tool_versions = os.path.join(home, ".tool-versions")
    if os.path.exists(home_tool_versions):
        tools = parse_tool_versions(home_tool_versions)
        if tool_name in tools:
            return tools[tool_name]

    # Check global version
    global_version_file = os.path.join(asdf_dir, "version", tool_name)
    if os.path.exists(global_version_file):
        with open(global_version_file, 'r') as f:
            return f.read().strip()

    return None

def get_installed_tools(asdf_dir):
    """Get list of all installed asdf tools"""
    installs_dir = os.path.join(asdf_dir, "installs")
    if os.path.exists(installs_dir):
        return [d for d in os.listdir(installs_dir)
                if os.path.isdir(os.path.join(installs_dir, d)) and not d.startswith('.')]
    return []

def add_to_path(new_path):
    """Add a path to PATH if not already present"""
    current_path = os.environ.get('PATH', '')
    path_parts = current_path.split(':')
    if new_path not in path_parts:
        os.environ['PATH'] = f"{new_path}:{current_path}"

def setup_tool_environment(tool_name, version, asdf_dir):
    """Set up environment for a specific tool"""
    install_path = os.path.join(asdf_dir, "installs", tool_name, version)

    if not os.path.exists(install_path):
        debug_print(f"Warning: {tool_name} {version} not installed at {install_path}")
        return False

    # Tool-specific environment setup
    tool_configs = {
        "golang": {
            "env": {
                "GOROOT": lambda: os.path.join(install_path, "go"),
                "GOPATH": lambda: os.environ.get('GOPATH', os.path.join(os.path.expanduser("~"), "go"))
            },
            "paths": [
                lambda: os.path.join(install_path, "go", "bin"),
                lambda: os.path.join(os.environ.get('GOPATH', os.path.join(os.path.expanduser("~"), "go")), "bin")
            ]
        },
        "nodejs": {
            "env": {
                "NODE_PATH": lambda: os.path.join(install_path, "lib", "node_modules")
            },
            "paths": [
                lambda: os.path.join(install_path, "bin")
            ]
        },
        "ruby": {
            "env": {
                "GEM_PATH": lambda: os.path.join(install_path, "lib", "ruby", "gems")
            },
            "paths": [
                lambda: os.path.join(install_path, "bin")
            ]
        },
        "rust": {
            "env": {
                "CARGO_HOME": lambda: install_path
            },
            "paths": [
                lambda: os.path.join(install_path, "bin")
            ]
        }
    }

    # Apply tool-specific configuration or use generic
    config = tool_configs.get(tool_name, {
        "paths": [lambda: os.path.join(install_path, "bin")]
    })

    # Set environment variables
    for var_name, var_func in config.get("env", {}).items():
        value = var_func()
        if value and os.path.exists(value):
            os.environ[var_name] = value
            debug_print(f"Set {var_name}: {value}")

    # Add paths
    for path_func in config.get("paths", []):
        path = path_func()
        if path and os.path.exists(path):
            add_to_path(path)

    return True

def setup_asdf_environment():
    """Main function to set up the complete asdf environment"""
    print("="*50)
    print("[sublime-asdf] Setting up environment...")

    home = os.path.expanduser("~")
    asdf_dir = os.path.join(home, ".asdf")

    if not os.path.exists(asdf_dir):
        print("[sublime-asdf] ERROR: asdf not found at ~/.asdf")
        return

    # Reset PATH to clean state
    system_paths = ['/usr/local/bin', '/usr/bin', '/bin', '/usr/sbin', '/sbin']
    os.environ['PATH'] = ':'.join(system_paths)

    # Add asdf paths
    asdf_shims = os.path.join(asdf_dir, "shims")
    asdf_bin = os.path.join(asdf_dir, "bin")

    for path in [asdf_shims, asdf_bin]:
        if os.path.exists(path):
            add_to_path(path)

    # Set asdf environment variables
    os.environ['ASDF_DIR'] = asdf_dir
    os.environ['ASDF_DATA_DIR'] = os.environ.get('ASDF_DATA_DIR', asdf_dir)

    # Get all installed tools
    installed_tools = get_installed_tools(asdf_dir)
    debug_print(f"Installed tools: {installed_tools}")

    # Set up each tool
    configured_tools = []
    for tool_name in installed_tools:
        version = get_tool_version(tool_name)
        if version:
            debug_print(f"Setting up {tool_name} {version}...")
            if setup_tool_environment(tool_name, version, asdf_dir):
                configured_tools.append(f"{tool_name}@{version}")

    # Update status bar if enabled
    if get_settings().get('show_status', True) and configured_tools:
        window = sublime.active_window()
        if window:
            for view in window.views():
                view.set_status('asdf', f"asdf: {', '.join(configured_tools)}")

    # Verify tools if in debug mode
    if get_settings().get('debug', False):
        verify_tools = get_settings().get('verify_tools', ['go', 'node', 'ruby', 'python'])
        print("\n[sublime-asdf] Verifying tools:")
        for cmd in verify_tools:
            try:
                result = subprocess.run(['which', cmd], capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"  ✓ {cmd}: {result.stdout.strip()}")
            except:
                pass

    # Restart LSP servers
    sublime.set_timeout(lambda: sublime.run_command("lsp_restart_server"), 1000)

    print("[sublime-asdf] Environment setup complete!")
    print("="*50)

def plugin_loaded():
    """Called when the plugin is loaded"""
    setup_asdf_environment()

class ReloadAsdfEnvironmentCommand(sublime_plugin.WindowCommand):
    """Command to manually reload asdf environment"""
    def run(self):
        setup_asdf_environment()
        self.window.status_message("asdf environment reloaded")

class ShowAsdfEnvironmentCommand(sublime_plugin.WindowCommand):
    """Command to show current environment in console"""
    def run(self):
        print("\n[sublime-asdf] Current Environment:")
        print(f"PATH: {os.environ.get('PATH', 'Not set')}")
        print(f"ASDF_DIR: {os.environ.get('ASDF_DIR', 'Not set')}")

        # Show tool-specific vars
        tool_vars = ['GOROOT', 'GOPATH', 'NODE_PATH', 'GEM_PATH', 'CARGO_HOME']
        for var in tool_vars:
            value = os.environ.get(var)
            if value:
                print(f"{var}: {value}")

class AsdfEnvironmentEventListener(sublime_plugin.EventListener):
    """Event listener for automatic environment updates"""

    def on_activated(self, view):
        """Reload when switching between windows"""
        if hasattr(self, '_last_window_id'):
            current_window_id = view.window().id() if view.window() else None
            if current_window_id != self._last_window_id:
                debug_print("Window changed, reloading environment...")
                setup_asdf_environment()

        if view.window():
            self._last_window_id = view.window().id()

    def on_post_save_async(self, view):
        """Reload when .tool-versions is saved"""
        if get_settings().get('auto_reload_on_save', True):
            if view.file_name() and view.file_name().endswith('.tool-versions'):
                print("[sublime-asdf] Detected .tool-versions change, reloading...")
                setup_asdf_environment()