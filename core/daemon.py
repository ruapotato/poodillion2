"""
Background Daemon/Process Support

Allows PooScript daemons to run continuously in background threads
while the main system continues operating.
"""

import threading
import time
from typing import Dict, Optional

class BackgroundDaemon:
    """Represents a running background daemon"""

    def __init__(self, pid: int, name: str, system: 'UnixSystem'):
        self.pid = pid
        self.name = name
        self.system = system
        self.thread: Optional[threading.Thread] = None
        self.running = False
        self.exit_code: Optional[int] = None
        self.stdout_buffer = []
        self.stderr_buffer = []

    def start(self, script_path: str):
        """Start daemon in background thread"""
        self.running = True

        def run_daemon():
            """Run daemon script in thread"""
            try:
                # Execute the daemon script as PID 1 (init process)
                # Daemons are children of init in Unix
                # This will block in the thread, not the main process
                exit_code, stdout, stderr = self.system.shell.execute(
                    script_path,
                    1,  # Execute as child of init (PID 1)
                    b''
                )
                self.exit_code = exit_code
                self.stdout_buffer.append(stdout)
                self.stderr_buffer.append(stderr)
            except Exception as e:
                self.exit_code = 1
                self.stderr_buffer.append(f"Daemon error: {e}\n".encode())
                import traceback
                self.stderr_buffer.append(traceback.format_exc().encode())
            finally:
                self.running = False

        self.thread = threading.Thread(
            target=run_daemon,
            name=f"daemon-{self.name}-{self.pid}",
            daemon=True  # Thread dies when main program exits
        )
        self.thread.start()

    def stop(self):
        """Stop the daemon (send signal)"""
        self.running = False
        # In a real system, this would send SIGTERM
        # For now, the daemon's while loop should check if system is shutting down

    def is_alive(self) -> bool:
        """Check if daemon is still running"""
        return self.running and (self.thread is None or self.thread.is_alive())


class DaemonManager:
    """Manages all background daemons"""

    def __init__(self):
        self.daemons: Dict[int, BackgroundDaemon] = {}
        self.next_daemon_id = 1000  # Start daemon PIDs at 1000

    def spawn_daemon(self, name: str, script_path: str, system: 'UnixSystem') -> int:
        """
        Spawn a background daemon

        Returns the daemon's PID
        """
        pid = self.next_daemon_id
        self.next_daemon_id += 1

        daemon = BackgroundDaemon(pid, name, system)
        self.daemons[pid] = daemon

        # Start daemon in background thread
        daemon.start(script_path)

        # Give it a moment to start
        time.sleep(0.1)

        return pid

    def get_daemon(self, pid: int) -> Optional[BackgroundDaemon]:
        """Get daemon by PID"""
        return self.daemons.get(pid)

    def stop_daemon(self, pid: int):
        """Stop a daemon"""
        daemon = self.daemons.get(pid)
        if daemon:
            daemon.stop()

    def stop_all(self):
        """Stop all daemons"""
        for daemon in self.daemons.values():
            daemon.stop()

    def list_daemons(self):
        """List all running daemons"""
        return [
            (pid, daemon.name, daemon.is_alive())
            for pid, daemon in self.daemons.items()
        ]
