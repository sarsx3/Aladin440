#!/usr/bin/env python3
"""
fix_playlist.py
----------------
উৎস M3U প্লেলিস্ট (যা অটো-আপডেট হয়) ডাউনলোড করে, প্রতিটা স্ট্রিম এন্ট্রির
#EXTVLCOPT:http-referrer / http-user-agent ঠিকভাবে বসিয়ে একটা "ফিক্সড"
প্লেলিস্ট জেনারেট করে।

মূল আইডিয়া (ডোমেইন-ভিত্তিক অটো-লার্নিং):
  সোর্স ফাইলে যেসব এন্ট্রিতে ইতিমধ্যে সঠিক http-referrer / http-user-agent
  ট্যাগ আছে, সেগুলো থেকে প্রতিটা ডোমেইনের জন্য সবচেয়ে বেশি ব্যবহৃত (majority)
  Referer/User-Agent মান শেখা হয়। তারপর একই ডোমেইনের যেসব এন্ট্রিতে ট্যাগ
  নেই, তাদের মধ্যে সেই মানটা বসিয়ে দেওয়া হয়।

  এতে কোনো ডোমেইন/Referer হার্ডকোড করা লাগে না — সোর্স প্লেলিস্ট ভবিষ্যতে
  নতুন ডোমেইন বা নতুন Referer মান যোগ করলেও স্ক্রিপ্ট নিজে থেকেই মানিয়ে নেয়।
"""

import sys
import re
import urllib.request
from collections import Counter
from urllib.parse import urlsplit
from datetime import datetime, timezone

SOURCE_URL = (
    "https://raw.githubusercontent.com/sm-monirulislam/"
    "SM-Movie-Hup-Auto-Update/refs/heads/main/Movie_Combined.m3u"
)
OUTPUT_PATH = "docs/Movie_Combined_Fixed.m3u"
USER_AGENT = "Mozilla/5.0 (fix-playlist-bot)"


def fetch_source(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read()
    # BOM/encoding নিরাপদে হ্যান্ডেল করা
    return raw.decode("utf-8-sig", errors="replace")


def domain_of(url: str) -> str:
    try:
        return urlsplit(url).netloc.lower()
    except Exception:
        return ""


def parse_entries(text: str):
    """
    প্লেলিস্টকে entry-ব্লকে ভাঙা হয়। প্রতিটা entry:
      {
        "extinf": "#EXTINF:...",
        "opts": ["#EXTVLCOPT:...", ...],   # EXTINF আর URL-এর মাঝের সব লাইন
        "url": "https://...",
      }
    হেডার (EXTM3U + উপরের কমেন্ট ব্লক) আলাদাভাবে রাখা হয়।
    """
    lines = text.splitlines()
    header_lines = []
    entries = []
    i = 0
    n = len(lines)

    # হেডার: প্রথম #EXTINF পাওয়ার আগ পর্যন্ত সব লাইন হেডার হিসেবে ধরা হয়
    while i < n and not lines[i].strip().startswith("#EXTINF"):
        header_lines.append(lines[i])
        i += 1

    while i < n:
        line = lines[i]
        if line.strip().startswith("#EXTINF"):
            entry = {"extinf": line, "opts": [], "url": None}
            i += 1
            while i < n:
                cur = lines[i]
                stripped = cur.strip()
                if stripped.startswith("#EXTINF"):
                    break
                if stripped.startswith("#"):
                    entry["opts"].append(cur)
                    i += 1
                    continue
                if stripped == "":
                    i += 1
                    continue
                # URL লাইন
                entry["url"] = cur.strip()
                i += 1
                break
            entries.append(entry)
        else:
            i += 1

    return header_lines, entries


def extract_opt(entry, key: str):
    """entry['opts'] এর মধ্যে #EXTVLCOPT:<key>=<value> থাকলে value রিটার্ন করে।"""
    prefix = f"#EXTVLCOPT:{key}="
    for opt in entry["opts"]:
        s = opt.strip()
        if s.lower().startswith(prefix.lower()):
            return s[len(prefix):].strip()
    return None


def learn_domain_values(entries):
    """প্রতিটা ডোমেইনের জন্য majority referrer / user-agent শেখে।"""
    referrer_votes = {}
    ua_votes = {}

    for e in entries:
        if not e["url"]:
            continue
        dom = domain_of(e["url"])
        ref = extract_opt(e, "http-referrer")
        ua = extract_opt(e, "http-user-agent")
        if ref:
            referrer_votes.setdefault(dom, Counter())[ref] += 1
        if ua:
            ua_votes.setdefault(dom, Counter())[ua] += 1

    domain_referrer = {
        dom: counter.most_common(1)[0][0] for dom, counter in referrer_votes.items()
    }
    domain_ua = {
        dom: counter.most_common(1)[0][0] for dom, counter in ua_votes.items()
    }
    return domain_referrer, domain_ua


def fix_entries(entries, domain_referrer, domain_ua):
    fixed = 0
    skipped_unknown_domain = 0

    for e in entries:
        if not e["url"]:
            continue
        dom = domain_of(e["url"])

        has_ref = extract_opt(e, "http-referrer") is not None
        has_ua = extract_opt(e, "http-user-agent") is not None

        changed = False
        if not has_ref and dom in domain_referrer:
            e["opts"].append(f"#EXTVLCOPT:http-referrer={domain_referrer[dom]}")
            changed = True
        elif not has_ref and dom not in domain_referrer:
            skipped_unknown_domain += 1

        if not has_ua and dom in domain_ua:
            e["opts"].append(f"#EXTVLCOPT:http-user-agent={domain_ua[dom]}")
            changed = True

        if changed:
            fixed += 1

    return fixed, skipped_unknown_domain


def render(header_lines, entries) -> str:
    out = []
    out.extend(header_lines)
    if out and out[-1].strip() != "":
        out.append("")
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    out.append(f"# Auto-fixed by fix_playlist.py — last run: {ts}")
    out.append("")

    for e in entries:
        if not e["url"]:
            continue
        out.append(e["extinf"])
        out.extend(e["opts"])
        out.append(e["url"])

    return "\n".join(out) + "\n"


def main():
    print(f"[fix_playlist] fetching source: {SOURCE_URL}")
    text = fetch_source(SOURCE_URL)

    header_lines, entries = parse_entries(text)
    total = len(entries)
    print(f"[fix_playlist] parsed {total} entries")

    domain_referrer, domain_ua = learn_domain_values(entries)
    print(f"[fix_playlist] learned referrer for domains: {list(domain_referrer.keys())}")
    print(f"[fix_playlist] learned user-agent for domains: {list(domain_ua.keys())}")

    fixed, unknown = fix_entries(entries, domain_referrer, domain_ua)
    print(f"[fix_playlist] fixed {fixed} entries")
    if unknown:
        print(
            f"[fix_playlist] WARNING: {unknown} entries on domains with no known "
            f"referrer value were left untouched (new/unknown domain — needs at "
            f"least one tagged example upstream to learn from)."
        )

    output = render(header_lines, entries)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(output)

    print(f"[fix_playlist] wrote {OUTPUT_PATH} ({total} entries, {fixed} auto-fixed)")


if __name__ == "__main__":
    sys.exit(main())
