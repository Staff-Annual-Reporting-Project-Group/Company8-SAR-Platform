"""
Unit tests — administration helper functions.

Tests the username suggestion and existing-user lookup helpers used by
the CSV staff import pipeline. No HTTP client or database views involved.

Run with:
    python manage.py test administration.tests.unit --testrunner=test_runner.SARTestRunner
"""

from django.contrib.auth.models import User
from django.test import TestCase

from administration.views import _find_existing_user, _suggest_username


def make_user(username, first_name='', last_name='', email=''):
    return User.objects.create_user(
        username=username, password='Pass123!',
        first_name=first_name, last_name=last_name, email=email,
    )


# ── _suggest_username ─────────────────────────────────────────────────────────

class SuggestUsernameTests(TestCase):

    def test_returns_firstname_dot_lastname(self):
        """Username suggestion follows the firstname.lastname pattern"""
        username = _suggest_username('Jane', 'Doe')
        self.assertEqual(username, 'jane.doe')

    def test_special_characters_are_stripped(self):
        """Non-alphanumeric characters (except dots) are removed from the suggestion"""
        username = _suggest_username("O'Brien", 'Smith-Jones')
        self.assertNotIn("'", username)
        self.assertNotIn('-', username)

    def test_collision_appends_counter(self):
        """When the suggested username is already taken a numeric suffix is added"""
        make_user('jane.doe')
        username = _suggest_username('Jane', 'Doe')
        self.assertEqual(username, 'jane.doe1')

    def test_multiple_collisions_increment_counter(self):
        """When multiple collisions exist the counter keeps incrementing"""
        make_user('jane.doe')
        make_user('jane.doe1')
        username = _suggest_username('Jane', 'Doe')
        self.assertEqual(username, 'jane.doe2')

    def test_works_with_no_last_name(self):
        """Username can be generated from a first name alone when no last name is given"""
        username = _suggest_username('Mononym', '')
        self.assertTrue(len(username) > 0)


# ── _find_existing_user ───────────────────────────────────────────────────────

class FindExistingUserTests(TestCase):

    def test_returns_none_when_no_match(self):
        """Returns (None, '') when no user matches the given name or email"""
        user, reason = _find_existing_user('Nonexistent', 'Person', 'nobody@uwi.edu')
        self.assertIsNone(user)
        self.assertEqual(reason, '')

    def test_matches_by_email(self):
        """A user is found when their email matches, and match_reason is 'email'"""
        existing = make_user('email.match', email='matchme@uwi.edu')
        user, reason = _find_existing_user('Any', 'Name', 'matchme@uwi.edu')
        self.assertEqual(user, existing)
        self.assertEqual(reason, 'email')

    def test_email_match_takes_priority_over_name(self):
        """Email match is checked first and takes priority over name matching"""
        email_user = make_user('by.email', first_name='Robert', last_name='Jones',
                               email='priority@uwi.edu')
        name_user = make_user('by.name', first_name='Robert', last_name='Jones',
                              email='other@uwi.edu')
        user, reason = _find_existing_user('Robert', 'Jones', 'priority@uwi.edu')
        self.assertEqual(user, email_user)
        self.assertEqual(reason, 'email')

    def test_matches_by_name_when_no_email(self):
        """A user is found by first+last name when no email is provided"""
        existing = make_user('name.only', first_name='Alice', last_name='Walker')
        user, reason = _find_existing_user('Alice', 'Walker', '')
        self.assertEqual(user, existing)
        self.assertEqual(reason, 'name')

    def test_name_match_is_case_insensitive(self):
        """Name matching works regardless of letter case"""
        existing = make_user('case.test', first_name='ALICE', last_name='WALKER')
        user, reason = _find_existing_user('alice', 'walker', '')
        self.assertEqual(user, existing)

    def test_no_match_when_only_first_name_given(self):
        """Returns None when only a first name is provided (ambiguous)"""
        make_user('first.only', first_name='Alice', last_name='')
        user, reason = _find_existing_user('Alice', '', '')
        self.assertIsNone(user)
