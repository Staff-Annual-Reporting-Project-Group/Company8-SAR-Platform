import os
import cloudinary.uploader
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.files import File
from users.models import UserProfilePic
from reports.models import Report


class Command(BaseCommand):
    help = 'Upload existing local images to Cloudinary and update database records'

    def handle(self, *args, **options):
        media_root = settings.MEDIA_ROOT
        uploaded = 0
        skipped = 0
        errors = 0

        # ── Profile pictures ──────────────────────────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING('=== Profile Pictures ==='))
        for profile in UserProfilePic.objects.all():
            field_name = str(profile.profilePic)
            if not field_name:
                skipped += 1
                continue

            if field_name.startswith('http') or 'cloudinary' in field_name or field_name.startswith('images/'):
                self.stdout.write(f'  SKIP (already Cloudinary): {field_name}')
                skipped += 1
                continue

            local_path = os.path.join(media_root, field_name)
            if not os.path.exists(local_path):
                self.stdout.write(self.style.WARNING(f'  MISSING file: {local_path}'))
                errors += 1
                continue

            try:
                with open(local_path, 'rb') as f:
                    profile.profilePic.save(os.path.basename(local_path), File(f), save=True)
                self.stdout.write(self.style.SUCCESS(f'  OK: {field_name} ->{profile.profilePic.name}'))
                uploaded += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ERROR: {field_name}: {e}'))
                errors += 1

        # ── Report feature images ─────────────────────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING('=== Report Feature Images ==='))

        # Upload the default image once, then apply to all reports using it
        default_fallback_path = os.path.join(media_root, 'report_images', 'ai_chip.png')
        default_cloudinary_name = None

        reports_needing_default = Report.objects.filter(feature_image='default_image.jpg')
        if reports_needing_default.exists():
            if not os.path.exists(default_fallback_path):
                self.stdout.write(self.style.ERROR(
                    f'  Cannot find fallback image at {default_fallback_path} — skipping {reports_needing_default.count()} reports'
                ))
                errors += reports_needing_default.count()
            else:
                self.stdout.write(f'  Uploading default image for {reports_needing_default.count()} reports...')
                try:
                    # Upload once to get the Cloudinary path
                    first_report = reports_needing_default.first()
                    with open(default_fallback_path, 'rb') as f:
                        first_report.feature_image.save('default_image.png', File(f), save=True)
                    default_cloudinary_name = str(first_report.feature_image)
                    uploaded += 1

                    # Bulk-update the rest
                    count = reports_needing_default.exclude(pk=first_report.pk).update(
                        feature_image=default_cloudinary_name
                    )
                    self.stdout.write(self.style.SUCCESS(
                        f'  OK: default image ->{default_cloudinary_name} (applied to {count + 1} reports)'
                    ))
                    uploaded += count
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  ERROR uploading default image: {e}'))
                    errors += reports_needing_default.count()

        # Handle any non-default report images
        for report in Report.objects.exclude(feature_image='default_image.jpg').exclude(feature_image=''):
            field_name = str(report.feature_image)

            if field_name.startswith('http') or 'cloudinary' in field_name or field_name.startswith('images/'):
                self.stdout.write(f'  SKIP (already Cloudinary): {field_name}')
                skipped += 1
                continue

            local_path = os.path.join(media_root, field_name)
            if not os.path.exists(local_path):
                self.stdout.write(self.style.WARNING(f'  MISSING file: {local_path}'))
                errors += 1
                continue

            try:
                with open(local_path, 'rb') as f:
                    report.feature_image.save(os.path.basename(local_path), File(f), save=True)
                self.stdout.write(self.style.SUCCESS(f'  OK: {field_name} ->{report.feature_image.name}'))
                uploaded += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ERROR: {field_name}: {e}'))
                errors += 1

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Done — {uploaded} uploaded/updated, {skipped} skipped, {errors} errors'
        ))
