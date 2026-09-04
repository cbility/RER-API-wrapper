# RER HTML & JSON Snapshots

This directory contains scripts for fetching and saving raw HTML responses and parsed JSON data from the RER portal.

## Quick Start

```bash
# From the repository root
uv run python test/rer-html/fetch_all_snapshots.py
```

## What It Does

The `fetch_all_snapshots.py` script:

1. **Authenticates** with the RER portal using your saved cookies (`rer_cookies.json`)
2. **Fetches all organisations** from your user dashboard
3. **For each organisation**, fetches:
   - Organisation details
   - Stations list
   - Station declarations
   - Certificates overview
   - Certificate breakdowns (by type)
   - Output data tasks
   - Station declaration tasks
   - Individual station details (first 5 stations)
4. **Saves two files** for each endpoint:
   - `response.html` - The raw HTML from the RER portal
   - `parsed.json` - The parsed and structured data as JSON

## Output Structure

```
test/rer-html/snapshots/
  YYYYMMDD_HHMMSS/           # Timestamp of the run
    _user/
      /user/
        response.html
        parsed.json
    GEN0000001/              # Organisation ID
      /organisation/
        response.html
        parsed.json
      /stations/
        response.html
        parsed.json
      /station-declarations/
        response.html
        parsed.json
      /certificates/
        response.html
        parsed.json
      /certificates/REGO_breakdown/
        response.html
        parsed.json
      /tasks/output-data/
        response.html
        parsed.json
      /tasks/station-declarations/
        response.html
        parsed.json
      /stations/STA0000001/
        response.html
        parsed.json
```

## Individual Fetch Scripts

You can also fetch specific pages individually:

- `fetch_user.py` - User dashboard
- `fetch_organisation.py` - Single organisation details
- `fetch_user_organisations.py` - User's organisations list
- `fetch_organisation_stations.py` - Organisation's stations
- `fetch_organisation_certificates.py` - Certificates overview
- `fetch_user_activity.py` - User activity
- `fetch_user_notifications.py` - User notifications
- `fetch_user_ownership.py` - User ownership data

## Requirements

- Valid RER authentication cookies in `rer_cookies.json` (run `bootstrap_rer_cookies.py` if needed)
- Python 3.12+ with `uv`

## Use Cases

- **Debugging parser issues** - Compare raw HTML with parsed output
- **Tracking data changes** - Run snapshots over time to see what changed
- **Offline development** - Work with real data without hitting the API
- **Testing** - Use saved HTML/JSON as test fixtures
- **Documentation** - Show actual API responses

## Notes

- Each run creates a new timestamped directory
- HTML files are saved with UTF-8 encoding
- JSON files use `dataclasses.asdict()` for conversion
- Station details are limited to first 5 per organisation to avoid excessive requests
- Failed requests are logged but don't stop the script
