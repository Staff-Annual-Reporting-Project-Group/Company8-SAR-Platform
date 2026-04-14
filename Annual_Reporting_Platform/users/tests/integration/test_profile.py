"""
Integration tests — profile, create/edit/delete report, account settings.

Each test fires a real HTTP request through the Django test client.

Run with:
    python manage.py test users.tests.integration --testrunner=test_runner.SARTestRunner
"""

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from reports.models import Category, Committee, Report

PROFILE_URL = reverse('users:profile')
CREATE_URL = reverse('users:create-report')
ACCOUNT_URL = reverse('users:account')


def make_user(username='testuser', password='SecurePass123!', email='test@uwi.edu', **kwargs):
    return User.objects.create_user(username=username, password=password, email=email, **kwargs)


def make_category(name='Research'):
    return Category.objects.get_or_create(name=name)[0]


def make_report(user, title='Existing Report Title',
                description='An existing report with a long enough description.'):
    return Report.objects.create(
        user=user, title=title, description=description, category=make_category()
    )


# ── Profile view ──────────────────────────────────────────────────────────────

class ProfileViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = make_user()

    def test_profile_redirects_to_login_when_not_authenticated(self):
        """Visiting the profile page while logged out redirects to login"""
        response = self.client.get(PROFILE_URL)
        self.assertEqual(response.status_code, 302)

    def test_profile_returns_200_when_logged_in(self):
        """A logged-in user can access their profile page"""
        self.client.force_login(self.user)
        response = self.client.get(PROFILE_URL)
        self.assertEqual(response.status_code, 200)

    def test_profile_shows_only_own_reports(self):
        """Profile page displays the current user's reports but not other users' reports"""
        other = make_user(username='other', email='other@uwi.edu')
        make_report(self.user, title='My Own Research Report Title')
        make_report(other, title='Someone Elses Report That Is Different')
        self.client.force_login(self.user)
        response = self.client.get(PROFILE_URL)
        self.assertContains(response, 'My Own Research Report Title')
        self.assertNotContains(response, 'Someone Elses Report That Is Different')

    def test_profile_search_filters_to_matching_reports(self):
        """Searching on the profile page shows only reports matching the keyword"""
        make_report(self.user, title='Machine Learning Research Results')
        make_report(self.user, title='Database Architecture Review Notes')
        self.client.force_login(self.user)
        response = self.client.get(PROFILE_URL + '?q=Machine Learning')
        self.assertContains(response, 'Machine Learning Research Results')
        self.assertNotContains(response, 'Database Architecture Review Notes')


# ── Create report ─────────────────────────────────────────────────────────────

class CreateReportTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.category = make_category()

    def test_create_report_requires_login(self):
        """Accessing the create-report page while logged out redirects"""
        response = self.client.get(CREATE_URL)
        self.assertEqual(response.status_code, 302)

    def test_create_report_page_returns_200_when_logged_in(self):
        """A logged-in user can access the create report page"""
        self.client.force_login(self.user)
        response = self.client.get(CREATE_URL)
        self.assertEqual(response.status_code, 200)

    def test_valid_submission_creates_report_in_database(self):
        """Submitting valid report data saves a new Report to the database"""
        self.client.force_login(self.user)
        before = Report.objects.count()
        self.client.post(CREATE_URL, {
            'title': 'A Valid New Report Title Here',
            'description': 'This is a valid description that is long enough to pass all validation.',
            'category': self.category.pk,
        })
        self.assertEqual(Report.objects.count(), before + 1)

    def test_created_report_is_owned_by_logged_in_user(self):
        """The newly created report is attributed to the currently logged-in user"""
        self.client.force_login(self.user)
        self.client.post(CREATE_URL, {
            'title': 'Report Owned By The Test User',
            'description': 'This is a valid description that is long enough to pass all validation.',
            'category': self.category.pk,
        })
        report = Report.objects.filter(title='Report Owned By The Test User').first()
        self.assertIsNotNone(report)
        self.assertEqual(report.user, self.user)

    def test_report_is_created_with_three_reports_for_same_user(self):
        """Three separate valid reports can be created by the same user"""
        self.client.force_login(self.user)
        titles = [
            'First Research Report Created Here',
            'Second Research Report Created Here',
            'Third Research Report Created Here',
        ]
        for title in titles:
            self.client.post(CREATE_URL, {
                'title': title,
                'description': 'This is a valid description that is long enough to pass all validation.',
                'category': self.category.pk,
            })
        self.assertEqual(Report.objects.filter(user=self.user).count(), 3)

    def test_report_created_with_committee_is_linked(self):
        """A report submitted with a committee correctly links that committee"""
        committee = Committee.objects.create(name='Research And Development Committee')
        self.client.force_login(self.user)
        self.client.post(CREATE_URL, {
            'title': 'Report Linked To A Committee',
            'description': 'This is a valid description that is long enough to pass all validation.',
            'category': self.category.pk,
            'committees': [committee.pk],
        })
        report = Report.objects.filter(title='Report Linked To A Committee').first()
        self.assertIsNotNone(report)
        self.assertIn(committee, report.committees.all())

    def test_short_title_is_rejected(self):
        """A title shorter than 5 characters is rejected and no report is created"""
        self.client.force_login(self.user)
        before = Report.objects.count()
        self.client.post(CREATE_URL, {
            'title': 'Hi',
            'description': 'This is a valid description that is long enough to pass all validation.',
            'category': self.category.pk,
        })
        self.assertEqual(Report.objects.count(), before)

    def test_missing_description_is_rejected(self):
        """Submitting a report with no description does not create a report"""
        self.client.force_login(self.user)
        before = Report.objects.count()
        self.client.post(CREATE_URL, {
            'title': 'A Valid Title For The Report',
            'description': '',
            'category': self.category.pk,
        })
        self.assertEqual(Report.objects.count(), before)

    def test_missing_category_is_rejected(self):
        """Submitting a report with no category selected does not create a report"""
        self.client.force_login(self.user)
        before = Report.objects.count()
        self.client.post(CREATE_URL, {
            'title': 'A Valid Title For The Report',
            'description': 'This is a valid description that is long enough to pass all validation.',
            'category': '',
        })
        self.assertEqual(Report.objects.count(), before)


# ── Edit report ───────────────────────────────────────────────────────────────

class EditReportTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.report = make_report(self.user)

    def test_edit_report_requires_login(self):
        """Accessing the edit-report page while logged out redirects"""
        url = reverse('users:edit-report', args=[self.report.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_edit_report_page_returns_200_for_owner(self):
        """A report owner can load the edit page for their own report"""
        self.client.force_login(self.user)
        url = reverse('users:edit-report', args=[self.report.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_non_owner_cannot_access_edit_page(self):
        """A user who does not own the report receives a 404 on the edit page"""
        other = make_user(username='other', email='other@uwi.edu')
        self.client.force_login(other)
        url = reverse('users:edit-report', args=[self.report.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_valid_edit_updates_title(self):
        """Submitting valid edits updates the report title in the database"""
        new_cat = make_category(name='Updated Category')
        self.client.force_login(self.user)
        url = reverse('users:edit-report', args=[self.report.pk])
        self.client.post(url, {
            'title': 'Updated Report Title After The Edit',
            'description': 'Updated description that is long enough to pass all validation checks.',
            'category': new_cat.pk,
        })
        self.report.refresh_from_db()
        self.assertEqual(self.report.title, 'Updated Report Title After The Edit')

    def test_valid_edit_updates_description(self):
        """Submitting valid edits updates the report description in the database"""
        self.client.force_login(self.user)
        url = reverse('users:edit-report', args=[self.report.pk])
        self.client.post(url, {
            'title': 'Report With Updated Description Title',
            'description': 'This is the brand new updated description that passes all checks.',
            'category': self.report.category.pk,
        })
        self.report.refresh_from_db()
        self.assertEqual(self.report.description,
                         'This is the brand new updated description that passes all checks.')

    def test_edit_page_pre_fills_existing_report_data(self):
        """The edit page is pre-filled with the current report title and description"""
        self.client.force_login(self.user)
        url = reverse('users:edit-report', args=[self.report.pk])
        response = self.client.get(url)
        self.assertContains(response, self.report.title)


# ── Delete report ─────────────────────────────────────────────────────────────

class DeleteReportTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.report = make_report(self.user)

    def test_delete_requires_login(self):
        """The delete endpoint requires authentication — unauthenticated request redirects"""
        url = reverse('users:delete-report', args=[self.report.pk])
        self.client.post(url)
        self.assertTrue(Report.objects.filter(pk=self.report.pk).exists())

    def test_owner_can_delete_own_report(self):
        """A user can permanently delete their own report"""
        self.client.force_login(self.user)
        url = reverse('users:delete-report', args=[self.report.pk])
        self.client.post(url)
        self.assertFalse(Report.objects.filter(pk=self.report.pk).exists())

    def test_non_owner_cannot_delete_report(self):
        """A user cannot delete a report that belongs to someone else"""
        other = make_user(username='other', email='other@uwi.edu')
        self.client.force_login(other)
        url = reverse('users:delete-report', args=[self.report.pk])
        self.client.post(url)
        self.assertTrue(Report.objects.filter(pk=self.report.pk).exists())

    def test_delete_redirects_to_profile(self):
        """Deleting a report redirects the user back to their profile page"""
        self.client.force_login(self.user)
        url = reverse('users:delete-report', args=[self.report.pk])
        response = self.client.post(url)
        self.assertRedirects(response, PROFILE_URL, fetch_redirect_response=False)
