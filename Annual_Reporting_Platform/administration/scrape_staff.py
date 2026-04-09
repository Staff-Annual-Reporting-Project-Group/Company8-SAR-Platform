import os
import sys
import re
import io
import secrets
import django
import requests
from bs4 import BeautifulSoup

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Annual_Reporting_Platform.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from django.contrib.auth.models import User
from users.models import UserProfilePic
from administration.cloudinary_storage import upload_avatar

STAFF_URL = 'https://sta.uwi.edu/fst/dcit/staff-profiles'
BASE_HOST = 'https://sta.uwi.edu'
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; DCIT-Scraper/1.0)'}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)

TITLES = re.compile(
    r'^(Dr\.?|Prof\.?|Professor|Mr\.?|Mrs\.?|Ms\.?|Miss|Sir|Rev\.?)\s+',
    re.IGNORECASE
)


def fetch(url):
    try:
        r = SESSION.get(url, timeout=15)
        r.raise_for_status()
        return BeautifulSoup(r.text, 'html.parser')
    except requests.RequestException as e:
        print(f'  [ERROR] {url}: {e}')
        return None


def fetch_image_bytes(url):
    try:
        if url.startswith('/'):
            url = BASE_HOST + url
        r = SESSION.get(url, timeout=15)
        r.raise_for_status()
        content_type = r.headers.get('Content-Type', 'image/jpeg')
        if 'image' not in content_type:
            return None, None
        buf = io.BytesIO(r.content)
        buf.name = url.split('/')[-1].split('?')[0] or 'avatar.jpg'
        buf.content_type = content_type
        return buf, content_type
    except Exception:
        return None, None


def strip_title(name):
    return TITLES.sub('', name).strip()


def parse_staff(soup):
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
        clean = strip_title(raw_name).strip()

        if len(clean.split()) < 2:
            continue
        if not re.match(r'^[A-Za-z\s.\-]+$', clean):
            continue
        if clean in seen:
            continue
        seen.add(clean)

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
                    photo_url = src if src.startswith('http') else BASE_HOST + src

        staff.append({
            'raw_name': raw_name,
            'clean_name': clean,
            'email': email,
            'photo_url': photo_url,
        })

    return staff


def slugify_username(name):
    parts = name.lower().split()
    base = '.'.join(parts[:2]) if len(parts) >= 2 else parts[0]
    base = re.sub(r'[^a-z0-9.]', '', base)
    username = base
    counter = 1
    while User.objects.filter(username=username).exists():
        existing = User.objects.get(username=username)
        if f"{existing.first_name} {existing.last_name}".lower() == name.lower():
            return username
        username = f'{base}{counter}'
        counter += 1
    return username


def create_or_update_staff(member):
    clean = member['clean_name']
    parts = clean.split()
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

    was_created = False
    if not user:
        username = slugify_username(clean)
        user = User.objects.create_user(
            username=username,
            first_name=first_name,
            last_name=last_name,
            email=member['email'],
            password=secrets.token_urlsafe(20),
            is_active=True,
        )
        was_created = True

    profile, _ = UserProfilePic.objects.get_or_create(user=user)
    if not user.is_active:
        user.is_active = True
        user.save(update_fields=['is_active'])

    if member['photo_url'] and not profile.profilePic:
        buf, _ = fetch_image_bytes(member['photo_url'])
        if buf:
            try:
                url = upload_avatar(buf)
                profile.profilePic = url
                profile.save(update_fields=['profilePic'])
                return user, was_created, True
            except Exception as e:
                print(f'    [PHOTO ERROR] {e}')

    return user, was_created, False


def main():
    print('=' * 55)
    print('  DCIT Staff Scraper')
    print(f'  {STAFF_URL}')
    print('=' * 55)

    soup = fetch(STAFF_URL)
    if not soup:
        print('Could not reach the staff page.')
        return

    members = parse_staff(soup)
    print(f'\nFound {len(members)} staff members\n')

    created = skipped = photos = 0
    for m in members:
        user, was_created, photo_uploaded = create_or_update_staff(m)
        photo_tag = ' 📷' if photo_uploaded else ''
        status = '[CREATED]' if was_created else '[EXISTS] '
        print(f'  {status} {m["raw_name"]:40} → @{user.username}{photo_tag}')
        if was_created:
            created += 1
        else:
            skipped += 1
        if photo_uploaded:
            photos += 1

    print(f'\nDone.  Created: {created}  |  Existed: {skipped}  |  Photos: {photos}')


if __name__ == '__main__':
    main()
