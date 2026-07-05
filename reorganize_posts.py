#!/usr/bin/env python3
"""
reorganize_posts.py

Reorganizes a flat Hugo content/posts/ directory into year/slug/ page bundles:

    content/posts/my-post.md
        -> content/posts/2025/my-post/index.md

    content/posts/my-post/  (already a bundle, e.g. my-post/index.md + images)
        -> content/posts/2025/my-post/  (folder just moves, contents untouched)

Year is pulled from the post's front matter `date:` field, not the filename
or file mtime. Slug is pulled from a `slug:` front matter field if present,
otherwise derived from the filename (date-prefixes like 2025-05-01- are
stripped automatically).

Usage:
    python3 reorganize_posts.py /path/to/content/posts            # dry run
    python3 reorganize_posts.py /path/to/content/posts --execute  # do it

Dry run (default) only prints the planned moves. Nothing is touched on disk
until you pass --execute. Safe to run repeatedly.
"""

import argparse
import re
import shutil
import sys
from pathlib import Path

DATE_RE = re.compile(r'^date\s*:\s*["\']?(\d{4})-(\d{2})-(\d{2})', re.MULTILINE)
SLUG_RE = re.compile(r'^slug\s*:\s*["\']?([a-zA-Z0-9\-_]+)', re.MULTILINE)
TITLE_RE = re.compile(r'^title\s*:\s*["\']?(.+?)["\']?\s*$', re.MULTILINE)

DATE_PREFIX_RE = re.compile(r'^\d{4}-\d{2}-\d{2}-')


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')


def read_front_matter(md_path: Path) -> str:
    """Return the YAML front matter block (between the first two '---' lines)."""
    text = md_path.read_text(encoding='utf-8', errors='ignore')
    if not text.startswith('---'):
        return ''
    parts = text.split('---', 2)
    if len(parts) < 3:
        return ''
    return parts[1]


def extract_year(front_matter: str, fallback_path: Path) -> str:
    m = DATE_RE.search(front_matter)
    if m:
        return m.group(1)
    # fallback: try a date-looking prefix in the filename/dirname
    m2 = re.match(r'(\d{4})-\d{2}-\d{2}', fallback_path.stem)
    if m2:
        return m2.group(1)
    return 'undated'


def extract_slug(front_matter: str, fallback_path: Path) -> str:
    m = SLUG_RE.search(front_matter)
    if m:
        return slugify(m.group(1))
    m2 = TITLE_RE.search(front_matter)
    if m2:
        return slugify(m2.group(1))
    stem = fallback_path.stem
    stem = DATE_PREFIX_RE.sub('', stem)
    if fallback_path.name == 'index.md':
        stem = fallback_path.parent.name
        stem = DATE_PREFIX_RE.sub('', stem)
    return slugify(stem)


def plan_moves(posts_dir: Path):
    moves = []  # (source, dest, kind)
    seen_dests = set()

    for entry in sorted(posts_dir.iterdir()):
        if entry.name.startswith('.'):
            continue

        # Skip anything that's already inside a year folder (idempotent re-runs)
        if entry.is_dir() and re.match(r'^\d{4}$', entry.name):
            continue

        if entry.is_dir():
            index_md = entry / 'index.md'
            if not index_md.exists():
                print(f"  ! skipping dir with no index.md: {entry}", file=sys.stderr)
                continue
            fm = read_front_matter(index_md)
            year = extract_year(fm, index_md)
            slug = extract_slug(fm, index_md)
            dest = posts_dir / year / slug
            moves.append((entry, dest, 'dir'))
        elif entry.suffix == '.md':
            fm = read_front_matter(entry)
            year = extract_year(fm, entry)
            slug = extract_slug(fm, entry)
            dest = posts_dir / year / slug
            moves.append((entry, dest, 'file-to-bundle'))
        else:
            continue

        if str(moves[-1][1]) in seen_dests:
            print(f"  ! WARNING: duplicate destination {moves[-1][1]} "
                  f"(from {moves[-1][0]}) - resolve slug collision manually",
                  file=sys.stderr)
        seen_dests.add(str(moves[-1][1]))

    return moves


def execute_moves(moves):
    for src, dest, kind in moves:
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            print(f"  ! SKIPPING, destination already exists: {dest}")
            continue
        if kind == 'dir':
            shutil.move(str(src), str(dest))
        else:  # file-to-bundle
            dest.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dest / 'index.md'))
        print(f"  moved: {src} -> {dest}")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('posts_dir', type=Path, help='Path to content/posts/')
    parser.add_argument('--execute', action='store_true',
                         help='Actually perform the moves (default is dry run)')
    args = parser.parse_args()

    posts_dir = args.posts_dir.resolve()
    if not posts_dir.is_dir():
        print(f"Not a directory: {posts_dir}", file=sys.stderr)
        sys.exit(1)

    moves = plan_moves(posts_dir)

    if not moves:
        print("Nothing to do.")
        return

    print(f"{'EXECUTING' if args.execute else 'DRY RUN'} - {len(moves)} item(s):\n")
    for src, dest, kind in moves:
        rel_src = src.relative_to(posts_dir)
        rel_dest = dest.relative_to(posts_dir)
        print(f"  {rel_src}  ->  {rel_dest}/index.md")

    if args.execute:
        print()
        execute_moves(moves)
        print("\nDone. Review with `git status` before committing.")
    else:
        print("\nThis was a dry run. Re-run with --execute to actually move files.")
        print("Recommend running `git add -A` / commit first so moves are tracked as renames.")


if __name__ == '__main__':
    main()
