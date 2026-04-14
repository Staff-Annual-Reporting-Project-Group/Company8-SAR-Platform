"""
Unit tests — Report, Category, Committee, Participant models.

No HTTP client is used here. Each test exercises model-level behaviour
directly: field defaults, properties, ordering, and relationships.

Run with:
    python manage.py test reports.tests.unit --testrunner=test_runner.SARTestRunner
"""

from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase

from reports.models import Category, Committee, Participant, Report


def make_user(username='testuser', password='SecurePass123!', email='test@uwi.edu'):
    return User.objects.create_user(username=username, password=password, email=email)


def make_category(name='Research'):
    return Category.objects.get_or_create(name=name)[0]


def make_report(user, category=None, title='Test Report Title',
                description='This is a test description for the report.'):
    if category is None:
        category = make_category()
    return Report.objects.create(user=user, title=title, description=description, category=category)


# ── Report ────────────────────────────────────────────────────────────────────

class ReportStrTests(TestCase):

    def test_str_contains_username_and_title(self):
        """Report __str__ contains the owner's username and the report title"""
        user = make_user()
        report = make_report(user)
        self.assertIn(user.username, str(report))
        self.assertIn(report.title, str(report))


class ReportDefaultsTests(TestCase):

    def setUp(self):
        self.user = make_user()

    def test_new_report_is_active_by_default(self):
        """A newly created report has isActive=True"""
        report = make_report(self.user)
        self.assertTrue(report.isActive)

    def test_soft_delete_sets_inactive(self):
        """Setting isActive=False soft-deletes a report without removing the database row"""
        report = make_report(self.user)
        report.isActive = False
        report.save()
        self.assertFalse(Report.objects.get(pk=report.pk).isActive)

    def test_soft_deleted_report_still_exists_in_database(self):
        """A soft-deleted report remains in the database and is retrievable by pk"""
        report = make_report(self.user)
        report.isActive = False
        report.save()
        self.assertTrue(Report.objects.filter(pk=report.pk).exists())


class ReportFeatureImgUrlTests(TestCase):

    def setUp(self):
        self.user = make_user()
        self.report = make_report(self.user)

    def test_empty_feature_image_returns_default_url(self):
        """feature_img_url returns DEFAULT_IMAGE when the image field is blank"""
        self.report.feature_image = ''
        self.report.save(update_fields=['feature_image'])
        self.assertEqual(self.report.feature_img_url, Report.DEFAULT_IMAGE)

    def test_stored_https_url_is_returned_unchanged(self):
        """feature_img_url returns a stored https:// URL directly without modification"""
        url = 'https://res.cloudinary.com/demo/image/upload/sample.jpg'
        self.report.feature_image = url
        self.report.save()
        self.assertEqual(self.report.feature_img_url, url)

    def test_default_image_constant_is_https_url(self):
        """DEFAULT_IMAGE constant is a full https:// Cloudinary URL"""
        self.assertTrue(Report.DEFAULT_IMAGE.startswith('https://'))


class ReportOrderingTests(TestCase):

    def test_reports_ordered_newest_date_first(self):
        """Reports are returned with the most recent date_of_report first"""
        user = make_user()
        cat = make_category()
        old = Report.objects.create(user=user, title='Older Report Title',
                                    description='Older description text here.',
                                    category=cat, date_of_report=date(2022, 1, 1))
        new = Report.objects.create(user=user, title='Newer Report Title',
                                    description='Newer description text here.',
                                    category=cat, date_of_report=date(2024, 1, 1))
        first = Report.objects.filter(user=user).first()
        self.assertEqual(first.pk, new.pk)


# ── Category ──────────────────────────────────────────────────────────────────

class CategoryModelTests(TestCase):

    def test_str_returns_category_name(self):
        """Category __str__ returns its name"""
        cat = Category.objects.create(name='Publication')
        self.assertEqual(str(cat), 'Publication')

    def test_category_can_be_created_without_regex(self):
        """A Category can be created with no regex pattern"""
        cat = Category.objects.create(name='Conference')
        self.assertIsNone(cat.regex)


# ── Committee ─────────────────────────────────────────────────────────────────

class CommitteeModelTests(TestCase):

    def test_str_returns_committee_name(self):
        """Committee __str__ returns its name"""
        comm = Committee.objects.create(name='Research & Development')
        self.assertEqual(str(comm), 'Research & Development')


# ── Participant ───────────────────────────────────────────────────────────────

class ParticipantModelTests(TestCase):

    def test_str_returns_participant_name(self):
        """Participant __str__ returns the participant's display name"""
        p = Participant.objects.create(name='Jane Doe')
        self.assertEqual(str(p), 'Jane Doe')

    def test_participant_user_link_is_optional(self):
        """A Participant can exist without being linked to a User account"""
        p = Participant.objects.create(name='External Collaborator Name')
        self.assertIsNone(p.user)

    def test_participant_can_be_linked_to_a_user(self):
        """A Participant can be linked to an existing User account"""
        user = make_user(username='linked', email='linked@uwi.edu')
        p = Participant.objects.create(name='Linked Person Name', user=user)
        self.assertEqual(p.user, user)
