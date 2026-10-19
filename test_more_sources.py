#!/usr/bin/env python3
import requests
import time

SOURCES = [
    # More Indian fintech/tech companies
    ("greenhouse", "openfx"),
    ("greenhouse", "kraftonindia"),
    ("greenhouse", "juspay"),
    ("greenhouse", "cashfree"),
    ("greenhouse", "zoho"),
    ("greenhouse", "freshworks"),
    ("greenhouse", "postman"),
    ("greenhouse", "apna"),
    ("greenhouse", "unacademy"),
    ("greenhouse", "byjus"),
    ("greenhouse", "swiggy"),
    ("greenhouse", "zomato"),
    ("greenhouse", "ola"),
    ("greenhouse", "rapido"),
    ("greenhouse", "dream11"),
    ("greenhouse", "meesho"),
    ("greenhouse", "phonepe"),
    ("greenhouse", "paytm"),
    ("greenhouse", "policybazaar"),
    ("greenhouse", "liquiloans"),
    ("greenhouse", "kissht"),
    ("greenhouse", "moneyview"),
    ("greenhouse", "earlysalary"),
    ("greenhouse", "paysense"),
    ("greenhouse", "slice"),
    ("greenhouse", "uni"),
    ("greenhouse", "voltz"),
    ("greenhouse", "fi"),
    ("greenhouse", "khatabook"),
    ("greenhouse", "okcredit"),
    ("greenhouse", "upstox"),
    ("greenhouse", "zerodha"),
    ("greenhouse", "groww"),
    ("greenhouse", "etmoney"),
    ("greenhouse", "smallcase"),
    ("greenhouse", "cleartax"),
    ("greenhouse", "razorpay"),
    ("greenhouse", "stripe"),
    ("greenhouse", "paypal"),
    ("greenhouse", "square"),
    ("greenhouse", "wise"),
    ("greenhouse", "remitly"),
    ("greenhouse", "westernunion"),
    ("greenhouse", "moneylion"),
    ("greenhouse", "dave"),
    ("greenhouse", "chime"),
    ("greenhouse", "vemo"),
    ("greenhouse", "prodigy"),
    ("greenhouse", "bamboo"),
    ("greenhouse", "tala"),
    ("greenhouse", "branch"),
    ("greenhouse", "kuda"),
    ("greenhouse", "opay"),
    ("greenhouse", "palmpay"),
    ("greenhouse", "wave"),
    ("greenhouse", "semicolon"),
    ("greenhouse", "corider"),
    ("greenhouse", "getlinked"),
    ("greenhouse", "turing"),
    ("greenhouse", "supersourcing"),
    ("greenhouse", "hackerearth"),
    ("greenhouse", "codeground"),
    ("greenhouse", "interviewbit"),
    ("greenhouse", "scaler"),
    ("greenhouse", "upgrad"),
    ("greenhouse", "greatlearning"),
    ("greenhouse", "simplilearn"),
    ("greenhouse", "udemy"),
    ("greenhouse", "coursera"),
    ("greenhouse", "byjus"),
    ("greenhouse", "vedantu"),
    ("greenhouse", "unacademy"),
    ("greenhouse", "gradeup"),
    ("greenhouse", "toppr"),
    ("greenhouse", "doubtnut"),
    ("greenhouse", "epic"),
    ("greenhouse", "microsoft"),
    ("greenhouse", "google"),
    ("greenhouse", "amazon"),
    ("greenhouse", "apple"),
    ("greenhouse", "meta"),
    ("greenhouse", "netflix"),
    ("greenhouse", "uber"),
    ("greenhouse", "airbnb"),
    ("greenhouse", "spotify"),
    ("greenhouse", "twitter"),
    ("greenhouse", "linkedin"),
    ("greenhouse", "salesforce"),
    ("greenhouse", "adobe"),
    ("greenhouse", "oracle"),
    ("greenhouse", "sap"),
    ("greenhouse", "dell"),
    ("greenhouse", "hp"),
    ("greenhouse", "intel"),
    ("greenhouse", "cisco"),
    ("greenhouse", "vmware"),
    ("greenhouse", "ibm"),
]

RESULTS = []
for kind, slug in SOURCES:
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
    try:
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            data = r.json()
            count = len(data.get("jobs", []))
            if count > 0:
                RESULTS.append((kind, slug, count))
                print(f"✓ {slug} — {count} jobs")
            else:
                print(f"✗ {slug} — 0 jobs")
        else:
            print(f"✗ {slug} — HTTP {r.status_code}")
    except Exception as e:
        print(f"✗ {slug} — {str(e)[:50]}")
    time.sleep(0.2)

print(f"\n=== WORKING: {len(RESULTS)} ===")
for kind, slug, count in RESULTS:
    print(f"  {slug}: {count}")
