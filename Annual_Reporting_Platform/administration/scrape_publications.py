import csv
import os
import re
import sys
import time
import django
import requests
from bs4 import BeautifulSoup
from datetime import date

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Annual_Reporting_Platform.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from django.contrib.auth.models import User
from reports.models import Report, Category, Participant, Committee

BASE_URL = 'https://sta.uwi.edu/fst/dcit/publications'
DELAY = 1.0
OWNER_USERNAME = 'admin'
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; DCIT-Scraper/1.0)'}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)


# -- fetch --

def fetch(url):
    try:
        r = SESSION.get(url, timeout=15)
        r.raise_for_status()
        return BeautifulSoup(r.text, 'html.parser')
    except requests.RequestException as e:
        print(f'  [ERROR] {url}: {e}')
        return None


# -- name matching --

TITLES = re.compile(
    r'^(Dr\.?|Prof\.?|Professor|Mr\.?|Mrs\.?|Ms\.?|Miss|Sir|Rev\.?)\s+',
    re.IGNORECASE
)


def _strip_title(name):
    return TITLES.sub('', name).strip()


def _normalise(name):
    """Lowercase, strip punctuation except hyphens, collapse spaces."""
    name = re.sub(r'[^a-z\s\-]', '', name.lower())
    return re.sub(r'\s+', ' ', name).strip()


def _initials_match(citation_name, full_name):
    """
    Check whether a citation name matches a full name.
    Handles:
      'J. Doe'        → first initial + last
      'Kieu, T.D.'    → last + multiple initials
      'Ragbir, D.'    → partial hyphenated last (Ragbir-Shripat)
    """
    cn = _normalise(citation_name)
    fn = _normalise(full_name)

    fn_parts = fn.split()
    if len(fn_parts) < 2:
        return False

    fn_last = fn_parts[-1]
    fn_given = fn_parts[:-1]

    # Expand hyphenated last name into variants
    # 'ragbir-shripat' → {'ragbir-shripat', 'ragbir', 'shripat'}
    fn_last_variants = {fn_last}
    if '-' in fn_last:
        fn_last_variants.update(fn_last.split('-'))

    cn_parts = cn.split()
    if len(cn_parts) < 2:
        return False

    initials = [p.rstrip('.') for p in cn_parts if len(p.rstrip('.')) == 1]
    words = [p for p in cn_parts if len(p.rstrip('.')) > 1]

    if not words:
        return False

    # Last name must match any variant (exact or prefix)
    last_match = any(
        w in fn_last_variants or
        any(v.startswith(w) or w.startswith(v) for v in fn_last_variants)
        for w in words
    )
    if not last_match:
        return False

    if not initials:
        return True

    fn_given_initials = [p[0] for p in fn_given if p]
    matched_initials = sum(1 for i in initials if i in fn_given_initials)
    return matched_initials == len(initials)


def find_user_for_name(citation_name, is_staff=False):
    """
    Try to find a User account matching a citation author name.
    Handles exact, initial, hyphenated last name, and multi-initial formats.
    """
    cn = _strip_title(citation_name.strip())
    if not cn:
        return None

    parts = cn.split()

    # 1. Exact full name match
    if len(parts) >= 2:
        if ',' in cn:
            last, first = [p.strip() for p in cn.split(',', 1)]
        else:
            first, last = parts[0], parts[-1]
        exact = User.objects.filter(
            first_name__iexact=first,
            last_name__iexact=last,
        ).first()
        if exact:
            return exact

        # 1b. Partial hyphenated last name — 'Ragbir' matching 'Ragbir-Shripat'
        partial = User.objects.filter(
            first_name__iexact=first,
            last_name__istartswith=last,
        ).first()
        if partial:
            return partial

        # Also try last name starting with the citation last (reversed order)
        partial2 = User.objects.filter(
            last_name__istartswith=last,
        )
        if partial2.count() == 1:
            # Only safe if unique
            candidate = partial2.first()
            # Verify first initial matches
            if candidate.first_name and candidate.first_name[0].upper() == first[0].upper():
                return candidate

    # 2. Initials match against all active users (handles hyphenated names too)
    for user in User.objects.filter(is_active=True).exclude(last_name=''):
        full = f"{user.first_name} {user.last_name}"
        if _initials_match(cn, full):
            return user

    # 3. Last-name only — exact or partial hyphenated
    last_only = re.sub(r'[,.]', '', parts[-1]).strip() if parts else ''
    if last_only and len(last_only) > 2:
        # Exact match
        matches = User.objects.filter(last_name__iexact=last_only)
        if matches.count() == 1:
            return matches.first()
        # Hyphenated: 'Ragbir' matches 'Ragbir-Shripat'
        partial = User.objects.filter(last_name__istartswith=last_only)
        if partial.count() == 1:
            return partial.first()
        if is_staff and (matches.count() > 1 or partial.count() > 1):
            pool = matches if matches.count() > 0 else partial
            return pool.filter(is_staff=True).first() or pool.first()

    return None


# -- citation parsing --

def _clean_name(raw):
    """Strip whitespace, trailing punctuation and honorifics."""
    raw = TITLES.sub('', raw).strip().strip('.,;').strip()
    return raw if len(raw) >= 2 else ''


def _parse_name_token(token):
    """
    Normalise a single name token into 'Firstname Lastname' form.
    Handles:
      'Doe, J.'   → 'J. Doe'
      'J. Doe'    → 'J. Doe'
      'John Doe'  → 'John Doe'
      'Doe'       → 'Doe'
      'V .'       → 'V.'   (space before period, common in scraped text)
    """
    token = token.strip().strip(',').strip()
    if not token:
        return ''

    # Normalise "V ." → "V." and "V . D." → "V.D."
    token = re.sub(r'([A-Za-z])\s+\.', r'\1.', token)

    # "Lastname, F." or "Lastname, F.G." — comma separates last from initials
    comma_parts = [p.strip() for p in token.split(',', 1) if p.strip()]
    if len(comma_parts) == 2:
        last, first = comma_parts
        # Only treat as Last,First if second part looks like initials or a name
        if re.match(r'^[A-Z]', first):
            return f'{first} {last}'

    return token


def parse_authors_from_html(citation_field_tag):
    """
    Parse author names from the citation HTML element.
    Returns list of dicts: {name, is_staff}
      - name     : normalised name string
      - is_staff : True if the name was underlined/linked on the UWI site
    """
    if not citation_field_tag:
        return []

    results = []
    seen = set()

    # First pass — extract underlined/linked names with is_staff=True
    # UWI marks DCIT authors with <a> or <u> tags inside the citation
    staff_tags = citation_field_tag.find_all(['a', 'u'])
    staff_names_raw = set()
    for tag in staff_tags:
        text = tag.get_text(strip=True)
        name = _clean_name(_parse_name_token(text))
        if name and len(name) >= 3:
            staff_names_raw.add(text.strip())
            if name not in seen:
                seen.add(name)
                results.append({'name': name, 'is_staff': True})

    # Second pass — parse full citation text for all authors
    full_text = citation_field_tag.get_text(separator=' ', strip=True)

    # Cut the author block from the rest of the citation.
    # Prefer cutting at an opening title-quote; fall back to a year marker
    # like "(2009)" or ", 2009," which signals the end of the author list.
    _AUTHOR_BLOCK_END = re.compile(
        r'["\u201c\u2018\u0022]'   # opening title quote  "  "  '
        r'|\s*\(\d{4}\)'           # year in parens  (2009)
        r'|,\s*\d{4}\s*[,.]'       # bare year  , 2009,
    )
    cut = _AUTHOR_BLOCK_END.split(full_text, maxsplit=1)[0]
    cut = cut.strip().rstrip('.,').strip()
    if not cut:
        return results

    # Split on ' and ' to separate last author
    parts = re.split(r'\s+and\s+', cut, flags=re.IGNORECASE)

    for part in parts:
        # Each part may be "Last, F." or "F. Last" or "First Last".
        # Strip any trailing venue/year fragments that slipped through.
        part = re.split(r'\(\d{4}\)|,\s*\d{4}', part, maxsplit=1)[0]
        part = part.strip().rstrip('.,').strip()
        if not part:
            continue

        # Split on comma to handle "Last, F." pairs
        tokens = [t.strip() for t in part.split(',') if t.strip()]
        i = 0
        while i < len(tokens):
            tok = tokens[i]
            next_tok = tokens[i + 1] if i + 1 < len(tokens) else ''

            # Normalise "V ." → "V." before matching
            next_tok_norm = re.sub(r'([A-Za-z])\s+\.', r'\1.', next_tok).strip()

            # "Lastname, F." — next token is a single initial (with or without period)
            if next_tok_norm and re.match(r'^[A-Z]\.?$', next_tok_norm):
                raw = f'{next_tok_norm} {tok}'
                i += 2
            else:
                raw = tok
                i += 1

            name = _clean_name(_parse_name_token(raw))
            if not name or len(name) < 2:
                continue

            # Check if this name was already added as a staff (underlined) name
            is_staff = any(
                raw_staff in raw or raw in raw_staff
                for raw_staff in staff_names_raw
            )

            if name not in seen:
                seen.add(name)
                results.append({'name': name, 'is_staff': is_staff})

    return results


# -- page parsing --

def get_years(soup):
    years = []
    for a in soup.select('a[href*="/publications/"]'):
        m = re.search(r'/publications/(\d{4})$', a.get('href', ''))
        if m:
            y = int(m.group(1))
            if y not in years:
                years.append(y)
    return sorted(years, reverse=True)


def parse_page(soup, year):
    publications = []
    for node in soup.select('div.node-publication'):
        title_tag = node.select_one('h2 a')
        if not title_tag:
            continue
        title = title_tag.get_text(separator=' ', strip=True)

        type_field = node.select_one('div.field-name-field-publication-type .field-item')
        pub_type = type_field.get_text(strip=True) if type_field else ''

        citation_field = node.select_one('div.field-name-field-publication-citation .field-item')
        citation_text = citation_field.get_text(separator=' ', strip=True) if citation_field else ''

        # Parse authors from HTML (preserves underline info)
        authors = parse_authors_from_html(citation_field)

        publications.append({
            'title': title,
            'pub_type': pub_type,
            'citation': citation_text,
            'authors': authors,
            'year': year,
        })
    print(f'  Found {len(publications)} publications')
    return publications


# -- resolve to CSV rows --

def resolve_publications_to_rows(publications, owner, category_name, committee_name):
    """
    Resolve author names to usernames and return a list of dicts ready for
    writing to CSV (matches the web importer's expected column format).
    """
    rows = []

    for pub in publications:
        title = pub['title']

        author_data = []
        for author in pub['authors']:
            name = author['name']
            is_staff = author['is_staff']
            if not name:
                continue
            matched_user = find_user_for_name(name, is_staff=is_staff)
            display_name = (
                f"{matched_user.first_name} {matched_user.last_name}".strip()
                if matched_user else name
            )
            author_data.append((name, display_name, matched_user, is_staff))

        matched_users = [u for _, _, u, _ in author_data if u is not None]
        if len(matched_users) == 1:
            report_owner = matched_users[0]
        else:
            report_owner = owner

        participant_names = [display_name for _, display_name, _, _ in author_data]

        rows.append({
            'username':        report_owner.username,
            'title':           title,
            'description':     pub['citation'] or f'{pub["pub_type"]}\n\n{title}',
            'category':        category_name,
            'date_of_report':  f'{pub["year"]}-01-01',
            'committees':      committee_name,
            'participants':    ';'.join(participant_names),
        })

    return rows


def write_csv(rows, output_path):
    """Write resolved publication rows to a CSV file."""
    fieldnames = ['username', 'title', 'description', 'category',
                  'date_of_report', 'committees', 'participants']
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f'\n  Saved {len(rows)} rows -> {output_path}')


# -- main --

def main():
    print('=' * 60)
    print('  DCIT Publications Scraper  (CSV export mode)')
    print('=' * 60)

    try:
        owner = User.objects.get(username=OWNER_USERNAME)
    except User.DoesNotExist:
        print(f'\n[ERROR] User "{OWNER_USERNAME}" not found.')
        print('Available users:', list(User.objects.values_list('username', flat=True)))
        username = input('Enter fallback owner username: ').strip()
        owner = User.objects.get(username=username)

    category_name  = 'Publication'
    committee_name = 'Research & Development'

    matchable = User.objects.filter(is_active=True).exclude(last_name='').count()
    print(f'Fallback owner : {owner.username}')
    print(f'Matchable users: {matchable}\n')

    print(f'Fetching {BASE_URL}/2026 ...')
    soup = fetch(f'{BASE_URL}/2026')
    if not soup:
        print('Cannot reach the site.')
        return

    years = get_years(soup)
    print(f'Years found: {years}\n')

    all_rows = []

    for i, year in enumerate(years):
        print(f'-- {year} --')
        year_soup = soup if i == 0 else fetch(f'{BASE_URL}/{year}')
        if not year_soup:
            print('  Could not fetch, skipping.')
            continue

        pubs = parse_page(year_soup, year)
        if pubs:
            rows = resolve_publications_to_rows(
                pubs, owner, category_name, committee_name
            )
            all_rows.extend(rows)

        if i < len(years) - 1:
            time.sleep(DELAY)

    output_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'publications_export.csv'
    )
    write_csv(all_rows, output_file)

    print('\n' + '=' * 60)
    print(f'  Done!  {len(all_rows)} rows written to CSV.')
    print(f'  Upload this file via the admin Generate Reports page.')
    print('=' * 60)


if __name__ == '__main__':
    main()
