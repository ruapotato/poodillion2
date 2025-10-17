#!/usr/bin/env python3
"""
Poodillion Web Server
Flask-based web interface for the Poodillion hacking game
"""

from flask import Flask, render_template, session, request
from flask_socketio import SocketIO, emit, join_room
import uuid
import threading
import time
from typing import Dict, Optional
from io import StringIO

from core.system import UnixSystem
from core.shell import ShellExecutor
from world_1990 import create_december_1990_world

app = Flask(__name__)
app.config['SECRET_KEY'] = 'poodillion-secret-key-change-in-production'
socketio = SocketIO(app, cors_allowed_origins="*")

# Session storage: session_id -> GameSession
sessions: Dict[str, 'GameSession'] = {}


class GameSession:
    """Manages a single player's game world and terminal session"""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.created_at = time.time()
        self.last_activity = time.time()

        # Create the game world for this player
        print(f"Creating game world for session {session_id}")
        attacker, network, all_systems = create_december_1990_world()

        # Store world components
        self.world = {
            'attacker': attacker,
            'network': network,
            'systems': network.systems,  # Dict of IP -> UnixSystem
            'all_systems': all_systems
        }

        # Start on the player's main system (the attacker)
        self.current_system_ip = attacker.ip
        self.current_system = attacker

        # Create shell executor for the current system
        self.shell = ShellExecutor(
            vfs=self.current_system.vfs,
            process_manager=self.current_system.process_manager,
            network=self.world.get('network'),
            system=self.current_system
        )

        # Get initial shell process (usually spawned by init -> login)
        # For simplicity, we'll use UID 0 (root) - adjust based on your world setup
        processes = self.current_system.process_manager.list_processes()
        shell_proc = None
        for proc in processes:
            if 'sh' in proc.command or 'shell' in proc.command:
                shell_proc = proc
                break

        if not shell_proc:
            # Create a shell process if none exists
            shell_proc = self.current_system.process_manager.spawn(
                parent_pid=1,
                uid=0,
                gid=0,
                euid=0,
                egid=0,
                command='/bin/sh',
                args=['/bin/sh'],
                cwd=1,  # root directory
                env={'PATH': '/bin:/usr/bin:/sbin:/usr/sbin', 'HOME': '/root', 'USER': 'root'},
                tags=[]
            )
            shell_proc = self.current_system.process_manager.get_process(shell_proc)

        self.shell_process = shell_proc

    def execute_command(self, command: str) -> tuple[str, str]:
        """
        Execute a command and return (stdout, stderr)
        """
        self.last_activity = time.time()

        try:
            # Execute the command using the shell executor
            exit_code, stdout, stderr = self.shell.execute_command(
                command,
                self.shell_process.pid,
                input_data=b''
            )

            return stdout.decode('utf-8', errors='ignore'), stderr.decode('utf-8', errors='ignore')

        except Exception as e:
            return "", f"Error: {str(e)}\n"

    def get_prompt(self) -> str:
        """Generate shell prompt"""
        proc = self.shell_process

        # Get username
        username = 'root' if proc.uid == 0 else f'user{proc.uid}'

        # Get hostname
        hostname = self.current_system.hostname

        # Get current directory
        cwd_inode = proc.cwd
        cwd_path = self._inode_to_path(cwd_inode)

        # Simplify home directory
        home = '/root' if proc.uid == 0 else f'/home/user{proc.uid}'
        if cwd_path.startswith(home):
            cwd_path = '~' + cwd_path[len(home):]

        # Use # for root, $ for others
        prompt_char = '#' if proc.uid == 0 else '$'

        return f"{username}@{hostname}:{cwd_path}{prompt_char} "

    def _inode_to_path(self, ino: int) -> str:
        """Convert inode number to path"""
        if ino == 1:
            return '/'

        vfs = self.current_system.vfs

        def find_path(target_ino, current_ino=1, current_path='/', visited=None):
            if visited is None:
                visited = set()

            if current_ino in visited:
                return None
            visited.add(current_ino)

            if current_ino == target_ino:
                return current_path

            inode = vfs.inodes.get(current_ino)
            if not inode or not inode.is_dir():
                return None

            entries = inode.content
            if not isinstance(entries, dict):
                return None

            for name, child_ino in entries.items():
                if name in ('.', '..'):
                    continue

                child_path = current_path + name if current_path == '/' else current_path + '/' + name
                result = find_path(target_ino, child_ino, child_path, visited)
                if result:
                    return result

            return None

        path = find_path(ino)
        return path or '???'


def get_or_create_session(session_id: str) -> GameSession:
    """Get existing session or create new one"""
    if session_id not in sessions:
        sessions[session_id] = GameSession(session_id)
    return sessions[session_id]


def cleanup_old_sessions():
    """Remove sessions inactive for more than 1 hour"""
    while True:
        time.sleep(300)  # Check every 5 minutes
        now = time.time()
        to_remove = []

        for sid, sess in sessions.items():
            if now - sess.last_activity > 3600:  # 1 hour
                to_remove.append(sid)

        for sid in to_remove:
            print(f"Removing inactive session {sid}")
            del sessions[sid]


# Start cleanup thread
cleanup_thread = threading.Thread(target=cleanup_old_sessions, daemon=True)
cleanup_thread.start()


@app.route('/')
def index():
    """Main page with terminal interface"""
    # Generate or get session ID
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())

    return render_template('index.html', session_id=session['session_id'])


@socketio.on('connect')
def handle_connect():
    """Handle new WebSocket connection"""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())

    session_id = session['session_id']
    join_room(session_id)

    # Get or create game session
    game_session = get_or_create_session(session_id)

    # Send initial prompt
    emit('output', {
        'data': f"Welcome to Poodillion - The 1990s Hacking Simulator\n"
                f"Type 'help' for available commands\n\n"
                f"{game_session.get_prompt()}"
    })

    print(f"Client connected: {session_id}")


@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection"""
    print(f"Client disconnected")


@socketio.on('input')
def handle_input(data):
    """Handle terminal input from client"""
    session_id = session.get('session_id')
    if not session_id:
        return

    command = data.get('data', '').strip()

    # Get game session
    game_session = get_or_create_session(session_id)

    # Special commands
    if command in ('exit', 'quit'):
        emit('output', {'data': '\nGoodbye!\n'})
        return

    # Execute command
    if command:
        stdout, stderr = game_session.execute_command(command)

        # Send output
        if stdout:
            emit('output', {'data': stdout})
        if stderr:
            emit('output', {'data': stderr})

    # Send new prompt
    emit('output', {'data': game_session.get_prompt()})


@app.route('/about')
def about():
    """About page"""
    return render_template('about.html')


@app.route('/stats')
def stats():
    """Server statistics"""
    return {
        'active_sessions': len(sessions),
        'sessions': [
            {
                'id': sid[:8] + '...',
                'age_minutes': int((time.time() - s.created_at) / 60),
                'idle_minutes': int((time.time() - s.last_activity) / 60)
            }
            for sid, s in sessions.items()
        ]
    }


if __name__ == '__main__':
    print("=" * 60)
    print("Poodillion Web Server")
    print("=" * 60)
    print("\nStarting server on http://localhost:5000")
    print("Press Ctrl+C to stop\n")

    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
