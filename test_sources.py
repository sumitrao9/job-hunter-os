#!/usr/bin/env python3
"""Test potential job sources and find working ones with India jobs."""
import requests
import json
import time

SOURCES = [
    # Greenhouse
    ("greenhouse", "superapp"),
    ("greenhouse", "openai"),
    ("greenhouse", "cartesia"),
    ("greenhouse", "razorpaysoftwareprivatelimited"),
    ("greenhouse", "groww"),
    ("greenhouse", "phonepe"),
    ("greenhouse", "myntra"),
    ("greenhouse", "zerodha"),
    ("greenhouse", "upstox"),
    ("greenhouse", "paytm"),
    ("greenhouse", "cred"),
    ("greenhouse", "slice"),
    ("greenhouse", "lazypay"),
    ("greenhouse", "mobikwik"),
    ("greenhouse", "paysense"),
    ("greenhouse", "earlysalary"),
    ("greenhouse", "moneyview"),
    ("greenhouse", "bajajfinserv"),
    ("greenhouse", "hdfcbank"),
    ("greenhouse", "icicibank"),
    ("greenhouse", "kotak"),
    ("greenhouse", "sbibank"),
    ("greenhouse", "axisbank"),
    ("greenhouse", "idfcfirstbank"),
    ("greenhouse", "yesbank"),
    ("greenhouse", "indusindbank"),
    ("greenhouse", "rblbank"),
    ("greenhouse", "au"),
    ("greenhouse", "federalbank"),
    ("greenhouse", "southindianbank"),
    ("greenhouse", "karnatakabank"),
    ("greenhouse", "tmb"),
    ("greenhouse", "dcbbank"),
    # Lever
    ("lever", "openai"),
    ("lever", "netflix"),
    ("lever", "uber"),
    ("lever", "robinhood"),
    ("lever", "crypto"),
    ("lever", "plaid"),
    ("lever", "mercury"),
    ("lever", "brex"),
    ("lever", "affirm"),
    ("lever", "chime"),
    ("lever", "wise"),
    ("lever", "revolut"),
    ("lever", "nubank"),
    ("lever", "stone"),
    ("lever", "pagseguro"),
    ("lever", "picpay"),
    ("lever", "n26"),
    ("lever", "monzo"),
    ("lever", "starling"),
    # Ashby
    ("ashby", "openai"),
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
    ("ashby", "togetherai"),
    ("ashby", "langchain"),
    ("ashby", "retell-ai"),
    ("ashby", "baseten"),
    ("ashby", "cartesia"),
    ("ashby", "heygen"),
    ("ashby", "suno"),
    ("ashby", "pika"),
]

RESULTS = []
for kind, slug in SOURCES:
    url = None
    if kind == "greenhouse":
        url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
    elif kind == "lever":
        url = f"https://api.lever.co/v0/postings/{slug}?mode=json&limit=200"
    elif kind == "ashby":
        url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
    
    if not url:
        continue
    
    try:
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            data = r.json()
            count = 0
            if kind == "greenhouse":
                count = len(data.get("jobs", []))
            elif kind == "lever":
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

print(f"\n=== WORKING SOURCES: {len(RESULTS)} ===")
for kind, slug, count in RESULTS:
    print(f"  {kind}:{slug} ({count})")
