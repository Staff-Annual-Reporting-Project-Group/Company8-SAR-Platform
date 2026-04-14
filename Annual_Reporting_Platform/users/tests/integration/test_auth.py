"""
Integration tests — authentication (login, logout, register).

Each test fires a real HTTP request through the Django test client and
asserts on the response, session state, and database.

Run with:
    python manage.py test users.tests.integration --testrunner=test_runner.SARTestRunner
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.messages import get_messages


LOGIN_URL    = reverse('users:login')
LOGOUT_URL   = reverse('users:logout')
REGISTER_URL = reverse('users:register')


def make_user(username='testuser', password='SecurePass123!', email='test@uwi.edu', **kwargs):
    return User.objects.create_user(
        username=username, password=password, email=email, **kwargs
    )


# ── login page ────────────────────────────────────────────────────────────────

class LoginPageTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = make_user()

    def test_login_page_returns_200(self):
        """GET /users/login/ returns HTTP 200"""
        response = self.client.get(LOGIN_URL)
        self.assertEqual(response.status_code, 200)

    def test_login_page_uses_login_template(self):
        """Login page renders the users/login.html template"""
        response = self.client.get(LOGIN_URL)
        self.assertTemplateUsed(response, 'users/login.html')

    def test_login_page_contains_username_and_password_fields(self):
        """Login form contains username and password input fields"""
        response = self.client.get(LOGIN_URL)
        self.assertContains(response, 'name="username"')
        self.assertContains(response, 'name="password"')

    def test_valid_credentials_redirect_to_reports_index(self):
        """Submitting correct credentials redirects to the reports index"""
        response = self.client.post(LOGIN_URL, {
            'username': 'testuser',
            'password': 'SecurePass123!',
        })
        self.assertRedirects(response, reverse('reports:index'),
                             fetch_redirect_response=False)

    def test_successful_login_stores_user_in_session(self):
        """After a successful login the user ID is stored in the session"""
        self.client.post(LOGIN_URL, {
            'username': 'testuser',
            'password': 'SecurePass123!',
        })
        self.assertIn('_auth_user_id', self.client.session)

    def test_login_with_email_address_is_accepted(self):
        """The username field also accepts an email address to log in"""
        response = self.client.post(LOGIN_URL, {
            'username': 'test@uwi.edu',
            'password': 'SecurePass123!',
        })
        self.assertRedirects(response, reverse('reports:index'),
                             fetch_redirect_response=False)

    def test_wrong_password_shows_error_message(self):
        """Submitting a wrong password keeps the user on the login page with an error"""
        response = self.client.post(LOGIN_URL, {
            'username': 'testuser',
            'password': 'WrongPassword!',
        })
        self.assertEqual(response.status_code, 200)
        msgs = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any('password' in str(m).lower() or 'username' in str(m).lower()
                for m in msgs)
        )

    def test_unknown_username_redirects_back_to_login(self):
        """Submitting a username that does not exist redirects back to the login page"""
        response = self.client.post(LOGIN_URL, {
            'username': 'nobody',
            'password': 'AnyPassword1!',
        })
        self.assertRedirects(response, LOGIN_URL, fetch_redirect_response=False)

    def test_empty_credentials_do_not_create_a_session(self):
        """Submitting empty username and password does not log anyone in"""
        self.client.post(LOGIN_URL, {'username': '', 'password': ''})
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_deactivated_account_cannot_log_in(self):
        """A user whose account has been deactivated is denied access"""
        self.user.is_active = False
        self.user.save()
        self.client.post(LOGIN_URL, {
            'username': 'testuser',
            'password': 'SecurePass123!',
        })
        self.assertNotIn('_auth_user_id', self.client.session)


# ── logout ────────────────────────────────────────────────────────────────────

class LogoutTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = make_user()

    def test_logout_redirects_to_reports_index(self):
        """Logging out redirects the user to the reports index page"""
        self.client.force_login(self.user)
        response = self.client.get(LOGOUT_URL)
        self.assertRedirects(response, reverse('reports:index'),
                             fetch_redirect_response=False)

    def test_logout_removes_user_from_session(self):
        """After logout the user ID is no longer present in the session"""
        self.client.force_login(self.user)
        self.assertIn('_auth_user_id', self.client.session)
        self.client.get(LOGOUT_URL)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_visiting_logout_while_not_logged_in_does_not_error(self):
        """Hitting the logout URL without an active session still redirects cleanly"""
        response = self.client.get(LOGOUT_URL)
        self.assertEqual(response.status_code, 302)


# ── register ──────────────────────────────────────────────────────────────────

class RegisterTests(TestCase):

    def setUp(self):
        self.client = Client()

    def test_register_page_returns_200(self):
        """GET /users/register/ returns HTTP 200"""
        response = self.client.get(REGISTER_URL)
        self.assertEqual(response.status_code, 200)

    def test_register_page_uses_register_template(self):
        """Register page renders the users/register.html template"""
        response = self.client.get(REGISTER_URL)
        self.assertTemplateUsed(response, 'users/register.html')

    def test_valid_registration_creates_a_new_user(self):
        """Submitting valid registration details creates a user in the database"""
        self.client.post(REGISTER_URL, {
            'username':   'newstaff',
            'first_name': 'Jane',
            'last_name':  'Doe',
            'email':      'jane.doe@uwi.edu',
            'password':   'StrongPass99!',
            'password2':  'StrongPass99!',
        })
        self.assertTrue(User.objects.filter(username='newstaff').exists())

    def test_duplicate_username_is_rejected(self):
        """Registering with an already-taken username does not create a second user"""
        make_user(username='existing')
        before = User.objects.count()
        self.client.post(REGISTER_URL, {
            'username':   'existing',
            'first_name': 'Other',
            'last_name':  'Person',
            'email':      'other@uwi.edu',
            'password':   'StrongPass99!',
            'password2':  'StrongPass99!',
        })
        self.assertEqual(User.objects.count(), before)

    def test_mismatched_passwords_are_rejected(self):
        """Registration fails when the two password fields do not match"""
        before = User.objects.count()
        self.client.post(REGISTER_URL, {
            'username':   'brandnew',
            'first_name': 'Test',
            'last_name':  'User',
            'email':      'new@uwi.edu',
            'password':   'StrongPass99!',
            'password2':  'DifferentPass99!',
        })
        self.assertEqual(User.objects.count(), before)
