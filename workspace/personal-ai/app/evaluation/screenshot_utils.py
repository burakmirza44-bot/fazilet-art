"""Screenshot Utilities Module.

Provides screenshot capture capabilities for TouchDesigner and Houdini
applications for visual verification.
"""

from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ScreenshotResult:
    """Result of screenshot capture."""

    success: bool = False
    filepath: str = ""
    error: str = ""
    timestamp: float = 0.0

    def __post_init__(self) -> None:
        """Set timestamp if not set."""
        if self.timestamp == 0.0:
            object.__setattr__(self, "timestamp", time.time())


class ScreenshotCapture:
    """Screenshot capture utility for applications.

    Supports multiple capture methods:
    - Platform-specific (Windows/macOS/Linux)
    - Application-specific (if app provides API)
    - Window-specific (capture specific window by title)
    """

    def __init__(self, output_dir: str = "data/screenshots"):
        """Initialize screenshot capture.

        Args:
            output_dir: Directory to save screenshots
        """
        self._output_dir = output_dir
        self._ensure_output_dir()

    def _ensure_output_dir(self) -> None:
        """Ensure output directory exists."""
        Path(self._output_dir).mkdir(parents=True, exist_ok=True)

    def capture_fullscreen(self, filename: str | None = None) -> ScreenshotResult:
        """Capture full screen screenshot.

        Args:
            filename: Optional filename (auto-generated if None)

        Returns:
            ScreenshotResult with filepath or error
        """
        if filename is None:
            filename = f"fullscreen_{int(time.time() * 1000)}.png"

        filepath = os.path.join(self._output_dir, filename)

        try:
            import platform

            system = platform.system()

            if system == "Windows":
                return self._capture_windows(filepath)
            elif system == "Darwin":  # macOS
                return self._capture_macos(filepath)
            elif system == "Linux":
                return self._capture_linux(filepath)
            else:
                return ScreenshotResult(
                    success=False,
                    error=f"Unsupported platform: {system}",
                )

        except Exception as e:
            return ScreenshotResult(
                success=False,
                error=f"Screenshot failed: {str(e)}",
            )

    def capture_window(self, window_title: str, filename: str | None = None) -> ScreenshotResult:
        """Capture specific window by title.

        Args:
            window_title: Title of window to capture
            filename: Optional filename

        Returns:
            ScreenshotResult with filepath or error
        """
        if filename is None:
            filename = f"window_{window_title.replace(' ', '_')}_{int(time.time() * 1000)}.png"

        filepath = os.path.join(self._output_dir, filename)

        try:
            import platform

            system = platform.system()

            if system == "Windows":
                return self._capture_window_windows(window_title, filepath)
            elif system == "Darwin":
                return self._capture_window_macos(window_title, filepath)
            elif system == "Linux":
                return self._capture_window_linux(window_title, filepath)
            else:
                return ScreenshotResult(
                    success=False,
                    error=f"Unsupported platform: {system}",
                )

        except Exception as e:
            return ScreenshotResult(
                success=False,
                error=f"Window screenshot failed: {str(e)}",
            )

    def _capture_windows(self, filepath: str) -> ScreenshotResult:
        """Capture screenshot on Windows.

        Args:
            filepath: Path to save screenshot

        Returns:
            ScreenshotResult
        """
        try:
            # Try using PIL/Pillow first
            from PIL import ImageGrab

            screenshot = ImageGrab.grab()
            screenshot.save(filepath)

            return ScreenshotResult(success=True, filepath=filepath)

        except ImportError:
            # Fallback to PowerShell
            ps_script = f'''
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bitmap = New-Object System.Drawing.Bitmap($screen.Width, $screen.Height)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size)
$bitmap.Save("{filepath}")
$graphics.Dispose()
$bitmap.Dispose()
'''
            try:
                subprocess.run(
                    ["powershell", "-Command", ps_script],
                    check=True,
                    capture_output=True,
                )
                return ScreenshotResult(success=True, filepath=filepath)
            except subprocess.CalledProcessError as e:
                return ScreenshotResult(
                    success=False,
                    error=f"PowerShell screenshot failed: {e.stderr.decode()}",
                )

    def _capture_macos(self, filepath: str) -> ScreenshotResult:
        """Capture screenshot on macOS.

        Args:
            filepath: Path to save screenshot

        Returns:
            ScreenshotResult
        """
        try:
            subprocess.run(
                ["screencapture", filepath],
                check=True,
                capture_output=True,
            )
            return ScreenshotResult(success=True, filepath=filepath)
        except subprocess.CalledProcessError as e:
            return ScreenshotResult(
                success=False,
                error=f"screencapture failed: {e.stderr.decode()}",
            )

    def _capture_linux(self, filepath: str) -> ScreenshotResult:
        """Capture screenshot on Linux.

        Args:
            filepath: Path to save screenshot

        Returns:
            ScreenshotResult
        """
        # Try gnome-screenshot first, then fallback to import
        for cmd in [
            ["gnome-screenshot", "-f", filepath],
            ["import", "-window", "root", filepath],
        ]:
            try:
                subprocess.run(cmd, check=True, capture_output=True)
                return ScreenshotResult(success=True, filepath=filepath)
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue

        return ScreenshotResult(
            success=False,
            error="No screenshot tool found (tried gnome-screenshot, ImageMagick)",
        )

    def _capture_window_windows(self, window_title: str, filepath: str) -> ScreenshotResult:
        """Capture specific window on Windows.

        Args:
            window_title: Title of window to capture
            filepath: Path to save screenshot

        Returns:
            ScreenshotResult
        """
        try:
            import win32gui
            import win32ui
            import win32con
            from PIL import Image

            # Find window
            hwnd = win32gui.FindWindow(None, window_title)
            if not hwnd:
                # Try partial match
                def callback(hwnd, extra):
                    if win32gui.IsWindowVisible(hwnd):
                        title = win32gui.GetWindowText(hwnd)
                        if window_title.lower() in title.lower():
                            extra.append(hwnd)

                windows = []
                win32gui.EnumWindows(callback, windows)
                if windows:
                    hwnd = windows[0]

            if not hwnd:
                return ScreenshotResult(
                    success=False,
                    error=f"Window not found: {window_title}",
                )

            # Get window dimensions
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width = right - left
            height = bottom - top

            # Capture
            hwndDC = win32gui.GetWindowDC(hwnd)
            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()

            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
            saveDC.SelectObject(saveBitMap)
            saveDC.BitBlt((0, 0), (width, height), mfcDC, (0, 0), win32con.SRCCOPY)

            # Convert to PIL Image and save
            bmpinfo = saveBitMap.GetInfo()
            bmpstr = saveBitMap.GetBitmapBits(True)
            im = Image.frombuffer(
                "RGB",
                (bmpinfo["bmWidth"], bmpinfo["bmHeight"]),
                bmpstr,
                "raw",
                "BGRX",
                0,
                1,
            )
            im.save(filepath)

            # Cleanup
            win32gui.DeleteObject(saveBitMap.GetHandle())
            saveDC.DeleteDC()
            mfcDC.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwndDC)

            return ScreenshotResult(success=True, filepath=filepath)

        except ImportError as e:
            return ScreenshotResult(
                success=False,
                error=f"Required library not available: {e}",
            )
        except Exception as e:
            return ScreenshotResult(
                success=False,
                error=f"Window capture failed: {str(e)}",
            )

    def _capture_window_macos(self, window_title: str, filepath: str) -> ScreenshotResult:
        """Capture specific window on macOS.

        Args:
            window_title: Title of window to capture
            filepath: Path to save screenshot

        Returns:
            ScreenshotResult
        """
        # macOS doesn't have a direct window capture command
        # Use AppleScript to get window bounds and capture region
        try:
            applescript = f'''
tell application "System Events"
    tell process "{window_title}"
        set winPos to position of window 1
        set winSize to size of window 1
        return "{{" & (item 1 of winPos) & "," & (item 2 of winPos) & "," & (item 1 of winSize) & "," & (item 2 of winSize) & "}}"
    end tell
end tell
'''
            result = subprocess.run(
                ["osascript", "-e", applescript],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                # Parse bounds and capture region
                bounds = result.stdout.strip()
                # Capture using screencapture with region
                subprocess.run(
                    ["screencapture", "-R" + bounds.replace("{", "").replace("}", "").replace(",", ","), filepath],
                    check=True,
                )
                return ScreenshotResult(success=True, filepath=filepath)
            else:
                # Fallback to full screen
                return self._capture_macos(filepath)

        except Exception as e:
            return ScreenshotResult(
                success=False,
                error=f"macOS window capture failed: {str(e)}",
            )

    def _capture_window_linux(self, window_title: str, filepath: str) -> ScreenshotResult:
        """Capture specific window on Linux.

        Args:
            window_title: Title of window to capture
            filepath: Path to save screenshot

        Returns:
            ScreenshotResult
        """
        try:
            # Try import with window ID
            result = subprocess.run(
                ["xdotool", "search", "--name", window_title],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                window_id = result.stdout.strip().split("\n")[0]
                subprocess.run(
                    ["import", "-window", window_id, filepath],
                    check=True,
                )
                return ScreenshotResult(success=True, filepath=filepath)
            else:
                return ScreenshotResult(
                    success=False,
                    error=f"Window not found: {window_title}",
                )

        except FileNotFoundError:
            return ScreenshotResult(
                success=False,
                error="xdotool or ImageMagick not installed",
            )
        except Exception as e:
            return ScreenshotResult(
                success=False,
                error=f"Linux window capture failed: {str(e)}",
            )


class TDScreenshotCapture(ScreenshotCapture):
    """Screenshot capture specifically for TouchDesigner."""

    def __init__(self, output_dir: str = "data/screenshots/touchdesigner"):
        """Initialize TD screenshot capture.

        Args:
            output_dir: Directory to save screenshots
        """
        super().__init__(output_dir)

    def capture_td_window(self, filename: str | None = None) -> ScreenshotResult:
        """Capture TouchDesigner main window.

        Args:
            filename: Optional filename

        Returns:
            ScreenshotResult
        """
        if filename is None:
            filename = f"td_{int(time.time() * 1000)}.png"

        # Try to find TouchDesigner window
        window_titles = [
            "TouchDesigner",
            "TouchDesigner 202",
            "TouchDesigner -",
            "TD",
        ]

        for title in window_titles:
            result = self.capture_window(title, filename)
            if result.success:
                return result

        # Fallback to fullscreen
        return self.capture_fullscreen(filename)

    def capture_td_network(self, filename: str | None = None) -> ScreenshotResult:
        """Capture TouchDesigner network view.

        Args:
            filename: Optional filename

        Returns:
            ScreenshotResult
        """
        if filename is None:
            filename = f"td_network_{int(time.time() * 1000)}.png"

        # Try to capture the network editor window specifically
        return self.capture_td_window(filename)


class HoudiniScreenshotCapture(ScreenshotCapture):
    """Screenshot capture specifically for Houdini."""

    def __init__(self, output_dir: str = "data/screenshots/houdini"):
        """Initialize Houdini screenshot capture.

        Args:
            output_dir: Directory to save screenshots
        """
        super().__init__(output_dir)

    def capture_houdini_window(self, filename: str | None = None) -> ScreenshotResult:
        """Capture Houdini main window.

        Args:
            filename: Optional filename

        Returns:
            ScreenshotResult
        """
        if filename is None:
            filename = f"houdini_{int(time.time() * 1000)}.png"

        # Try to find Houdini window
        window_titles = [
            "Houdini",
            "Houdini FX",
            "Houdini Core",
            "Houdini Apprentice",
        ]

        for title in window_titles:
            result = self.capture_window(title, filename)
            if result.success:
                return result

        # Fallback to fullscreen
        return self.capture_fullscreen(filename)

    def capture_houdini_network(self, filename: str | None = None) -> ScreenshotResult:
        """Capture Houdini network view.

        Args:
            filename: Optional filename

        Returns:
            ScreenshotResult
        """
        if filename is None:
            filename = f"houdini_network_{int(time.time() * 1000)}.png"

        return self.capture_houdini_window(filename)


# Convenience functions for quick access

def take_td_screenshot(filename: str | None = None, output_dir: str = "data/screenshots") -> str:
    """Take a TouchDesigner screenshot.

    Args:
        filename: Optional filename
        output_dir: Output directory

    Returns:
        Path to screenshot file (empty string on failure)
    """
    capture = TDScreenshotCapture(output_dir=os.path.join(output_dir, "touchdesigner"))
    result = capture.capture_td_window(filename)
    return result.filepath if result.success else ""


def take_houdini_screenshot(filename: str | None = None, output_dir: str = "data/screenshots") -> str:
    """Take a Houdini screenshot.

    Args:
        filename: Optional filename
        output_dir: Output directory

    Returns:
        Path to screenshot file (empty string on failure)
    """
    capture = HoudiniScreenshotCapture(output_dir=os.path.join(output_dir, "houdini"))
    result = capture.capture_houdini_window(filename)
    return result.filepath if result.success else ""


def take_screenshot(
    app: str,
    label: str = "",
    output_dir: str = "data/screenshots",
) -> str:
    """Take a screenshot for any supported application.

    Args:
        app: Application type (touchdesigner, houdini, or generic)
        label: Label for screenshot filename
        output_dir: Output directory

    Returns:
        Path to screenshot file (empty string on failure)
    """
    timestamp = int(time.time() * 1000)
    filename = f"{app}_{label}_{timestamp}.png" if label else f"{app}_{timestamp}.png"

    if app == "touchdesigner":
        return take_td_screenshot(filename, output_dir)
    elif app == "houdini":
        return take_houdini_screenshot(filename, output_dir)
    else:
        capture = ScreenshotCapture(output_dir)
        result = capture.capture_fullscreen(filename)
        return result.filepath if result.success else ""
