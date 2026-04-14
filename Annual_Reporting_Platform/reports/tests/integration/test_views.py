"""
Integration tests — reports index, report detail, annual report, selected user reports.

Each test fires a real HTTP request through the Django test client and
asserts on the response status, template used, and visible content.

Run with:
    python manage.py test reports.tests.integration --testrunner=test_runner.SARTestRunner
"""

from datetime import date

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from reports.models import Category, Committee, Report

INDEX_URL = reverse('reports:index')
ANNUAL_URL = reverse('reports:annual_report')
PDF_URL = reverse('reports:annual_report_pdf')


def make_user(username='testuser', password='SecurePass123!', email='test@uwi.edu', **kwargs):
    return User.objects.create_user(username=username, password=password, email=email, **kwargs)


def make_category(name='Research'):
    return Category.objects.get_or_create(name=name)[0]


def make_report(user, title='Test Report Title',
                description='This is a valid test report description.',
                report_date=None, active=True):
    r = Report.objects.create(
        user=user, title=title, description=description,
        category=make_category(),
        date_of_report=report_date or date.today(),
        isActive=active,
    )
    return r


# ── Index ─────────────────────────────────────────────────────────────────────

class ReportIndexTests(TestCase):

    def setUp(self):
        cache.clear()
        self.client = Client()
        self.user = make_user()

    def test_index_returns_200(self):
        """GET /reports/ returns HTTP 200"""
        response = self.client.get(INDEX_URL)
        self.assertEqual(response.status_code, 200)

    def test_index_shows_active_reports(self):
        """Active reports appear on the public index page"""
        make_report(self.user, title='Visible Active Report Study')
        response = self.client.get(INDEX_URL)
        self.assertContains(response, 'Visible Active Report Study')

    def test_index_hides_soft_deleted_reports(self):
        """Reports with isActive=False do not appear on the index page"""
        make_report(self.user, title='Hidden Deleted Report Study', active=False)
        response = self.client.get(INDEX_URL)
        self.assertNotContains(response, 'Hidden Deleted Report Study')

    def test_keyword_search_returns_matching_reports(self):
        """Searching by keyword returns only reports whose title or description matches"""
        make_report(self.user, title='Quantum Computing Research Study')
        make_report(self.user, title='Database Architecture Overview Notes')
        response = self.client.get(INDEX_URL + '?q=Quantum')
        self.assertContains(response, 'Quantum Computing Research Study')
        self.assertNotContains(response, 'Database Architecture Overview Notes')

    def test_search_with_no_results_returns_empty_set(self):
        """A search term that matches nothing returns an empty results page"""
        make_report(self.user, title='Machine Learning Research Paper')
        response = self.client.get(INDEX_URL + '?q=xyznonexistent999')
        self.assertNotContains(response, 'Machine Learning Research Paper')

    def test_index_filters_by_category(self):
        """Filtering by category shows only reports in that category"""
        cat_a = Category.objects.create(name='CategoryAlpha')
        cat_b = Category.objects.create(name='CategoryBeta')
        Report.objects.create(user=self.user, title='Alpha Category Report Title',
                               description='Valid description for alpha category.',
                               category=cat_a)
        Report.objects.create(user=self.user, title='Beta Category Report Title',
                               description='Valid description for beta category.',
                               category=cat_b)
        response = self.client.get(INDEX_URL + '?period=this_year&category=CategoryAlpha')
        self.assertContains(response, 'Alpha Category Report Title')
        self.assertNotContains(response, 'Beta Category Report Title')


# ── Report detail ─────────────────────────────────────────────────────────────

class ReportDetailTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.report = make_report(self.user)

    def test_report_detail_returns_200(self):
        """GET /report/<pk> returns HTTP 200 for an active report"""
        url = reverse('reports:report_detail', args=[self.report.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_report_detail_uses_correct_template(self):
        """Report detail page uses the report_details template"""
        url = reverse('reports:report_detail', args=[self.report.pk])
        response = self.client.get(url)
        self.assertTemplateUsed(response, 'reports/report_details.html')

    def test_report_detail_shows_title(self):
        """Report detail page displays the report's title"""
        url = reverse('reports:report_detail', args=[self.report.pk])
        response = self.client.get(url)
        self.assertContains(response, self.report.title)

    def test_soft_deleted_report_returns_404(self):
        """Accessing a soft-deleted report returns HTTP 404"""
        self.report.isActive = False
        self.report.save()
        url = reverse('reports:report_detail', args=[self.report.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_report_detail_shows_committee_name(self):
        """Report detail page lists the committees the report is associated with"""
        committee = Committee.objects.create(name='Visible Test Committee')
        self.report.committees.add(committee)
        url = reverse('reports:report_detail', args=[self.report.pk])
        response = self.client.get(url)
        self.assertContains(response, 'Visible Test Committee')


# ── Annual report ─────────────────────────────────────────────────────────────

class AnnualReportTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = make_user()

    def test_annual_report_page_returns_200(self):
        """GET /annual-report/ returns HTTP 200"""
        response = self.client.get(ANNUAL_URL)
        self.assertEqual(response.status_code, 200)

    def test_year_filter_shows_matching_reports_only(self):
        """Annual report filtered by year shows only reports from that year"""
        cat = make_category()
        Report.objects.create(user=self.user, title='Report From Year 2023 Study',
                               description='Valid description for year 2023.',
                               category=cat, date_of_report=date(2023, 6, 1))
        Report.objects.create(user=self.user, title='Report From Year 2022 Study',
                               description='Valid description for year 2022.',
                               category=cat, date_of_report=date(2022, 6, 1))
        response = self.client.get(ANNUAL_URL + '?range_type=year&year=2023')
        self.assertContains(response, 'Report From Year 2023 Study')
        self.assertNotContains(response, 'Report From Year 2022 Study')

    def test_annual_report_excludes_inactive_reports(self):
        """Soft-deleted reports do not appear in the annual report view"""
        cat = make_category()
        Report.objects.create(user=self.user, title='Deleted Report Invisible In Annual',
                               description='This report is soft deleted.',
                               category=cat, date_of_report=date(2024, 1, 1), isActive=False)
        response = self.client.get(ANNUAL_URL + '?range_type=year&year=2024')
        self.assertNotContains(response, 'Deleted Report Invisible In Annual')

    def test_academic_year_filter_covers_two_calendar_years(self):
        """Academic year filter includes reports from the August–July span"""
        cat = make_category()
        Report.objects.create(user=self.user, title='Academic Year September Report',
                               description='Valid description for academic year test.',
                               category=cat, date_of_report=date(2023, 9, 1))
        Report.objects.create(user=self.user, title='Academic Year March Report',
                               description='Valid description for academic year test.',
                               category=cat, date_of_report=date(2024, 3, 1))
        Report.objects.create(user=self.user, title='Outside Academic Year Report',
                               description='Valid description for outside academic year.',
                               category=cat, date_of_report=date(2022, 5, 1))
        response = self.client.get(ANNUAL_URL + '?range_type=academic&start_year=2023')
        self.assertContains(response, 'Academic Year September Report')
        self.assertContains(response, 'Academic Year March Report')
        self.assertNotContains(response, 'Outside Academic Year Report')

    def test_annual_report_pdf_returns_pdf_content_type(self):
        """The annual report PDF endpoint returns a response with PDF content type"""
        response = self.client.get(PDF_URL + '?range_type=year&year=2024')
        self.assertEqual(response.status_code, 200)
        self.assertIn('pdf', response.get('Content-Type', '').lower())


# ── Selected user reports ─────────────────────────────────────────────────────

class SelectedUserReportsTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = make_user()

    def test_selected_user_reports_returns_200(self):
        """GET /reports/user/<pk>/ returns HTTP 200"""
        url = reverse('reports:selected_user_reports', args=[self.user.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_selected_user_page_shows_that_users_reports(self):
        """The selected user reports page shows reports authored by that user"""
        make_report(self.user, title='Belongs To The Selected Test User')
        url = reverse('reports:selected_user_reports', args=[self.user.pk])
        response = self.client.get(url)
        self.assertContains(response, 'Belongs To The Selected Test User')

    def test_selected_user_page_does_not_show_other_users_reports(self):
        """Reports authored by a different user do not appear on this page"""
        other = make_user(username='other', email='other@uwi.edu')
        make_report(other, title='Belongs To The Other User Only')
        url = reverse('reports:selected_user_reports', args=[self.user.pk])
        response = self.client.get(url)
        self.assertNotContains(response, 'Belongs To The Other User Only')
