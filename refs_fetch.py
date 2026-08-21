#!/usr/bin/env python3
"""Reference photographs: fetch them, and check the rule that keeps them out of git.

The photographs this project measures are third-party works — CC0, CC BY, CC BY-SA.
Share-alike conflicts with the CC BY 4.0 the models ship under, and CC BY would
require carrying the credit inside the file, so **the photographs are never
committed**. What is committed is one manifest per folder:

    <aircraft folder>/refs/manifest.json        schema "latam-refs/1"

recording, for every photograph, its URL, author, licence and date. This script is
the other half of that bargain: it turns the manifest back into the photographs, so
"links only" stays usable for refinement work instead of merely compliant.

    python3 refs_fetch.py                        # the whole fleet
    python3 refs_fetch.py "boeing 777-300ER"     # one folder (substring matches)
    python3 refs_fetch.py --listar               # what the manifests hold
    python3 refs_fetch.py --verificar            # the gate, see below

--verificar answers the only two questions that matter, in one command:
  1. does every manifest entry carry URL + author + licence?
  2. is any photograph currently tracked by git, or exposed to the next `git add`?
Exit code is non-zero if either answer is bad, so it can be wired into CI or a hook.

Downloads go to the path each entry records in "file", relative to the aircraft
folder. New entries should use "refs/<name>"; a few older photographs sit at the
folder root because measurement scripts already point at them there.

Needs: requests, Pillow (both already used elsewhere in this project).
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse

ROOT = os.path.dirname(os.path.abspath(__file__))
MANIFEST = "refs/manifest.json"
SCHEMA = "latam-refs/1"

# Wikimedia asks for a descriptive User-Agent and blocks the default python one.
UA = ("LatamFleetModels-refs-fetch/1.0 "
      "(https://github.com/kimlage; non-commercial 3D replica project)")

IMAGE_EXT = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".tif", ".tiff", ".avif",
             ".bmp", ".heic")
# photographs that live at an aircraft-folder root rather than under refs/
ROOT_PHOTO_RE = re.compile(r"(^|/)(ref_|ws_|ctl_|radome_side_)[^/]*$", re.I)

MIN_BYTES = 20_000       # anything smaller is an error page, not a photograph
MIN_PIXELS = 200         # ... and anything this small is a thumbnail or an icon


# ---------------------------------------------------------------- manifests

def folders():
    """Every folder holding a refs/manifest.json, in a stable order."""
    out = []
    for name in sorted(os.listdir(ROOT)):
        path = os.path.join(ROOT, name)
        if os.path.isdir(path) and os.path.exists(os.path.join(path, MANIFEST)):
            out.append(name)
    return out


def load(folder):
    with open(os.path.join(ROOT, folder, MANIFEST), encoding="utf-8") as fh:
        return json.load(fh)


def pick(patterns):
    """Resolve command-line folder arguments against the folders that exist."""
    known = folders()
    if not patterns:
        return known
    chosen, unknown = [], []
    for pat in patterns:
        hits = [f for f in known if f == pat] or \
               [f for f in known if pat.lower() in f.lower()]
        if hits:
            chosen += [h for h in hits if h not in chosen]
        else:
            unknown.append(pat)
    if unknown:
        sys.exit("unknown folder(s): %s\nknown: %s"
                 % (", ".join(unknown), ", ".join(known)))
    return chosen


# ---------------------------------------------------------------- download

def candidate_urls(entry):
    """Download URLs to try, best first.

    Special:FilePath is preferred over a direct upload.wikimedia.org link: the
    latter starts returning 429 after about ten anonymous originals, which is a
    trap a previous session already fell into and wrote down.
    """
    urls, page = [], entry.get("page_url")
    if page:
        m = re.search(r"/wiki/(?:File|Ficheiro|Arquivo|Datei):(.+)$", page)
        if m:
            name = urllib.parse.unquote(m.group(1)).replace(" ", "_")
            urls.append("https://commons.wikimedia.org/wiki/Special:FilePath/"
                        + urllib.parse.quote(name, safe="()!*'-_.~"))
    for u in (entry.get("url"), page):
        if u and u not in urls and not re.search(r"/wiki/(?:File|Ficheiro):", u):
            urls.append(u)
    return urls


def verify_image(path):
    """(ok, description). A real image, of a size that could be a photograph."""
    size = os.path.getsize(path)
    if size < MIN_BYTES:
        return False, "only %d bytes — almost certainly an error page" % size
    try:
        from PIL import Image
    except ImportError:
        return True, "%d bytes (Pillow missing, pixels unchecked)" % size
    try:
        with Image.open(path) as im:
            im.verify()                      # catches truncated / non-image data
        with Image.open(path) as im:
            w, h = im.size
            fmt = im.format
    except Exception as exc:                 # noqa: BLE001 - report, never crash
        return False, "not a readable image (%s)" % exc
    if w < MIN_PIXELS or h < MIN_PIXELS:
        return False, "%dx%d is too small to be the reference" % (w, h)
    return True, "%s %dx%d, %.1f MB" % (fmt, w, h, size / 1e6)


def download(url, dest, timeout):
    import requests
    tmp = dest + ".part"
    with requests.get(url, headers={"User-Agent": UA}, timeout=timeout,
                      stream=True, allow_redirects=True) as r:
        r.raise_for_status()
        ctype = r.headers.get("Content-Type", "")
        if ctype and not ctype.startswith(("image/", "application/octet-stream")):
            raise ValueError("server sent %s, not an image" % ctype)
        os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
        with open(tmp, "wb") as fh:
            for chunk in r.iter_content(65536):
                fh.write(chunk)
    return tmp


def fetch_folder(folder, force, pause, timeout):
    data = load(folder)
    photos = data.get("photos", [])
    print("\n=== %s  (%d entries)" % (folder, len(photos)))
    tally = {"ok": 0, "present": 0, "skipped": 0, "failed": 0}
    failures = []

    for entry in photos:
        rel = entry.get("file")
        label = rel or entry.get("file_note") or "(no local file)"

        if not rel:
            print("  --  %-52s citation only, nothing to download" % label[:52])
            tally["skipped"] += 1
            continue
        if entry.get("derived"):
            print("  --  %-52s derived crop; re-fetch the source and re-crop" % rel[:52])
            tally["skipped"] += 1
            continue

        dest = os.path.join(ROOT, folder, rel)
        if os.path.exists(dest) and not force:
            ok, why = verify_image(dest)
            if ok:
                print("  ==  %-52s already here (%s)" % (rel[:52], why))
                tally["present"] += 1
                continue
            print("  !!  %-52s on disk but %s — refetching" % (rel[:52], why))

        urls = candidate_urls(entry)
        if not urls:
            print("  XX  %-52s no usable URL in the manifest" % rel[:52])
            tally["failed"] += 1
            failures.append((folder, rel, "no URL recorded"))
            continue

        last = None
        for url in urls:
            try:
                tmp = download(url, dest, timeout)
            except Exception as exc:                       # noqa: BLE001
                last = "%s: %s" % (url.split("/")[-1][:40], exc)
                continue
            ok, why = verify_image(tmp)
            if not ok:
                os.remove(tmp)
                last = why
                continue
            os.replace(tmp, dest)
            print("  OK  %-52s %s" % (rel[:52], why))
            tally["ok"] += 1
            last = None
            break

        if last is not None:
            print("  XX  %-52s FAILED: %s" % (rel[:52], last))
            tally["failed"] += 1
            failures.append((folder, rel, last))
        if pause:
            time.sleep(pause)

    print("  -- %d fetched, %d already present, %d citation-only, %d failed"
          % (tally["ok"], tally["present"], tally["skipped"], tally["failed"]))
    return tally, failures


# ---------------------------------------------------------------- verifier

def git(*args):
    try:
        out = subprocess.run(("git",) + args, cwd=ROOT, capture_output=True,
                             text=True, timeout=60)
    except Exception:                                       # noqa: BLE001
        return None
    return out.stdout if out.returncode == 0 else None


def looks_like_photo(path):
    if not path.lower().endswith(IMAGE_EXT):
        return False
    return "/refs/" in "/" + path or ROOT_PHOTO_RE.search(path) is not None


def verify():
    print("Reference photographs — manifest and git check")
    print("=" * 68)

    known = folders()
    print("\n1. manifests: one per folder at %s" % MANIFEST)
    stray = []
    for name in sorted(os.listdir(ROOT)):
        d = os.path.join(ROOT, name)
        if not os.path.isdir(d) or name.startswith("."):
            continue
        for bad in ("refs_manifest.json", "refs/refs_manifest.json"):
            if os.path.exists(os.path.join(d, bad)):
                stray.append("%s/%s" % (name, bad))
    problems = []

    total = 0
    for folder in known:
        data = load(folder)
        photos = data.get("photos", [])
        total += len(photos)
        bad = []
        if data.get("schema") != SCHEMA:
            bad.append("schema is %r, expected %r" % (data.get("schema"), SCHEMA))
        for entry in photos:
            missing = [k for k in ("url", "author", "license") if not entry.get(k)]
            if missing:
                bad.append("%s -> no %s"
                           % (entry.get("file") or entry.get("file_note") or "?",
                              ", ".join(missing)))
        mark = "ok " if not bad else "BAD"
        print("   %s %-20s %3d entries" % (mark, folder, len(photos)))
        for b in bad:
            print("        - %s" % b)
        problems += [(folder, b) for b in bad]

    if stray:
        print("\n   BAD manifests outside the convention:")
        for s in stray:
            print("        - %s (should be <folder>/%s)" % (s, MANIFEST))
        problems += [(s, "manifest outside the convention") for s in stray]

    print("\n2. git: no photograph may be tracked or newly exposed")
    tracked = [p for p in (git("ls-files") or "").splitlines() if looks_like_photo(p)]
    if tracked:
        print("   BAD %d photograph(s) TRACKED by git:" % len(tracked))
        for p in tracked[:40]:
            print("        - %s" % p)
        problems += [(p, "tracked by git") for p in tracked]
    else:
        print("   ok  no photograph is tracked")

    status = git("status", "--porcelain", "--untracked=all")
    exposed = []
    if status is not None:
        for line in status.splitlines():
            path = line[3:].strip().strip('"')
            if line[:2].strip() and looks_like_photo(path):
                exposed.append(path)
    if exposed:
        print("   BAD %d photograph(s) NOT ignored — the next `git add` would take them:"
              % len(exposed))
        for p in exposed[:40]:
            print("        - %s" % p)
        problems += [(p, "not ignored") for p in exposed]
    else:
        print("   ok  every photograph on disk is ignored")

    print("\n%s" % ("=" * 68))
    print("%d entries across %d folders." % (total, len(known)))
    if problems:
        print("FAIL — %d problem(s) above." % len(problems))
        return 1
    print("PASS — every entry carries URL, author and licence; no photograph is in git.")
    return 0


def listing():
    for folder in folders():
        data = load(folder)
        photos = data.get("photos", [])
        here = sum(1 for p in photos if p.get("file")
                   and os.path.exists(os.path.join(ROOT, folder, p["file"])))
        cite = sum(1 for p in photos if not p.get("file"))
        print("%-20s %3d entries  %3d on disk  %2d citation-only"
              % (folder, len(photos), here, cite))
    return 0


def main():
    ap = argparse.ArgumentParser(
        description="Fetch the reference photographs recorded in the refs manifests, "
                    "or verify the manifests and the git rule.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="examples:\n"
               "  python3 refs_fetch.py\n"
               "  python3 refs_fetch.py \"boeing 777-300ER\" \"boeing 787-9\"\n"
               "  python3 refs_fetch.py --verificar\n")
    ap.add_argument("folders", nargs="*",
                    help="aircraft folder(s); a substring is enough. Default: all.")
    ap.add_argument("--verificar", "--verify", dest="verificar", action="store_true",
                    help="check every entry has URL+author+licence and that no "
                         "photograph is tracked by or exposed to git")
    ap.add_argument("--listar", "--list", dest="listar", action="store_true",
                    help="summarise the manifests without touching the network")
    ap.add_argument("--forcar", "--force", dest="forcar", action="store_true",
                    help="re-download even when the file is already present")
    ap.add_argument("--pausa", type=float, default=1.5, metavar="S",
                    help="seconds between requests (default 1.5; be kind to Commons)")
    ap.add_argument("--timeout", type=float, default=120.0, metavar="S")
    args = ap.parse_args()

    if args.verificar:
        return verify()
    if args.listar:
        return listing()

    try:
        import requests  # noqa: F401
    except ImportError:
        sys.exit("this needs `requests`:  python3 -m pip install requests Pillow")

    grand = {"ok": 0, "present": 0, "skipped": 0, "failed": 0}
    failures = []
    for folder in pick(args.folders):
        tally, fails = fetch_folder(folder, args.forcar, args.pausa, args.timeout)
        for k in grand:
            grand[k] += tally[k]
        failures += fails

    print("\n" + "=" * 68)
    print("%d fetched, %d already present, %d citation-only, %d failed"
          % (grand["ok"], grand["present"], grand["skipped"], grand["failed"]))
    if failures:
        print("\nFailed — the URL may have died, which after a few years is normal.")
        print("Fix the manifest entry (the Commons page usually still knows the file)")
        print("rather than dropping the credit:")
        for folder, rel, why in failures:
            print("  %s/%s\n      %s" % (folder, rel, why))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
