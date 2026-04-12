import io
import re
import secrets
import time
from datetime import date

import requests
from bs4 import BeautifulSoup
from django.contrib.auth.models import User
from django.db import transaction

from reports.models import Report, Category, Participant, Committee
from users.models import UserProfilePic
from .cloudinary_storage import upload_avatar




HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; DCIT-Scraper/1.0)'}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)

TITLES = re.compile(
    r'^(Dr\.?|Prof\.?|Professor|Mr\.?|Mrs\.?|Ms\.?|Miss|Sir|Rev\.?)\s+',
    re.IGNORECASE
)

STAFF_URL = 'https://sta.uwi.edu/fst/dcit/staff-profiles'
STAFF_BASE_HOST = 'https://sta.uwi.edu'

PUBLICATIONS_BASE_URL = 'https://sta.uwi.edu/fst/dcit/publications'
PUBLICATIONS_DELAY = 1.0




def fetch_soup(url):
    try:
        response = SESSION.get(url, timeout=20)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'html.parser')
    except requests.RequestException:
        return None


def strip_title(name):
    return TITLES.sub('', name).strip()


# ==========================================================
# STAFF SCRAPING HELPERS
# ==========================================================

def fetch_image_bytes(url):
    try:
        if url.startswith('/'):
            url = STAFF_BASE_HOST + url

        response = SESSION.get(url, timeout=20)
        response.raise_for_status()

        content_type = response.headers.get('Content-Type', 'image/jpeg')
        if 'image' not in content_type:
            return None

        buf = io.BytesIO(response.content)
        buf.name = url.split('/')[-1].split('?')[0] or 'avatar.jpg'
        return buf
    except Exception:
        return None


def parse_staff_members(soup):
    staff = []
    seen = set()

    for tr in soup.select('tr:has(td.views-field-field-staff-portrait)'):
        photo_td = tr.select_one('td.views-field-field-staff-portrait')
        all_tds = tr.find_all('td')
        info_td = next((td for td in all_tds if td != photo_td), None)

        if not info_td:
            continue

        name_tag = info_td.select_one('a')
        if not name_tag:
            continue

        raw_name = name_tag.get_text(strip=True)
        clean_name = strip_title(raw_name)

        if len(clean_name.split()) < 2:
            continue
        if not re.match(r'^[A-Za-z\s.\-]+$', clean_name):
            continue
        if clean_name in seen:
            continue

        seen.add(clean_name)

        email = ''
        for text in info_td.find_all(string=True):
            t = text.strip()
            if '@' in t and 'uwi.edu' in t.lower():
                email = t.strip('" ')
                break

        photo_url = ''
        if photo_td:
            img = photo_td.find('img')
            if img:
                src = img.get('src', '') or img.get('data-src', '')
                if src:
                    photo_url = src if src.startswith('http') else STAFF_BASE_HOST + src

        staff.append({
            'raw_name': raw_name,
            'clean_name': clean_name,
            'email': email,
            'photo_url': photo_url,
        })

    return staff


def slugify_username_from_name(name):
    parts = name.lower().split()
    base = '.'.join(parts[:2]) if len(parts) >= 2 else parts[0]
    base = re.sub(r'[^a-z0-9.]', '', base)

    username = base
    counter = 1

    while User.objects.filter(username=username).exists():
        existing = User.objects.filter(username=username).first()
        if existing and f"{existing.first_name} {existing.last_name}".lower() == name.lower():
            return username
        username = f'{base}{counter}'
        counter += 1

    return username


def create_or_update_staff_user(member):
    clean_name = member['clean_name']
    parts = clean_name.split()
    first_name = parts[0]
    last_name = ' '.join(parts[1:])

    user = None

    if member['email']:
        user = User.objects.filter(email__iexact=member['email']).first()

    if not user:
        user = User.objects.filter(
            first_name__iexact=first_name,
            last_name__iexact=last_name,
        ).first()

    created = False
    photo_uploaded = False

    if not user:
        username = slugify_username_from_name(clean_name)
        user = User.objects.create_user(
            username=username,
            first_name=first_name,
            last_name=last_name,
            email=member['email'],
            password=secrets.token_urlsafe(20),
            is_active=True,
        )
        created = True
    else:
        changed = False
        if member['email'] and not user.email:
            user.email = member['email']
            changed = True
        if not user.is_active:
            user.is_active = True
            changed = True
        if changed:
            user.save()

    profile, _ = UserProfilePic.objects.get_or_create(user=user)

    # Only try uploading if there is a real external photo
    if member['photo_url']:
        try:
            current_name = getattr(profile.profilePic, 'name', '')
            has_default = current_name in ['', 'profile_pictures/user.png']
            if has_default:
                buf = fetch_image_bytes(member['photo_url'])
                if buf:
                    uploaded_url = upload_avatar(buf)
                    profile.profilePic = uploaded_url
                    profile.save(update_fields=['profilePic'])
                    photo_uploaded = True
        except Exception:
            photo_uploaded = False

    return user, created, photo_uploaded


def generate_staff_accounts():
    soup = fetch_soup(STAFF_URL)
    if not soup:
        return {
            'success': False,
            'message': 'Could not reach the DCIT staff page.',
            'created': 0,
            'existing': 0,
            'photos': 0,
        }

    members = parse_staff_members(soup)

    created_count = 0
    existing_count = 0
    photo_count = 0

    for member in members:
        _, was_created, photo_uploaded = create_or_update_staff_user(member)

        if was_created:
            created_count += 1
        else:
            existing_count += 1

        if photo_uploaded:
            photo_count += 1

    return {
        'success': True,
        'message': f'Staff sync completed. Created: {created_count}, Existing: {existing_count}, Photos uploaded: {photo_count}.',
        'created': created_count,
        'existing': existing_count,
        'photos': photo_count,
    }


# ==========================================================
# PUBLICATION SCRAPING HELPERS
# ==========================================================

def _normalise(name):
    name = re.sub(r'[^a-z\s\-]', '', name.lower())
    return re.sub(r'\s+', ' ', name).strip()


def _initials_match(citation_name, full_name):
    cn = _normalise(citation_name)
    fn = _normalise(full_name)

    fn_parts = fn.split()
    if len(fn_parts) < 2:
        return False

    fn_last = fn_parts[-1]
    fn_given = fn_parts[:-1]

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
    cn = strip_title(citation_name.strip())
    if not cn:
        return None

    parts = cn.split()

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

        partial = User.objects.filter(
            first_name__iexact=first,
            last_name__istartswith=last,
        ).first()
        if partial:
            return partial

        partial2 = User.objects.filter(last_name__istartswith=last)
        if partial2.count() == 1:
            candidate = partial2.first()
            if candidate.first_name and candidate.first_name[0].upper() == first[0].upper():
                return candidate

    for user in User.objects.filter(is_active=True).exclude(last_name=''):
        full = f"{user.first_name} {user.last_name}"
        if _initials_match(cn, full):
            return user

    last_only = re.sub(r'[,.]', '', parts[-1]).strip() if parts else ''
    if last_only and len(last_only) > 2:
        matches = User.objects.filter(last_name__iexact=last_only)
        if matches.count() == 1:
            return matches.first()

        partial = User.objects.filter(last_name__istartswith=last_only)
        if partial.count() == 1:
            return partial.first()

        if is_staff and (matches.count() > 1 or partial.count() > 1):
            pool = matches if matches.count() > 0 else partial
            return pool.filter(is_staff=True).first() or pool.first()

    return None


def _clean_name(raw):
    raw = TITLES.sub('', raw).strip().strip('.,;').strip()
    return raw if len(raw) >= 2 else ''


def _parse_name_token(token):
    token = token.strip().strip(',').strip()
    if not token:
        return ''

    comma_parts = [p.strip() for p in token.split(',', 1) if p.strip()]
    if len(comma_parts) == 2:
        last, first = comma_parts
        if re.match(r'^[A-Z]', first):
            return f'{first} {last}'

    return token


def parse_authors_from_html(citation_field_tag):
    if not citation_field_tag:
        return []

    results = []
    seen = set()

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

    full_text = citation_field_tag.get_text(separator=' ', strip=True)
    cut = re.split(r'["\u201c\u2018\u0022]', full_text, maxsplit=1)[0]
    cut = cut.strip().rstrip(',').strip()
    if not cut:
        return results

    parts = re.split(r'\s+and\s+', cut, flags=re.IGNORECASE)

    for part in parts:
        tokens = [t.strip() for t in part.split(',') if t.strip()]
        i = 0

        while i < len(tokens):
            tok = tokens[i]
            next_tok = tokens[i + 1] if i + 1 < len(tokens) else ''

            if next_tok and re.match(r'^[A-Z]\.?$', next_tok):
                raw = f'{next_tok} {tok}'
                i += 2
            else:
                raw = tok
                i += 1

            name = _clean_name(_parse_name_token(raw))
            if not name or len(name) < 2:
                continue

            is_staff = any(raw_staff in raw or raw in raw_staff for raw_staff in staff_names_raw)

            if name not in seen:
                seen.add(name)
                results.append({'name': name, 'is_staff': is_staff})

    return results


def get_publication_years(soup):
    years = []
    for a in soup.select('a[href*="/publications/"]'):
        m = re.search(r'/publications/(\d{4})$', a.get('href', ''))
        if m:
            y = int(m.group(1))
            if y not in years:
                years.append(y)
    return sorted(years, reverse=True)


def parse_publication_page(soup, year):
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
        authors = parse_authors_from_html(citation_field)

        publications.append({
            'title': title,
            'pub_type': pub_type,
            'citation': citation_text,
            'authors': authors,
            'year': year,
        })

    return publications


def save_publications(publications, fallback_owner, category, committee):
    created = 0
    skipped = 0

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
            report_owner = fallback_owner

        if Report.objects.filter(title=title, user=report_owner, isActive=True).exists():
            skipped += 1
            continue

        with transaction.atomic():
            report = Report.objects.create(
                user=report_owner,
                title=title,
                description=pub['citation'] or f'{pub["pub_type"]}\n\n{title}',
                category=category,
                date_of_report=date(pub['year'], 1, 1),
                isActive=True,
            )

            report.committees.add(committee)

            for author_name, display_name, matched_user, _ in author_data:
                participant, _ = Participant.objects.get_or_create(name=display_name)
                if matched_user and participant.user != matched_user:
                    participant.user = matched_user
                    participant.save(update_fields=['user'])
                report.participants.add(participant)

        created += 1

    return created, skipped


def generate_publication_reports(owner_username='admin'):
    fallback_owner = User.objects.filter(username=owner_username).first()
    if not fallback_owner:
        return {
            'success': False,
            'message': f'Fallback owner "{owner_username}" was not found.',
            'created': 0,
            'skipped': 0,
        }

    category, _ = Category.objects.get_or_create(name='Publication')
    committee, _ = Committee.objects.get_or_create(name='Research & Development')

    first_page_soup = fetch_soup(f'{PUBLICATIONS_BASE_URL}/2026')
    if not first_page_soup:
        return {
            'success': False,
            'message': 'Could not reach the DCIT publications page.',
            'created': 0,
            'skipped': 0,
        }

    years = get_publication_years(first_page_soup)

    total_created = 0
    total_skipped = 0

    for index, year in enumerate(years):
        year_soup = first_page_soup if index == 0 else fetch_soup(f'{PUBLICATIONS_BASE_URL}/{year}')
        if not year_soup:
            continue

        publications = parse_publication_page(year_soup, year)
        if publications:
            created, skipped = save_publications(publications, fallback_owner, category, committee)
            total_created += created
            total_skipped += skipped

        if index < len(years) - 1:
            time.sleep(PUBLICATIONS_DELAY)

    return {
        'success': True,
        'message': f'Publication import completed. Created: {total_created}, Skipped: {total_skipped}.',
        'created': total_created,
        'skipped': total_skipped,
    }