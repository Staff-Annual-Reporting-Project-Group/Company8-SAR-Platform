"""
Integration tests — admin report management and account management.

Each test fires a real HTTP request through the Django test client.
Admin views require is_staff=True — the @admin_required decorator
checks is_staff first (short-circuit), so no custom is_admin field is needed.

Run with:
    python manage.py test administration.tests.integration --testrunner=test_runner.SARTestRunner
"""

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from reports.models import Category, Report

ADMIN_REPORTS_URL = reverse('administration:admin-reports')
ADMIN_ACCOUNTS_URL = reverse('administration:admin-accounts')
GENERATE_URL = reverse('administration:generate-reports')


def make_admin(username='admin', password='AdminPass123!', email='admin@uwi.edu'):
    return User.objects.create_user(
        username=username, password=password, email=email,
        is_staff=True, is_active=True,
    )


def make_user(username='staffmember', password='StaffPass123!', email='staff@uwi.edu', **kwargs):
    return User.objects.create_user(username=username, password=password, email=email, **kwargs)


def make_category(name='Research'):
    return Category.objects.get_or_create(name=name)[0]


def make_report(user, title='Admin Test Report Title',
                description='Description for the admin test report.'):
    return Report.objects.create(
        user=user, title=title, description=description, category=make_category()
    )


# ── Access control ────────────────────────────────────────────────────────────

class AdminAccessControlTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.admin = make_admin()
        self.regular_user = make_user()

    def test_unauthenticated_user_is_redirected_from_admin_reports(self):
        """An unauthenticated request to admin-reports is redirected away"""
        response = self.client.get(ADMIN_REPORTS_URL)
        self.assertEqual(response.status_code, 302)

    def test_unauthenticated_user_is_redirected_from_admin_accounts(self):
        """An unauthenticated request to admin-accounts is redirected away"""
        response = self.client.get(ADMIN_ACCOUNTS_URL)
        self.assertEqual(response.status_code, 302)

    def test_unauthenticated_user_is_redirected_from_generate_reports(self):
        """An unauthenticated request to generate-reports is redirected away"""
        response = self.client.get(GENERATE_URL)
        self.assertEqual(response.status_code, 302)

    def test_admin_can_access_admin_reports(self):
        """A staff user can load the admin reports page"""
        self.client.force_login(self.admin)
        response = self.client.get(ADMIN_REPORTS_URL)
        self.assertEqual(response.status_code, 200)

    def test_admin_can_access_admin_accounts(self):
        """A staff user can load the admin accounts page"""
        self.client.force_login(self.admin)
        response = self.client.get(ADMIN_ACCOUNTS_URL)
        self.assertEqual(response.status_code, 200)

    def test_admin_can_access_generate_reports(self):
        """A staff user can load the generate reports page"""
        self.client.force_login(self.admin)
        response = self.client.get(GENERATE_URL)
        self.assertEqual(response.status_code, 200)


# ── Report management ─────────────────────────────────────────────────────────

class AdminReportManagementTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.admin = make_admin()
        self.user = make_user()
        self.client.force_login(self.admin)

    def test_admin_reports_page_lists_active_reports(self):
        """Active reports appear in the admin reports list"""
        make_report(self.user, title='Active Report Visible In Admin Panel')
        response = self.client.get(ADMIN_REPORTS_URL)
        self.assertContains(response, 'Active Report Visible In Admin Panel')

    def test_admin_can_soft_delete_a_report(self):
        """Posting the delete action soft-deletes the report (isActive=False)"""
        report = make_report(self.user)
        self.client.post(ADMIN_REPORTS_URL, {'action': 'delete', 'report_id': report.pk})
        report.refresh_from_db()
        self.assertFalse(report.isActive)

    def test_soft_deleted_report_no_longer_appears_in_admin_list(self):
        """After soft-deleting a report it is not shown in the admin report list"""
        report = make_report(self.user, title='Report To Be Hidden After Deletion')
        self.client.post(ADMIN_REPORTS_URL, {'action': 'delete', 'report_id': report.pk}, follow=True)
        response = self.client.get(ADMIN_REPORTS_URL)
        self.assertNotContains(response, 'Report To Be Hidden After Deletion')

    def test_admin_can_search_reports_by_keyword(self):
        """Admin keyword search returns matching reports and hides non-matching ones"""
        make_report(self.user, title='Blockchain Technology Research Study')
        make_report(self.user, title='Machine Learning Overview Research Paper')
        response = self.client.get(ADMIN_REPORTS_URL + '?q=Blockchain')
        self.assertContains(response, 'Blockchain Technology Research Study')
        self.assertNotContains(response, 'Machine Learning Overview Research Paper')

    def test_admin_report_filter_by_category(self):
        """Admin can filter the report list by category name"""
        cat_a = Category.objects.create(name='AdminCategoryAlpha')
        cat_b = Category.objects.create(name='AdminCategoryBeta')
        Report.objects.create(user=self.user, title='Alpha Category Admin Report',
                               description='Valid description for alpha category report.',
                               category=cat_a)
        Report.objects.create(user=self.user, title='Beta Category Admin Report',
                               description='Valid description for beta category report.',
                               category=cat_b)
        response = self.client.get(ADMIN_REPORTS_URL + '?category=AdminCategoryAlpha')
        self.assertContains(response, 'Alpha Category Admin Report')
        self.assertNotContains(response, 'Beta Category Admin Report')

    def test_admin_can_search_reports_by_username(self):
        """Admin can filter the report list by the author's username"""
        other = make_user(username='specific.author', email='author@uwi.edu')
        make_report(self.user, title='Report By The Default Staff User')
        make_report(other, title='Report By The Specific Author User')
        response = self.client.get(ADMIN_REPORTS_URL + '?username=specific.author')
        self.assertContains(response, 'Report By The Specific Author User')
        self.assertNotContains(response, 'Report By The Default Staff User')


# ── Account management ────────────────────────────────────────────────────────

class AdminAccountManagementTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.admin = make_admin()
        self.target_user = make_user()
        self.client.force_login(self.admin)

    def test_admin_can_deactivate_an_active_user_account(self):
        """Admin can deactivate an active user account"""
        self.client.post(ADMIN_ACCOUNTS_URL, {
            'action': 'deactivate', 'user_id': self.target_user.pk,
        })
        self.target_user.refresh_from_db()
        self.assertFalse(self.target_user.is_active)

    def test_admin_can_reactivate_a_deactivated_account(self):
        """Admin can reactivate a previously deactivated user account"""
        self.target_user.is_active = False
        self.target_user.save()
        self.client.post(ADMIN_ACCOUNTS_URL, {
            'action': 'activate', 'user_id': self.target_user.pk,
        })
        self.target_user.refresh_from_db()
        self.assertTrue(self.target_user.is_active)

    def test_admin_cannot_deactivate_their_own_account(self):
        """An admin cannot deactivate their own account through the accounts page"""
        self.client.post(ADMIN_ACCOUNTS_URL, {
            'action': 'deactivate', 'user_id': self.admin.pk,
        })
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_active_users_appear_in_active_tab(self):
        """An active user appears on the active accounts tab"""
        response = self.client.get(ADMIN_ACCOUNTS_URL + '?tab=active')
        self.assertContains(response, self.target_user.username)

    def test_deactivated_user_appears_in_inactive_tab(self):
        """A deactivated user appears on the inactive accounts tab"""
        self.target_user.is_active = False
        self.target_user.save()
        response = self.client.get(ADMIN_ACCOUNTS_URL + '?tab=inactive')
        self.assertContains(response, self.target_user.username)

    def test_deactivated_user_does_not_appear_in_active_tab(self):
        """A deactivated user does not appear on the active accounts tab"""
        self.target_user.is_active = False
        self.target_user.save()
        response = self.client.get(ADMIN_ACCOUNTS_URL + '?tab=active')
        self.assertNotContains(response, self.target_user.username)

    def test_admin_can_search_accounts_by_username(self):
        """Admin account search filters the user list by username"""
        make_user(username='findable.user', email='findable@uwi.edu')
        response = self.client.get(ADMIN_ACCOUNTS_URL + '?q=findable.user')
        self.assertContains(response, 'findable.user')
        self.assertNotContains(response, self.target_user.username)
