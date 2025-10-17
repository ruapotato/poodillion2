#!/usr/bin/env python3
"""
Test the play.py scenario system (non-interactive)
"""

from scenarios import list_scenarios, SCENARIOS


def test_scenarios():
    """Test scenario loading"""
    print("=== Testing Scenario System ===\n")

    # List available scenarios
    scenarios = list_scenarios()
    print(f"Found {len(scenarios)} scenarios:\n")

    for scenario in scenarios:
        print(f"[{scenario['key']}] {scenario['title']}")
        print(f"    Description: {scenario['description']}")
        print(f"    Difficulty: {scenario['difficulty']}")
        print()

    # Test loading each scenario
    for key in ['1', '2', '3']:
        print(f"\n{'='*60}")
        print(f"Testing Scenario {key}")
        print(f"{'='*60}\n")

        create_scenario = SCENARIOS[key]
        attacker, network, metadata = create_scenario()

        print(f"Title: {metadata['title']}")
        print(f"Objective: {metadata['objective']}")
        print(f"Systems created: {len(metadata['systems'])}")

        for sys in metadata['systems']:
            print(f"  - {sys.hostname:20s} @ {sys.ip}")

        print(f"\nNetwork routes:")
        for ip, routes in network.connections.items():
            if routes:
                print(f"  {ip} can reach: {', '.join(sorted(routes))}")

        print(f"\nFirewall rules:")
        for ip, rules in network.firewalls.items():
            if rules:
                for rule in rules:
                    print(f"  {ip}: {rule['action']} port {rule['port']}")

        # Test that attacker can login
        print(f"\nTesting attacker system ({attacker.hostname})...")
        success = attacker.login('root', 'root')
        print(f"  Login: {'✓ Success' if success else '✗ Failed'}")

        # Test network connectivity
        if len(metadata['systems']) > 1:
            target_ip = metadata['systems'][1].ip
            can_reach = network.can_connect(attacker.ip, target_ip, 80)
            print(f"  Can reach {target_ip}:80: {'✓ Yes' if can_reach else '✗ No'}")

    print(f"\n{'='*60}")
    print("All scenarios loaded successfully!")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    test_scenarios()
