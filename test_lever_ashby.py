#!/usr/bin/env python3
import requests
import time

SOURCES = [
    # Lever
    ("lever", "crypto"),
    ("lever", "offchainlabs"),
    ("lever", "mystenlabs"),
    ("lever", "metabase"),
    ("lever", "outreach"),
    ("lever", "highspot"),
    ("lever", "appzen"),
    ("lever", "secureframe"),
    ("lever", "finix"),
    ("lever", "greenlight"),
    ("lever", "wealthfront"),
    ("lever", "baselane"),
    ("lever", "sideinc"),
    ("lever", "chownow"),
    ("lever", "lyrahealth"),
    ("lever", "minted"),
    ("lever", "peerspace"),
    ("lever", "whoop"),
    ("lever", "fliff"),
    ("lever", "getlabs"),
    ("lever", "hive"),
    ("lever", "sysdig"),
    ("lever", "sprucesystems"),
    # Ashby
    ("ashby", "ramp"),
    ("ashby", "linear"),
    ("ashby", "notion"),
    ("ashby", "docker"),
    ("ashby", "snowflake"),
    ("ashby", "plaid"),
    ("ashby", "vanta"),
    ("ashby", "1password"),
    ("ashby", "cursor"),
    ("ashby", "replit"),
    ("ashby", "perplexity"),
    ("ashby", "harvey"),
    ("ashby", "sierra"),
    ("ashby", "decagon"),
    ("ashby", "mercor"),
    ("ashby", "langchain"),
    ("ashby", "retell-ai"),
    ("ashby", "baseten"),
    ("ashby", "cartesia"),
    ("ashby", "heygen"),
    ("ashby", "suno"),
    ("ashby", "pika"),
    ("ashby", "togetherai"),
    ("ashby", "read-ai"),
    ("ashby", "eliseai"),
    ("ashby", "cresta"),
    ("ashby", "nooks"),
    ("ashby", "altanaai"),
    ("ashby", "mirage"),
    ("ashby", "fleetworks"),
    ("ashby", "vizcom"),
    ("ashby", "radai"),
    ("ashby", "speechify"),
    ("ashby", "gleanwork"),
    ("ashby", "otterai"),
    ("ashby", "benchling"),
    ("ashby", "aclima"),
    ("ashby", "skydio"),
    ("ashby", "higharc"),
    ("ashby", "pano-ai"),
    ("ashby", "solace"),
    ("ashby", "permitflow"),
    ("ashby", "onebrief"),
    ("ashby", "cape"),
    ("ashby", "andurilindustries"),
    ("ashby", "verkada"),
    ("ashby", "owllabs"),
    ("ashby", "fictiv"),
    ("ashby", "flexe"),
    ("ashby", "markforged"),
    ("ashby", "carbon"),
    ("ashby", "pomelocare"),
    ("ashby", "medrio"),
    ("ashby", "careaccess"),
    ("ashby", "mode"),
]

RESULTS = []
for kind, slug in SOURCES:
    if kind == "lever":
        url = f"https://api.lever.co/v0/postings/{slug}?mode=json&limit=200"
    elif kind == "ashby":
        url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
    else:
        continue
    
    try:
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            data = r.json()
            count = 0
            if kind == "lever":
                count = len(data) if isinstance(data, list) else 0
            elif kind == "ashby":
                count = len(data.get("jobPostings", []))
            if count > 0:
                RESULTS.append((kind, slug, count))
                print(f"✓ {kind}:{slug} — {count} jobs")
            else:
                print(f"✗ {kind}:{slug} — 0 jobs")
        else:
            print(f"✗ {kind}:{slug} — HTTP {r.status_code}")
    except Exception as e:
        print(f"✗ {kind}:{slug} — {str(e)[:50]}")
    time.sleep(0.3)

print(f"\n=== WORKING: {len(RESULTS)} ===")
for kind, slug, count in sorted(RESULTS, key=lambda x: -x[2]):
    print(f"  {kind}:{slug}: {count}")
