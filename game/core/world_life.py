"""
World Life System
Makes the virtual world feel alive with background activity, random events, etc.
"""

import random
import time
from typing import List, Dict
from dataclasses import dataclass
from datetime import datetime

@dataclass
class WorldEvent:
    """A random event that can happen in the world"""
    timestamp: float
    system_ip: str
    event_type: str
    message: str
    visible_to_player: bool = False


class WorldLife:
    """Manages background activity and events in the world"""

    def __init__(self, network, all_systems):
        self.network = network
        self.all_systems = all_systems
        self.events = []
        self.last_update = time.time()

        # Simulated users on the network
        self.active_users = {
            '192.168.1.10': ['anonymous', 'hackerman', 'lurker99'],
            '192.168.1.11': ['zero_cool', 'crash_override', 'acid_burn'],
            '192.168.3.100': ['student42', 'prof_smith', 'gradstudent'],
            '192.168.99.1': ['???', '???', 'the_nexus'],
        }

        # BBS messages that can appear
        self.bbs_messages = [
            "New user 'phantom' joined underground.bbs",
            "Elite hacker spotted on nexus.unknown",
            "Government agents scanning the network",
            "Credit card database leaked on dark web",
            "MegaCorp stock price plummeting",
            "Strange packets detected from 192.168.99.1",
            "University VAX system running slow",
            "The Nexus is watching...",
        ]

    def update(self):
        """Update world state - call this periodically"""
        now = time.time()

        # Update every 5-10 seconds
        if now - self.last_update < 5:
            return []

        self.last_update = now
        new_events = []

        # Random chance of events
        if random.random() < 0.3:  # 30% chance
            event = self._generate_random_event()
            if event:
                new_events.append(event)
                self.events.append(event)

        return new_events

    def _generate_random_event(self):
        """Generate a random event"""
        event_type = random.choice([
            'user_login',
            'bbs_post',
            'network_scan',
            'file_access',
            'mysterious_activity',
        ])

        system_ip = random.choice([s.ip for s in self.all_systems])
        system = next((s for s in self.all_systems if s.ip == system_ip), None)

        if event_type == 'user_login':
            users = self.active_users.get(system_ip, ['unknown'])
            user = random.choice(users)
            return WorldEvent(
                timestamp=time.time(),
                system_ip=system_ip,
                event_type='user_login',
                message=f"User '{user}' logged into {system.hostname if system else system_ip}",
                visible_to_player=random.random() < 0.5
            )

        elif event_type == 'bbs_post':
            message = random.choice(self.bbs_messages)
            return WorldEvent(
                timestamp=time.time(),
                system_ip=system_ip,
                event_type='bbs_post',
                message=f"[BBS] {message}",
                visible_to_player=True
            )

        elif event_type == 'network_scan':
            return WorldEvent(
                timestamp=time.time(),
                system_ip=system_ip,
                event_type='network_scan',
                message=f"Network scan detected from {system_ip}",
                visible_to_player=random.random() < 0.3
            )

        elif event_type == 'mysterious_activity':
            if system_ip == '192.168.99.1':  # The Nexus
                messages = [
                    "The Nexus pulse detected across all networks",
                    "Anomalous data patterns from nexus.unknown",
                    "The Nexus is... changing",
                    "Connection established: ??? → ALL SYSTEMS",
                ]
                return WorldEvent(
                    timestamp=time.time(),
                    system_ip=system_ip,
                    event_type='mysterious',
                    message=f"[ALERT] {random.choice(messages)}",
                    visible_to_player=True
                )

        return None

    def get_recent_events(self, count=5, visible_only=True):
        """Get recent events"""
        events = self.events[-count:]
        if visible_only:
            events = [e for e in events if e.visible_to_player]
        return events

    def get_active_users_on(self, system_ip):
        """Get simulated active users on a system"""
        return self.active_users.get(system_ip, [])

    def simulate_network_traffic(self):
        """Generate background network traffic"""
        # Randomly move some packets around
        traffic = []

        for _ in range(random.randint(1, 5)):
            src = random.choice([s.ip for s in self.all_systems])
            dst = random.choice([s.ip for s in self.all_systems])
            if src != dst:
                traffic.append({
                    'src': src,
                    'dst': dst,
                    'type': random.choice(['HTTP', 'SSH', 'TELNET', 'FTP', 'UNKNOWN']),
                    'size': random.randint(100, 5000)
                })

        return traffic

    def get_dynamic_content(self, content_type='news'):
        """Generate dynamic content for pages"""
        if content_type == 'news':
            headlines = [
                "BREAKING: Strange Activity on Network Tonight",
                "MegaCorp Denies Nexus Project Allegations",
                "University Researcher Goes Missing",
                "Underground BBS Posts Encrypted Files",
                "Government Issues Network Security Warning",
                f"Local Time: {datetime.now().strftime('%H:%M:%S')}",
                f"{len(self.active_users)} users online across network",
            ]
            return random.sample(headlines, min(3, len(headlines)))

        elif content_type == 'users':
            total = sum(len(users) for users in self.active_users.values())
            return f"{total} users online"

        elif content_type == 'mysterious':
            messages = [
                "01010100 01101000 01100101 00100000 01001110 01100101 01111000 01110101 01110011",
                "Connection detected: ???.???.???.???",
                "The network... it's alive",
                "Do you feel it? The pulse?",
                "They're watching. Always watching.",
            ]
            return random.choice(messages)

        return ""
