import base64
import json
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from datetime import datetime, timezone

# ── Sources ───────────────────────────────────────────────────────────────────
SOURCES = [
    "https://cdn.jsdelivr.net/gh/television-app/television-data@main/playlist.json",
    "https://raw.githubusercontent.com/television-app/television-data/main/playlist.json",
]

# AES key (copyOf to 32 bytes, zero-padded)
AES_KEY = b"T3l3v1s10n_S3cr3t_K3y_2026_@ppX".ljust(32, b"\x00")

HEADERS = {
    "User-Agent": "TeleVisionApp_SecretShieldV3/1.0 (Android TV; ExoPlayer)",
}

# ── Decrypt ───────────────────────────────────────────────────────────────────
def decrypt(data: bytes) -> list:
    enc = base64.b64decode(data)
    iv, ct = enc[:16], enc[16:]
    try:
        plain = unpad(AES.new(AES_KEY, AES.MODE_CBC, iv).decrypt(ct), 16)
    except Exception:
        # Fallback: static IV
        static_iv = b"1234567890123456"
        plain = unpad(AES.new(AES_KEY, AES.MODE_CBC, static_iv).decrypt(enc), 16)
    return json.loads(plain.decode("utf-8"))


def fetch_channels() -> list:
    for url in SOURCES:
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            channels = decrypt(r.content)
            if channels:
                print(f"✅ Fetched {len(channels)} channels from:\n   {url}")
                return channels
        except Exception as e:
            print(f"⚠️  Failed {url}: {e}")
    raise RuntimeError("All sources failed.")


# ── Build M3U ─────────────────────────────────────────────────────────────────
def build_m3u(channels: list) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [f"#EXTM3U x-tvg-url=\"\" <!-- Auto-generated: {now} -->\n"]
    for i, ch in enumerate(channels):
        name  = ch.get("n") or ch.get("name", f"Channel {i+1}")
        url   = ch.get("u") or ch.get("url", "")
        logo  = ch.get("l") or ch.get("logo", "")
        cid   = ch.get("i") or ch.get("id",  f"ch_{i}")
        group = ch.get("g") or ch.get("group", "TV")

        if not url:
            continue

        lines.append(
            f'#EXTINF:-1 tvg-id="{cid}" tvg-name="{name}" '
            f'tvg-logo="{logo}" group-title="{group}",{name}'
        )
        lines.append(url)

    return "\n".join(lines) + "\n"


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    channels = fetch_channels()
    m3u = build_m3u(channels)

    out = "playlist.m3u"
    with open(out, "w", encoding="utf-8") as f:
        f.write(m3u)

    total = m3u.count("#EXTINF")
    print(f"✅ Saved {total} channels → {out}")
