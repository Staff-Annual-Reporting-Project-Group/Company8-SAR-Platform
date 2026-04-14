"""
Unit tests — UserProfilePic model.

No HTTP client is used here.  Each test exercises model-level behaviour
directly: field defaults, properties, signals, and __str__ output.

Run with:
    python manage.py test users.tests.unit --testrunner=test_runner.SARTestRunner
"""

from django.test import TestCase
from django.contrib.auth.models import User
from users.models import UserProfilePic


def make_user(username='testuser', password='SecurePass123!', email='test@uwi.edu'):
    return User.objects.create_user(username=username, password=password, email=email)


# ── constants ─────────────────────────────────────────────────────────────────

class UserProfilePicDefaultsTests(TestCase):

    def test_default_pic_constant_is_full_url(self):
        """DEFAULT_PIC constant is a full Cloudinary https:// URL"""
        self.assertTrue(UserProfilePic.DEFAULT_PIC.startswith('https://'))

    def test_robot_pic_id_references_robot_image(self):
        """ROBOT_PIC_ID constant contains 'ai_robot' identifier"""
        self.assertIn('ai_robot', UserProfilePic.ROBOT_PIC_ID)

    def test_new_profile_receives_default_pic(self):
        """A newly created profile is assigned the default avatar URL"""
        user = make_user()
        profile = UserProfilePic.objects.get(user=user)
        self.assertEqual(str(profile.profilePic), UserProfilePic.DEFAULT_PIC)


# ── __str__ ───────────────────────────────────────────────────────────────────

class UserProfilePicStrTests(TestCase):

    def test_str_returns_username_profile(self):
        """__str__ returns '<username> Profile' format"""
        user = make_user(username='jane.doe')
        profile = UserProfilePic.objects.get(user=user)
        self.assertEqual(str(profile), 'jane.doe Profile')


# ── pic_url property ──────────────────────────────────────────────────────────

class PicUrlPropertyTests(TestCase):

    def setUp(self):
        self.user = make_user()
        self.profile = UserProfilePic.objects.get(user=self.user)

    def test_full_https_url_is_returned_unchanged(self):
        """pic_url returns a stored https:// URL directly without modification"""
        full_url = 'https://res.cloudinary.com/demo/image/upload/sample.jpg'
        self.profile.profilePic = full_url
        self.profile.save()
        self.assertEqual(self.profile.pic_url, full_url)

    def test_full_url_is_not_double_wrapped(self):
        """pic_url does not pass a full URL through .url (would produce a broken double-URL)"""
        full_url = 'https://res.cloudinary.com/demo/image/upload/sample.jpg'
        self.profile.profilePic = full_url
        self.profile.save()
        self.assertFalse(self.profile.pic_url.count('https://') > 1)

    def test_empty_stored_value_returns_empty_string(self):
        """pic_url returns an empty string when no image is stored"""
        self.profile.profilePic = ''
        self.profile.save(update_fields=['profilePic'])
        self.assertEqual(self.profile.pic_url, '')

    def test_default_pic_url_is_usable(self):
        """pic_url works correctly when the field holds the DEFAULT_PIC URL"""
        self.profile.profilePic = UserProfilePic.DEFAULT_PIC
        self.profile.save()
        self.assertEqual(self.profile.pic_url, UserProfilePic.DEFAULT_PIC)


# ── signal ────────────────────────────────────────────────────────────────────

class UserProfilePicSignalTests(TestCase):

    def test_profile_is_created_automatically_on_user_creation(self):
        """A UserProfilePic row is auto-created by signal when a User is saved"""
        user = make_user(username='signaltest')
        self.assertTrue(UserProfilePic.objects.filter(user=user).exists())

    def test_saving_user_again_does_not_create_duplicate_profile(self):
        """Re-saving a User does not create a second UserProfilePic row"""
        user = make_user(username='oneprofile')
        user.first_name = 'Updated'
        user.save()
        self.assertEqual(UserProfilePic.objects.filter(user=user).count(), 1)
