#!/usr/bin/env python3
"""
Poodillion Web Server
Flask-based web interface for the Poodillion hacking game
"""

from flask import Flask, render_template, session, request, jsonify
from flask_socketio import SocketIO, emit, join_room
import uuid
import threading
import time
from typing import Dict, Optional
from io import StringIO

from core.system import UnixSystem
from core.shell import Shell
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

        # Multiple shell sessions - each terminal gets its own
        self.shells = {}  # shell_id -> {'shell': Shell, 'process': Process}
        self.shell_counter = 0

    def create_shell(self) -> str:
        """Create a new shell session with its own PTY and return its ID"""
        self.shell_counter += 1
        shell_id = f"shell-{self.shell_counter}"

        # Create a PTY pair for this terminal
        master_path, slave_path, master_tty, slave_tty = self.current_system.create_pty_pair()

        # Create a NEW Shell instance for this terminal (critical for isolation)
        from core.shell import Shell
        shell = Shell(
            self.current_system.vfs,
            self.current_system.permissions,
            self.current_system.processes,
            self.current_system.network,
            self.current_system.ip,
            system=self.current_system
        )

        # Create a shell process with this PTY
        shell_proc_id = self.current_system.processes.spawn(
            parent_pid=1,
            uid=0,
            gid=0,
            euid=0,
            egid=0,
            command='/bin/sh',
            args=['/bin/sh'],
            cwd=1,  # root directory
            env={
                'PATH': '/bin:/usr/bin:/sbin:/usr/sbin',
                'HOME': '/root',
                'USER': 'root',
                'TERM': 'xterm',
                'TTY': slave_path
            },
            tags=['shell', f'tty:{slave_path}']
        )
        shell_proc = self.current_system.processes.get_process(shell_proc_id)

        # Attach TTY to process
        if shell_proc:
            shell_proc.tty = slave_tty

        # Store shell info with TTY references
        self.shells[shell_id] = {
            'shell': shell,
            'process': shell_proc,
            'master_tty': master_tty,
            'slave_tty': slave_tty,
            'master_path': master_path,
            'slave_path': slave_path
        }

        return shell_id

    def execute_command(self, shell_id: str, command: str) -> tuple[str, str]:
        """
        Execute a command in a specific shell and return (stdout, stderr)
        """
        self.last_activity = time.time()

        if shell_id not in self.shells:
            return "", f"Error: Invalid shell session\n"

        try:
            shell_info = self.shells[shell_id]
            shell = shell_info['shell']
            shell_proc = shell_info['process']

            # Execute the command using the shell
            exit_code, stdout, stderr = shell.execute(
                command,
                shell_proc.pid,
                input_data=b''
            )

            return stdout.decode('utf-8', errors='ignore'), stderr.decode('utf-8', errors='ignore')

        except Exception as e:
            return "", f"Error: {str(e)}\n"

    def get_prompt(self, shell_id: str) -> str:
        """Generate shell prompt for a specific shell"""
        if shell_id not in self.shells:
            return "# "

        shell_info = self.shells[shell_id]
        proc = shell_info['process']
        slave_tty = shell_info['slave_tty']

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

        # Update TTY session info
        if slave_tty:
            slave_tty.session_leader = proc.pid

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
def handle_connect(auth=None):
    """Handle new WebSocket connection"""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())

    session_id = session['session_id']
    join_room(session_id)

    print(f"Client connected: {session_id}")


@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection"""
    print(f"Client disconnected")


@socketio.on('create_shell')
def handle_create_shell():
    """Create a new shell session for a terminal"""
    session_id = session.get('session_id')
    if not session_id:
        emit('shell_error', {'error': 'No session'})
        return

    # Get or create game session
    game_session = get_or_create_session(session_id)

    # Create new shell
    shell_id = game_session.create_shell()

    # Join a room for this shell
    join_room(shell_id)

    # Send initial welcome and prompt
    emit('shell_created', {
        'shell_id': shell_id,
        'data': f"Welcome to Poodillion - The 1990s Hacking Simulator\n"
                f"Type 'help' for available commands\n\n"
                f"{game_session.get_prompt(shell_id)}"
    })

    print(f"Created shell {shell_id} for session {session_id}")


@socketio.on('input')
def handle_input(data):
    """Handle terminal input from client"""
    session_id = session.get('session_id')
    if not session_id:
        return

    shell_id = data.get('shell_id')
    if not shell_id:
        emit('output', {'data': 'Error: No shell_id provided\n'})
        return

    command = data.get('data', '').strip()

    # Get game session
    game_session = get_or_create_session(session_id)

    # Special commands
    if command in ('exit', 'quit'):
        emit('output', {'shell_id': shell_id, 'data': '\nGoodbye!\n'}, room=shell_id)
        return

    # Execute command
    if command:
        stdout, stderr = game_session.execute_command(shell_id, command)

        # Send output to this specific shell only
        if stdout:
            emit('output', {'shell_id': shell_id, 'data': stdout}, room=shell_id)
        if stderr:
            emit('output', {'shell_id': shell_id, 'data': stderr}, room=shell_id)

    # Send new prompt
    emit('output', {'shell_id': shell_id, 'data': game_session.get_prompt(shell_id)}, room=shell_id)


@socketio.on('destroy_shell')
def handle_destroy_shell(data):
    """Clean up a shell when terminal is closed"""
    session_id = session.get('session_id')
    if not session_id:
        return

    shell_id = data.get('shell_id')
    if not shell_id:
        return

    # Get game session
    if session_id not in sessions:
        return

    game_session = sessions[session_id]

    # Remove shell from session
    if shell_id in game_session.shells:
        shell_info = game_session.shells[shell_id]

        # Clean up process
        if shell_info['process']:
            try:
                game_session.current_system.processes.kill(shell_info['process'].pid)
            except:
                pass

        # Remove shell
        del game_session.shells[shell_id]

        print(f"Destroyed shell {shell_id} for session {session_id}")


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


@app.route('/api/browse', methods=['POST'])
def api_browse():
    """Handle browser requests - execute lynx command to get page content"""
    session_id = session.get('session_id')
    if not session_id:
        return jsonify({'success': False, 'error': 'No session'})

    data = request.get_json()
    url = data.get('url', '').strip()

    if not url:
        return jsonify({'success': False, 'error': 'No URL provided'})

    # Get game session
    game_session = get_or_create_session(session_id)

    # Create or use a dedicated shell for browser requests
    # Use the first shell if available, otherwise create one
    if not game_session.shells:
        shell_id = game_session.create_shell()
    else:
        shell_id = list(game_session.shells.keys())[0]

    # Execute lynx command to fetch the page
    command = f'lynx {url}'

    try:
        stdout, stderr = game_session.execute_command(shell_id, command)

        if stderr and 'Error' in stderr:
            return jsonify({'success': False, 'error': stderr})

        return jsonify({
            'success': True,
            'content': stdout,
            'url': url
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


if __name__ == '__main__':
    print("=" * 60)
    print("Poodillion Web Server")
    print("=" * 60)
    print("\nStarting server on http://localhost:5000")
    print("Press Ctrl+C to stop\n")

    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
