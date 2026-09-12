"""Quick test to verify cached HTML works."""

import sys
from pathlib import Path

# Add test directory to path
sys.path.insert(0, str(Path(__file__).parent / "test" / "rer-python"))

from cached_wrapper import CachedRERWrapper, FIXTURES_DIR

print(f"Cache directory: {FIXTURES_DIR}")
print(f"Cache exists: {FIXTURES_DIR.exists()}")

if FIXTURES_DIR.exists():
    print(f"\nCache contents:")
    for item in list(FIXTURES_DIR.iterdir())[:5]:
        print(f"  - {item.name}")

    # Try to load User endpoint
    wrapper = CachedRERWrapper(FIXTURES_DIR)
    try:
        print("\nTesting User endpoint...")
        user = wrapper.get_user()
        print(f"✓ Successfully loaded user: {user.email}")

        print("\nTesting User Organisations endpoint...")
        orgs = wrapper.get_user_organisations()
        print(f"✓ Successfully loaded {len(orgs)} organisations")

        if orgs:
            print(f"\nTesting Organisation endpoint...")
            org_id = orgs[0].organisation_id
            org_detail = wrapper.get_organisation(org_id)
            print(f"✓ Successfully loaded organisation {org_id}")

        print("\n✅ All basic tests passed! Cached HTML is working.")

    except FileNotFoundError as e:
        print(f"✗ Cache file not found: {e}")
    except Exception as e:
        print(f"✗ Error: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
else:
    print("✗ Cache directory not found!")
    print(
        "Run: wsl cp -r /home/cbility/git/RER-API-wrapper/test/rer-html/snapshots/20260904_133159 ./test/rer-html/snapshots/latest"
    )
