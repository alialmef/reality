"""
Music controller - controls music playback.
macOS: Uses AppleScript to control Apple Music/Spotify
Windows: Uses Spotify global hotkeys (limited functionality)
"""

import platform
import subprocess
from typing import Optional

PLATFORM = platform.system()  # "Darwin" for macOS, "Windows" for Windows


class MusicController:
    """
    Controls music playback on macOS via AppleScript.
    Supports Apple Music (preferred) and Spotify.
    Can route music to a specific speaker.
    """

    def __init__(self, default_app: str = "Music", music_speaker: str = "External Headphones"):
        """
        Initialize the music controller.

        Args:
            default_app: "Music" for Apple Music, "Spotify" for Spotify
            music_speaker: Name of the audio output device for music
        """
        self.default_app = default_app
        self.music_speaker = music_speaker
        print(f"[Music] Controller initialized (default: {default_app}, speaker: {music_speaker})")

    def _run_command(self, cmd: list) -> tuple[bool, str]:
        """Run a shell command and return (success, output)."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return True, result.stdout.strip()
            else:
                return False, result.stderr.strip()
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except Exception as e:
            return False, str(e)

    def _switch_audio_output(self, device_name: str) -> bool:
        """Switch system audio output to specified device."""
        if PLATFORM == "Darwin":
            success, output = self._run_command(["SwitchAudioSource", "-s", device_name])
        elif PLATFORM == "Windows":
            # On Windows, audio device switching requires additional tools
            # For now, we skip automatic switching - user sets default in Windows
            print(f"[Music] Audio switching not implemented on Windows")
            return True
        else:
            return False

        if success:
            print(f"[Music] Switched audio to: {device_name}")
            return True
        else:
            print(f"[Music] Failed to switch audio: {output}")
            return False

    def _get_current_output(self) -> str:
        """Get current audio output device name."""
        if PLATFORM == "Darwin":
            success, output = self._run_command(["SwitchAudioSource", "-c"])
            return output if success else "Unknown"
        return "Default"

    def _ensure_music_speaker(self) -> None:
        """Switch to the music speaker if not already active."""
        if PLATFORM != "Darwin":
            return  # Skip on non-macOS
        current = self._get_current_output()
        if current != self.music_speaker:
            self._switch_audio_output(self.music_speaker)

    def _run_applescript(self, script: str) -> tuple[bool, str]:
        """Run an AppleScript command and return (success, output). macOS only."""
        if PLATFORM != "Darwin":
            return False, "AppleScript not available on this platform"
        return self._run_command(["osascript", "-e", script])

    def _run_powershell(self, script: str) -> tuple[bool, str]:
        """Run a PowerShell command and return (success, output). Windows only."""
        if PLATFORM != "Windows":
            return False, "PowerShell not available on this platform"
        return self._run_command(["powershell", "-Command", script])

    def _send_media_key(self, key: str) -> tuple[bool, str]:
        """Send a media key on Windows. Keys: play, pause, next, prev"""
        if PLATFORM != "Windows":
            return False, "Media keys only on Windows"
        # Use PowerShell to send media keys
        key_map = {
            "play": "0xB3",      # VK_MEDIA_PLAY_PAUSE
            "pause": "0xB3",     # VK_MEDIA_PLAY_PAUSE
            "next": "0xB0",      # VK_MEDIA_NEXT_TRACK
            "prev": "0xB1",      # VK_MEDIA_PREV_TRACK
        }
        vk = key_map.get(key)
        if not vk:
            return False, f"Unknown media key: {key}"

        ps_script = f'''
        Add-Type -TypeDefinition '
        using System;
        using System.Runtime.InteropServices;
        public class Keyboard {{
            [DllImport("user32.dll")]
            public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, UIntPtr dwExtraInfo);
        }}
        '
        [Keyboard]::keybd_event({vk}, 0, 0, [UIntPtr]::Zero)
        [Keyboard]::keybd_event({vk}, 0, 2, [UIntPtr]::Zero)
        '''
        return self._run_powershell(ps_script)

    def play(self, app: str = None) -> str:
        """Start or resume playback."""
        app = app or self.default_app
        self._ensure_music_speaker()

        if PLATFORM == "Darwin":
            success, output = self._run_applescript(f'tell application "{app}" to play')
            if success:
                return f"Playing on {app}"
            return f"Error: {output}"
        elif PLATFORM == "Windows":
            success, _ = self._send_media_key("play")
            if success:
                return "Playing"
            return "Error sending play command"
        return "Playback control not available on this platform"

    def pause(self, app: str = None) -> str:
        """Pause playback."""
        app = app or self.default_app

        if PLATFORM == "Darwin":
            success, output = self._run_applescript(f'tell application "{app}" to pause')
            if success:
                return f"Paused {app}"
            return f"Error: {output}"
        elif PLATFORM == "Windows":
            success, _ = self._send_media_key("pause")
            if success:
                return "Paused"
            return "Error sending pause command"
        return "Playback control not available on this platform"

    def toggle_playback(self, app: str = None) -> str:
        """Toggle play/pause."""
        app = app or self.default_app

        if PLATFORM == "Darwin":
            success, output = self._run_applescript(f'tell application "{app}" to playpause')
            if success:
                return f"Toggled playback on {app}"
            return f"Error: {output}"
        elif PLATFORM == "Windows":
            success, _ = self._send_media_key("play")
            if success:
                return "Toggled playback"
            return "Error toggling playback"
        return "Playback control not available on this platform"

    def next_track(self, app: str = None) -> str:
        """Skip to next track."""
        app = app or self.default_app

        if PLATFORM == "Darwin":
            success, output = self._run_applescript(f'tell application "{app}" to next track')
            if success:
                return "Skipped to next track"
            return f"Error: {output}"
        elif PLATFORM == "Windows":
            success, _ = self._send_media_key("next")
            if success:
                return "Skipped to next track"
            return "Error skipping track"
        return "Playback control not available on this platform"

    def previous_track(self, app: str = None) -> str:
        """Go to previous track."""
        app = app or self.default_app

        if PLATFORM == "Darwin":
            success, output = self._run_applescript(f'tell application "{app}" to previous track')
            if success:
                return "Went to previous track"
            return f"Error: {output}"
        elif PLATFORM == "Windows":
            success, _ = self._send_media_key("prev")
            if success:
                return "Went to previous track"
            return "Error going to previous track"
        return "Playback control not available on this platform"

    def set_volume(self, level: int, app: str = None) -> str:
        """
        Set SYSTEM volume level (0-100).
        This controls the actual speaker output, not the app's internal volume.
        """
        level = max(0, min(100, level))

        if PLATFORM == "Darwin":
            success, output = self._run_applescript(f'set volume output volume {level}')
        elif PLATFORM == "Windows":
            # Use PowerShell to set volume (requires audio cmdlet or nircmd)
            # Scale 0-100 to 0-65535 for Windows
            win_level = int(level * 65535 / 100)
            ps_script = f'''
            $obj = New-Object -ComObject WScript.Shell
            1..50 | ForEach-Object {{ $obj.SendKeys([char]174) }}
            1..{level // 2} | ForEach-Object {{ $obj.SendKeys([char]175) }}
            '''
            # Simpler approach: just report success, actual control via nircmd if installed
            success, output = self._run_command(["nircmd", "setsysvolume", str(win_level)])
            if not success:
                return f"Volume control requires nircmd on Windows. Install from nirsoft.net"
        else:
            return "Volume control not available on this platform"

        if success:
            return f"System volume set to {level}%"
        return f"Error: {output}"

    def adjust_volume(self, direction: str) -> str:
        """
        Adjust system volume up or down by ~15%.
        direction: 'up' or 'down'
        """
        if PLATFORM == "Darwin":
            # Get current volume
            success, output = self._run_applescript('output volume of (get volume settings)')
            if not success:
                return f"Error getting volume: {output}"
            try:
                current = int(output)
            except ValueError:
                return f"Error parsing volume: {output}"

            # Adjust by 15%
            if direction == "up":
                new_level = min(100, current + 15)
            else:
                new_level = max(0, current - 15)
            return self.set_volume(new_level)

        elif PLATFORM == "Windows":
            # Use nircmd for volume adjustment
            if direction == "up":
                success, output = self._run_command(["nircmd", "changesysvolume", "10000"])
            else:
                success, output = self._run_command(["nircmd", "changesysvolume", "-10000"])
            if success:
                return f"Volume adjusted {direction}"
            return f"Volume control requires nircmd on Windows"

        return "Volume control not available on this platform"

    def get_volume(self, app: str = None) -> str:
        """Get current SYSTEM volume level."""
        if PLATFORM == "Darwin":
            success, output = self._run_applescript('output volume of (get volume settings)')
            if success:
                return f"System volume is at {output}%"
            return f"Error: {output}"
        return "Volume query not available on this platform"

    def get_volume_level(self) -> Optional[int]:
        """Get current system volume as an integer (0-100), or None on error."""
        if PLATFORM == "Darwin":
            success, output = self._run_applescript('output volume of (get volume settings)')
            if success:
                try:
                    return int(output)
                except ValueError:
                    return None
        return None

    def duck(self, duck_level: int = 15) -> Optional[int]:
        """
        Duck (lower) the music volume for voice interaction.
        Returns the original volume level so it can be restored later.
        """
        original = self.get_volume_level()
        if original is not None and original > duck_level:
            self._run_applescript(f'set volume output volume {duck_level}')
            print(f"[Music] Ducked volume: {original}% -> {duck_level}%")
        return original

    def restore(self, original_volume: Optional[int]) -> None:
        """Restore volume to the original level after ducking."""
        if original_volume is not None:
            self._run_applescript(f'set volume output volume {original_volume}')
            print(f"[Music] Restored volume to {original_volume}%")

    def get_current_track(self, app: str = None) -> str:
        """Get info about the currently playing track."""
        if PLATFORM != "Darwin":
            return "Track info not available on this platform"

        app = app or self.default_app

        if app == "Music":
            script = '''
            tell application "Music"
                if player state is playing then
                    set trackName to name of current track
                    set artistName to artist of current track
                    set albumName to album of current track
                    return trackName & " by " & artistName & " from " & albumName
                else if player state is paused then
                    set trackName to name of current track
                    set artistName to artist of current track
                    return trackName & " by " & artistName & " (paused)"
                else
                    return "Nothing playing"
                end if
            end tell
            '''
        else:  # Spotify
            script = '''
            tell application "Spotify"
                if player state is playing then
                    set trackName to name of current track
                    set artistName to artist of current track
                    set albumName to album of current track
                    return trackName & " by " & artistName & " from " & albumName
                else if player state is paused then
                    set trackName to name of current track
                    set artistName to artist of current track
                    return trackName & " by " & artistName & " (paused)"
                else
                    return "Nothing playing"
                end if
            end tell
            '''

        success, output = self._run_applescript(script)
        if success:
            return output
        return f"Error: {output}"

    def get_player_state(self, app: str = None) -> str:
        """Get the current player state (playing, paused, stopped)."""
        if PLATFORM != "Darwin":
            return "Unknown"

        app = app or self.default_app
        success, output = self._run_applescript(
            f'tell application "{app}" to get player state as string'
        )
        if success:
            return output
        return f"Error: {output}"

    def search_and_play(self, query: str, app: str = None) -> str:
        """
        Search for and play music matching the query.
        macOS: Apple Music searches local library, Spotify uses URI scheme.
        Windows: Uses Spotify URI scheme.
        """
        import urllib.parse

        app = app or self.default_app
        self._ensure_music_speaker()

        # Spotify URI scheme works on both platforms
        if app == "Spotify" or PLATFORM == "Windows":
            encoded_query = urllib.parse.quote(query)

            if PLATFORM == "Darwin":
                self._run_command(["open", f"spotify:search:{encoded_query}"])
            elif PLATFORM == "Windows":
                # Use cmd /c start to open URI on Windows
                subprocess.run(f'start spotify:search:{encoded_query}', shell=True)

            return f"Searching for '{query}' on Spotify"

        elif PLATFORM == "Darwin" and app == "Music":
            # Search Apple Music library and play first match
            script = f'''
            tell application "Music"
                set searchResults to search playlist "Library" for "{query}"
                if searchResults is not {{}} then
                    play item 1 of searchResults
                    set trackName to name of current track
                    set artistName to artist of current track
                    return "Playing " & trackName & " by " & artistName
                else
                    return "No results found for {query}"
                end if
            end tell
            '''
            success, output = self._run_applescript(script)
            if success:
                return output
            return f"Error searching for '{query}': {output}"

        return "Music search not available on this platform"

    def play_playlist(self, playlist_name: str, app: str = None) -> str:
        """Play a playlist by name."""
        app = app or self.default_app
        self._ensure_music_speaker()

        if app == "Music":
            script = f'''
            tell application "Music"
                play playlist "{playlist_name}"
                return "Playing playlist: {playlist_name}"
            end tell
            '''
        else:  # Spotify
            script = f'''
            tell application "Spotify"
                set targetPlaylist to "{playlist_name}"
                -- Spotify AppleScript is more limited, try to play by name
                play track targetPlaylist
                return "Playing: {playlist_name}"
            end tell
            '''

        success, output = self._run_applescript(script)
        if success:
            return output
        return f"Error playing playlist '{playlist_name}': {output}"

    def shuffle(self, enabled: bool = True, app: str = None) -> str:
        """Enable or disable shuffle."""
        app = app or self.default_app
        value = "true" if enabled else "false"
        success, output = self._run_applescript(
            f'tell application "{app}" to set shuffling to {value}'
        )
        if success:
            state = "on" if enabled else "off"
            return f"Shuffle {state}"
        return f"Error: {output}"

    def repeat(self, mode: str = "all", app: str = None) -> str:
        """
        Set repeat mode.
        Modes: "off", "one", "all"
        """
        app = app or self.default_app

        if app == "Music":
            mode_map = {"off": "off", "one": "one", "all": "all"}
            apple_mode = mode_map.get(mode, "off")
            success, output = self._run_applescript(
                f'tell application "Music" to set song repeat to {apple_mode}'
            )
        else:  # Spotify
            # Spotify uses true/false for repeating
            value = "true" if mode != "off" else "false"
            success, output = self._run_applescript(
                f'tell application "Spotify" to set repeating to {value}'
            )

        if success:
            return f"Repeat set to {mode}"
        return f"Error: {output}"

    def get_status(self, app: str = None) -> str:
        """Get full playback status."""
        app = app or self.default_app

        state = self.get_player_state(app)
        track = self.get_current_track(app)
        volume = self.get_volume(app)

        return f"Status: {state}\nTrack: {track}\n{volume}"


# Singleton instance
_controller = None


def get_music_controller() -> MusicController:
    """Get the music controller singleton."""
    global _controller
    if _controller is None:
        _controller = MusicController(default_app="Music")
    return _controller
