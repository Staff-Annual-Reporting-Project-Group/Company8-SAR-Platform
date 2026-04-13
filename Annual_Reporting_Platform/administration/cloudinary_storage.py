"""
cloudinary_storage.py
─────────────────────
Place in your reports/ app directory.

Environment variables required:
    CLOUDINARY_CLOUD_NAME
    CLOUDINARY_API_KEY
    CLOUDINARY_API_SECRET
"""

import os
import cloudinary
import cloudinary.uploader


def _configure():
    cloudinary.config(
        cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME', ''),
        api_key=os.environ.get('CLOUDINARY_API_KEY', ''),
        api_secret=os.environ.get('CLOUDINARY_API_SECRET', ''),
        secure=True,
    )


def upload_image(file_obj, folder='uploads', filename=None):
    """Upload a file to Cloudinary. Returns the public_id (not the full URL)
    so it can be stored directly in a Django ImageField backed by
    cloudinary_storage — calling .url on the field will then produce the
    correct Cloudinary link."""
    _configure()
    file_obj.seek(0)
    options = {
        'folder': folder,
        'resource_type': 'image',
        'overwrite': True,
        'access_mode': 'public',
    }
    if filename:
        options['public_id'] = filename
    result = cloudinary.uploader.upload(file_obj, **options)
    return result['public_id']


def delete_image(url):
    """Delete an image from Cloudinary by its URL. Silently ignores errors."""
    if not url:
        return
    try:
        _configure()
        if '/upload/' not in url:
            return
        after_upload = url.split('/upload/', 1)[1]
        parts = after_upload.split('/')
        if parts[0].startswith('v') and parts[0][1:].isdigit():
            parts = parts[1:]
        last = parts[-1]
        if '.' in last:
            parts[-1] = last.rsplit('.', 1)[0]
        cloudinary.uploader.destroy('/'.join(parts), resource_type='image')
    except Exception:
        pass


def upload_avatar(file_obj):
    return upload_image(file_obj, folder='images/profile_pictures')


def upload_report_image(file_obj):
    return upload_image(file_obj, folder='images/report_images')