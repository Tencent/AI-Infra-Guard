"""Run the entire live matrix: attacks, defenses, channels, agents.

One real example per method against the configured model. Requires the same
environment variables as the other scripts here (see README.md).

Run:  python demos/live_matrix/run_all.py
"""

from _common import require_env

import test_agents_live
import test_attacks_live
import test_channels_live
import test_defenses_live


def main() -> None:
    require_env()
    print("\n########## ATTACKS ##########")
    test_attacks_live.main()
    print("\n########## DEFENSES ##########")
    test_defenses_live.main()
    print("\n########## CHANNELS ##########")
    test_channels_live.main()
    print("\n########## AGENTS ##########")
    test_agents_live.main()
    print("\nAll live matrix demos completed.")


if __name__ == "__main__":
    main()
