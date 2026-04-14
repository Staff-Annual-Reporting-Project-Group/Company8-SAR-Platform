"""
Integration tests — CSV bulk import for reports and staff accounts.

Each test exercises the full upload → session → preview → confirm pipeline
through the Django test client.

Run with:
    python manage.py test administration.tests.integration --testrunner=test_runner.SARTestRunner
"""

import io
import json

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from reports.models import Category, Report

GENERATE_URL = reverse('administration:generate-reports')
CSV_PREVIEW_REPORTS_URL = reverse('administration:csv-preview-reports')
CSV_UPLOAD_STAFF_URL = reverse('administration:csv-upload-staff')
CSV_PREVIEW_STAFF_URL = reverse('administration:csv-preview-staff')


def make_admin(username='admin', password='AdminPass123!', email='admin@uwi.edu'):
    return User.objects.create_user(
        username=username, password=password, email=email,
        is_staff=True, is_active=True,
    )


def make_user(username='staffmember', password='StaffPass123!', email='staff@uwi.edu', **kwargs):
    return User.objects.create_user(username=username, password=password, email=email, **kwargs)


def make_csv_file(content, filename='test.csv'):
    """Return an in-memory file object suitable for test client multipart upload."""
    f = io.BytesIO(content.encode('utf-8'))
    f.name = filename
    return f


# ── Reports CSV — upload & session ────────────────────────────────────────────

class ReportCSVUploadTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.admin = make_admin()
        self.user = make_user()
        self.client.force_login(self.admin)

    def _upload(self, csv_content, filename='test.csv'):
        return self.client.post(GENERATE_URL, {
            'csv_file': make_csv_file(csv_content, filename),
        }, format='multipart')

    def test_valid_csv_redirects_to_reports_preview(self):
        """Uploading a valid reports CSV redirects to the preview page"""
        csv_content = (
            'username,title,description,category,date_of_report,committees,participants\n'
            f'{self.user.username},First Report Title,Valid description long enough.,Research,2024-01-01,,\n'
        )
        response = self._upload(csv_content)
        self.assertRedirects(response, CSV_PREVIEW_REPORTS_URL, fetch_redirect_response=False)

    def test_non_csv_file_is_rejected(self):
        """Uploading a non-CSV file type is rejected and stays on generate reports"""
        response = self.client.post(GENERATE_URL, {
            'csv_file': make_csv_file('not a csv', 'report.txt'),
        }, format='multipart')
        self.assertRedirects(response, GENERATE_URL, fetch_redirect_response=False)

    def test_valid_row_is_stored_as_valid_in_session(self):
        """A CSV row with a recognised username and required fields is stored as valid"""
        csv_content = (
            'username,title,description,category,date_of_report,committees,participants\n'
            f'{self.user.username},Valid Report Title,Valid description long enough.,Research,2024-01-01,,\n'
        )
        self._upload(csv_content)
        rows = self.client.session.get('csv_report_rows', [])
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]['valid'])

    def test_unknown_username_is_flagged_as_invalid(self):
        """A CSV row referencing a non-existent username is stored as invalid"""
        csv_content = (
            'username,title,description,category,date_of_report,committees,participants\n'
            'nobody_at_all,Some Report Title,Valid description long enough.,Research,2024-01-01,,\n'
        )
        self._upload(csv_content)
        rows = self.client.session.get('csv_report_rows', [])
        self.assertEqual(len(rows), 1)
        self.assertFalse(rows[0]['valid'])

    def test_bad_date_format_is_flagged_as_invalid(self):
        """A CSV row with a malformed date is stored as invalid"""
        csv_content = (
            'username,title,description,category,date_of_report,committees,participants\n'
            f'{self.user.username},Title Here,Valid description long enough.,Research,01/01/2024,,\n'
        )
        self._upload(csv_content)
        rows = self.client.session.get('csv_report_rows', [])
        self.assertFalse(rows[0]['valid'])

    def test_empty_csv_shows_error_and_stays_on_generate_page(self):
        """A CSV containing only a header row (no data) shows an error"""
        csv_content = 'username,title,description,category,date_of_report,committees,participants\n'
        response = self._upload(csv_content)
        self.assertRedirects(response, GENERATE_URL, fetch_redirect_response=False)

    def test_multiple_rows_are_all_stored_in_session(self):
        """Multiple valid rows from one CSV are all stored in the session"""
        csv_content = (
            'username,title,description,category,date_of_report,committees,participants\n'
            f'{self.user.username},First Report Here,Valid description long enough.,Research,2024-01-01,,\n'
            f'{self.user.username},Second Report Here,Valid description long enough.,Research,2024-02-01,,\n'
            f'{self.user.username},Third Report Here,Valid description long enough.,Research,2024-03-01,,\n'
        )
        self._upload(csv_content)
        rows = self.client.session.get('csv_report_rows', [])
        self.assertEqual(len(rows), 3)


# ── Reports CSV — confirm & import ────────────────────────────────────────────

class ReportCSVConfirmTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.admin = make_admin()
        self.user = make_user()
        self.client.force_login(self.admin)

    def _upload_rows(self, extra_rows=''):
        csv_content = (
            'username,title,description,category,date_of_report,committees,participants\n'
            f'{self.user.username},Imported Report Number One,Valid description long enough.,Research,2024-03-01,,\n'
            + extra_rows
        )
        self.client.post(GENERATE_URL, {
            'csv_file': make_csv_file(csv_content),
        }, format='multipart')

    def _confirm(self, kept_indices):
        return self.client.post(CSV_PREVIEW_REPORTS_URL, {
            'kept_indices': json.dumps(kept_indices),
        })

    def test_confirming_import_creates_report_in_database(self):
        """Confirming the preview creates the expected Report record"""
        self._upload_rows()
        rows = self.client.session.get('csv_report_rows', [])
        kept = [r['idx'] for r in rows if r['valid']]
        before = Report.objects.count()
        self._confirm(kept)
        self.assertEqual(Report.objects.count(), before + 1)

    def test_three_rows_create_three_reports(self):
        """Confirming three valid rows creates three new Report records"""
        extra = (
            f'{self.user.username},Imported Report Number Two,Valid description long enough.,Research,2024-04-01,,\n'
            f'{self.user.username},Imported Report Number Three,Valid description long enough.,Research,2024-05-01,,\n'
        )
        self._upload_rows(extra_rows=extra)
        rows = self.client.session.get('csv_report_rows', [])
        kept = [r['idx'] for r in rows if r['valid']]
        before = Report.objects.count()
        self._confirm(kept)
        self.assertEqual(Report.objects.count(), before + 3)

    def test_imported_report_belongs_to_specified_user(self):
        """The imported report is attributed to the user named in the CSV"""
        self._upload_rows()
        rows = self.client.session.get('csv_report_rows', [])
        kept = [r['idx'] for r in rows if r['valid']]
        self._confirm(kept)
        report = Report.objects.filter(title='Imported Report Number One').first()
        self.assertIsNotNone(report)
        self.assertEqual(report.user, self.user)

    def test_duplicate_report_is_skipped(self):
        """Importing a report that already exists for that user is skipped"""
        cat, _ = Category.objects.get_or_create(name='Research')
        Report.objects.create(user=self.user, title='Imported Report Number One',
                               description='Pre-existing description.', category=cat)
        self._upload_rows()
        rows = self.client.session.get('csv_report_rows', [])
        kept = [r['idx'] for r in rows if r['valid']]
        before = Report.objects.count()
        self._confirm(kept)
        self.assertEqual(Report.objects.count(), before)

    def test_deselected_row_is_not_imported(self):
        """A row excluded from kept_indices is not saved to the database"""
        extra = (
            f'{self.user.username},Excluded Report Not Imported,'
            f'Valid description long enough.,Research,2024-04-01,,\n'
        )
        self._upload_rows(extra_rows=extra)
        rows = self.client.session.get('csv_report_rows', [])
        # Only keep the first row
        kept = [rows[0]['idx']] if rows else []
        self._confirm(kept)
        self.assertFalse(Report.objects.filter(title='Excluded Report Not Imported').exists())

    def test_report_committees_are_linked_on_import(self):
        """Committees listed in the CSV are linked to the imported report"""
        csv_content = (
            'username,title,description,category,date_of_report,committees,participants\n'
            f'{self.user.username},Report With Committee Linked,Valid description long enough.,'
            f'Research,2024-01-01,Research & Development,\n'
        )
        self.client.post(GENERATE_URL, {'csv_file': make_csv_file(csv_content)}, format='multipart')
        rows = self.client.session.get('csv_report_rows', [])
        kept = [r['idx'] for r in rows if r['valid']]
        self._confirm(kept)
        report = Report.objects.filter(title='Report With Committee Linked').first()
        self.assertIsNotNone(report)
        self.assertTrue(report.committees.filter(name='Research & Development').exists())

    def test_session_is_cleared_after_import(self):
        """The session csv_report_rows key is removed after a successful import"""
        self._upload_rows()
        rows = self.client.session.get('csv_report_rows', [])
        kept = [r['idx'] for r in rows if r['valid']]
        self._confirm(kept)
        self.assertNotIn('csv_report_rows', self.client.session)


# ── Staff CSV — upload & session ──────────────────────────────────────────────

class StaffCSVUploadTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.admin = make_admin()
        self.client.force_login(self.admin)

    def _upload(self, csv_content):
        return self.client.post(CSV_UPLOAD_STAFF_URL, {
            'staff_csv_file': make_csv_file(csv_content),
        }, format='multipart')

    def test_valid_staff_csv_redirects_to_preview(self):
        """Uploading a valid staff CSV redirects to the staff preview page"""
        csv_content = 'first_name,last_name,email,photo_url\nJane,Smith,jane.smith@uwi.edu,\n'
        response = self._upload(csv_content)
        self.assertRedirects(response, CSV_PREVIEW_STAFF_URL, fetch_redirect_response=False)

    def test_new_user_row_is_flagged_as_new(self):
        """A row whose name and email are not in the database is flagged as a new account"""
        csv_content = 'first_name,last_name,email,photo_url\nBrand,Newuser,brandnew@uwi.edu,\n'
        self._upload(csv_content)
        rows = self.client.session.get('csv_staff_rows', [])
        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0]['existing_id'])

    def test_existing_user_matched_by_email_is_flagged_as_existing(self):
        """A row whose email matches an existing account is flagged as existing"""
        make_user(username='existing.person', email='existing@uwi.edu',
                  first_name='Jane', last_name='Smith')
        csv_content = 'first_name,last_name,email,photo_url\nJane,Smith,existing@uwi.edu,\n'
        self._upload(csv_content)
        rows = self.client.session.get('csv_staff_rows', [])
        self.assertIsNotNone(rows[0]['existing_id'])
        self.assertEqual(rows[0]['match_reason'], 'email')

    def test_existing_user_matched_by_name_is_flagged_as_existing(self):
        """A row whose first+last name matches an existing account is flagged as existing"""
        make_user(username='name.match', email='namematch@uwi.edu',
                  first_name='Robert', last_name='Johnson')
        csv_content = 'first_name,last_name,email,photo_url\nRobert,Johnson,different@uwi.edu,\n'
        self._upload(csv_content)
        rows = self.client.session.get('csv_staff_rows', [])
        self.assertIsNotNone(rows[0]['existing_id'])
        self.assertEqual(rows[0]['match_reason'], 'name')

    def test_missing_first_name_is_flagged_as_invalid(self):
        """A staff CSV row with no first_name is stored as invalid"""
        csv_content = 'first_name,last_name,email,photo_url\n,Smith,no.firstname@uwi.edu,\n'
        self._upload(csv_content)
        rows = self.client.session.get('csv_staff_rows', [])
        self.assertFalse(rows[0]['valid'])

    def test_username_is_suggested_for_new_users(self):
        """A username is automatically suggested for new user rows"""
        csv_content = 'first_name,last_name,email,photo_url\nAutomatic,Username,auto@uwi.edu,\n'
        self._upload(csv_content)
        rows = self.client.session.get('csv_staff_rows', [])
        self.assertTrue(len(rows[0]['username']) > 0)


# ── Staff CSV — confirm & import ──────────────────────────────────────────────

class StaffCSVConfirmTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.admin = make_admin()
        self.client.force_login(self.admin)

    def _upload(self, csv_content):
        self.client.post(CSV_UPLOAD_STAFF_URL, {
            'staff_csv_file': make_csv_file(csv_content),
        }, format='multipart')

    def _confirm(self, kept_indices):
        return self.client.post(CSV_PREVIEW_STAFF_URL, {
            'kept_indices': json.dumps(kept_indices),
        })

    def test_confirming_import_creates_new_user_account(self):
        """Confirming a new staff row creates a User account in the database"""
        self._upload('first_name,last_name,email,photo_url\nNewStaff,Person,newstaff@uwi.edu,\n')
        rows = self.client.session.get('csv_staff_rows', [])
        kept = [r['idx'] for r in rows]
        before = User.objects.count()
        self._confirm(kept)
        self.assertEqual(User.objects.count(), before + 1)
        self.assertTrue(User.objects.filter(email='newstaff@uwi.edu').exists())

    def test_new_user_is_created_as_active(self):
        """A newly imported staff member is created with is_active=True"""
        self._upload('first_name,last_name,email,photo_url\nActive,Staff,activestaff@uwi.edu,\n')
        rows = self.client.session.get('csv_staff_rows', [])
        kept = [r['idx'] for r in rows]
        self._confirm(kept)
        user = User.objects.filter(email='activestaff@uwi.edu').first()
        self.assertTrue(user.is_active)

    def test_confirming_import_updates_existing_users_email(self):
        """Confirming a row that matches an existing user updates their email"""
        existing = make_user(username='updateme', email='old@uwi.edu',
                             first_name='Update', last_name='Me')
        self._upload('first_name,last_name,email,photo_url\nUpdate,Me,updated@uwi.edu,\n')
        rows = self.client.session.get('csv_staff_rows', [])
        kept = [r['idx'] for r in rows]
        self._confirm(kept)
        existing.refresh_from_db()
        self.assertEqual(existing.email, 'updated@uwi.edu')

    def test_inactive_existing_user_is_reactivated(self):
        """Importing a row that matches an inactive user reactivates their account"""
        existing = make_user(username='inactive.staff', email='inactive@uwi.edu',
                             first_name='Inactive', last_name='Staff', is_active=False)
        self._upload('first_name,last_name,email,photo_url\nInactive,Staff,inactive@uwi.edu,\n')
        rows = self.client.session.get('csv_staff_rows', [])
        kept = [r['idx'] for r in rows]
        self._confirm(kept)
        existing.refresh_from_db()
        self.assertTrue(existing.is_active)

    def test_deselected_row_prevents_user_creation(self):
        """A row excluded from kept_indices is not imported"""
        self._upload('first_name,last_name,email,photo_url\nSkipped,User,skipped@uwi.edu,\n')
        self._confirm([])
        self.assertFalse(User.objects.filter(email='skipped@uwi.edu').exists())

    def test_session_is_cleared_after_staff_import(self):
        """The session csv_staff_rows key is removed after a successful import"""
        self._upload('first_name,last_name,email,photo_url\nClean,Session,clean@uwi.edu,\n')
        rows = self.client.session.get('csv_staff_rows', [])
        kept = [r['idx'] for r in rows]
        self._confirm(kept)
        self.assertNotIn('csv_staff_rows', self.client.session)
