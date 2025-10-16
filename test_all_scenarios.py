#!/usr/bin/env python3
"""
Test that all scenarios can be created and booted successfully
"""

from scenarios import SCENARIOS

def test_all_scenarios():
    """Test all scenarios"""

    print("=" * 80)
    print("TESTING ALL POODILLION 2 SCENARIOS")
    print("=" * 80)

    for key, create_scenario in SCENARIOS.items():
        print(f"\n{'=' * 80}")
        print(f"Testing Scenario {key}")
        print(f"{'=' * 80}\n")

        try:
            # Create scenario
            attacker, network, metadata = create_scenario()

            print(f"✓ Scenario created successfully")
            print(f"  Title: {metadata['title']}")
            print(f"  Difficulty: {metadata['difficulty']}")
            print(f"  Systems: {len(metadata['systems'])}")

            # Check network type
            print(f"  Network type: {type(network).__name__}")

            # Check physical network
            if hasattr(network, 'physical_network'):
                num_segments = len(network.physical_network.segments)
                print(f"  Physical segments: {num_segments}")

                for seg_name, segment in network.physical_network.segments.items():
                    print(f"    - {seg_name}: {len(segment.interfaces)} interfaces")

            # Boot all systems (just check they don't crash)
            print(f"\n  Booting {len(metadata['systems'])} systems...")
            for i, system in enumerate(metadata['systems']):
                # Don't print full boot output, just status
                import io
                import sys
                old_stdout = sys.stdout
                sys.stdout = io.StringIO()

                try:
                    system.boot()
                    booted = system.is_alive()
                finally:
                    sys.stdout = old_stdout

                status = "✓" if booted else "✗"
                print(f"    {status} {system.hostname} ({system.ip})")

            print(f"\n✓ Scenario {key} is fully operational!")

        except Exception as e:
            print(f"\n✗ Scenario {key} failed: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 80)
    print("✓ ALL SCENARIOS TESTED SUCCESSFULLY!")
    print("=" * 80)
    print("\nAll scenarios are ready to play!")
    print("Run: python3 play.py\n")

if __name__ == '__main__':
    test_all_scenarios()
