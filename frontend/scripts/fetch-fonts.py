"""Download the interface fonts into src/fonts/ and regenerate src/fonts.css.

The fonts are self-hosted rather than linked from a CDN: the rest of the system runs
offline (local models, no headless browser for PDFs), and an interface that silently
falls back to a different face on an air-gapped machine is not the same interface.

Run from the frontend directory:  python scripts/fetch-fonts.py

Space Grotesk, JetBrains Mono and IBM Plex Sans Arabic are all SIL Open Font License.
Only the subsets the interface needs are kept - Latin for the two Latin faces, plus
Arabic for IBM Plex Sans Arabic. Browsers fetch only the subsets a page actually uses,
so a Latin-only session never downloads the Arabic files.
"""

import io
import os
import re
import urllib.request

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

FAMILIES = {
    "Space Grotesk": ("spacegrotesk", "wght@400;500;600;700", {"latin", "latin-ext"}),
    "JetBrains Mono": ("jetbrainsmono", "wght@400;500;700", {"latin", "latin-ext"}),
    "IBM Plex Sans Arabic": ("plexarabic", "wght@400;500;600;700", {"latin", "latin-ext", "arabic"}),
}


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(request, timeout=60).read()


def main() -> None:
    out_dir = os.path.join("src", "fonts")
    os.makedirs(out_dir, exist_ok=True)
    blocks = []
    total = 0

    for family, (slug, weights, keep) in FAMILIES.items():
        query = family.replace(" ", "+")
        css = fetch(
            f"https://fonts.googleapis.com/css2?family={query}:{weights}&display=swap"
        ).decode("utf8")

        # Each @font-face is preceded by a /* subset */ comment naming its unicode range.
        for subset, face in re.findall(r"/\*\s*([\w-]+)\s*\*/\s*(@font-face\s*\{[^}]*\})", css):
            if subset not in keep:
                continue
            weight = re.search(r"font-weight:\s*(\d+)", face).group(1)
            url = re.search(r"url\((https://[^)]+\.woff2)\)", face).group(1)
            name = f"{slug}-{weight}-{subset}.woff2"
            data = fetch(url)
            io.open(os.path.join(out_dir, name), "wb").write(data)
            total += len(data)
            blocks.append(face.replace(url, f"./fonts/{name}").strip())
            print(f"{name:38} {len(data) // 1024:>4} KB")

    header = (
        "/* Self-hosted so the interface renders identically with no route to a font CDN.
"
        "   Downloaded from Google Fonts (all three families are Open Font License).
"
        "   Regenerate with scripts/fetch-fonts.py. */

"
    )
    io.open(os.path.join("src", "fonts.css"), "w", encoding="utf8").write(
        header + "

".join(blocks) + "
"
    )
    print(f"
total {total // 1024} KB across {len(blocks)} files")


if __name__ == "__main__":
    main()
