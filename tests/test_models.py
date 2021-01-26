import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone

from oauth2_provider.models import (
    clear_expired,
    get_access_token_model,
    get_application_model,
    get_grant_model,
    get_id_token_model,
    get_refresh_token_model,
)

from . import presets


Application = get_application_model()
Grant = get_grant_model()
AccessToken = get_access_token_model()
RefreshToken = get_refresh_token_model()
UserModel = get_user_model()
IDToken = get_id_token_model()


class BaseTestModels(TestCase):
    def setUp(self):
        self.user = UserModel.objects.create_user("test_user", "test@example.com", "123456")

    def tearDown(self):
        self.user.delete()


class TestModels(BaseTestModels):
    def test_allow_scopes(self):
        self.client.login(username="test_user", password="123456")
        app = Application.objects.create(
            name="test_app",
            redirect_uris="http://localhost http://example.com http://example.org",
            user=self.user,
            client_type=Application.CLIENT_CONFIDENTIAL,
            authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
        )

        access_token = AccessToken(user=self.user, scope="read write", expires=0, token="", application=app)

        self.assertTrue(access_token.allow_scopes(["read", "write"]))
        self.assertTrue(access_token.allow_scopes(["write", "read"]))
        self.assertTrue(access_token.allow_scopes(["write", "read", "read"]))
        self.assertTrue(access_token.allow_scopes([]))
        self.assertFalse(access_token.allow_scopes(["write", "destroy"]))

    def test_grant_authorization_code_redirect_uris(self):
        app = Application(
            name="test_app",
            redirect_uris="",
            user=self.user,
            client_type=Application.CLIENT_CONFIDENTIAL,
            authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
        )

        self.assertRaises(ValidationError, app.full_clean)

    def test_grant_implicit_redirect_uris(self):
        app = Application(
            name="test_app",
            redirect_uris="",
            user=self.user,
            client_type=Application.CLIENT_CONFIDENTIAL,
            authorization_grant_type=Application.GRANT_IMPLICIT,
        )

        self.assertRaises(ValidationError, app.full_clean)

    def test_str(self):
        app = Application(
            redirect_uris="",
            user=self.user,
            client_type=Application.CLIENT_CONFIDENTIAL,
            authorization_grant_type=Application.GRANT_IMPLICIT,
        )
        self.assertEqual("%s" % app, app.client_id)

        app.name = "test_app"
        self.assertEqual("%s" % app, "test_app")

    def test_scopes_property(self):
        self.client.login(username="test_user", password="123456")

        app = Application.objects.create(
            name="test_app",
            redirect_uris="http://localhost http://example.com http://example.org",
            user=self.user,
            client_type=Application.CLIENT_CONFIDENTIAL,
            authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
        )

        access_token = AccessToken(user=self.user, scope="read write", expires=0, token="", application=app)

        access_token2 = AccessToken(user=self.user, scope="write", expires=0, token="", application=app)

        self.assertEqual(access_token.scopes, {"read": "Reading scope", "write": "Writing scope"})
        self.assertEqual(access_token2.scopes, {"write": "Writing scope"})


@override_settings(
    OAUTH2_PROVIDER_APPLICATION_MODEL="tests.SampleApplication",
    OAUTH2_PROVIDER_ACCESS_TOKEN_MODEL="tests.SampleAccessToken",
    OAUTH2_PROVIDER_REFRESH_TOKEN_MODEL="tests.SampleRefreshToken",
    OAUTH2_PROVIDER_GRANT_MODEL="tests.SampleGrant",
)
@pytest.mark.usefixtures("oauth2_settings")
class TestCustomModels(BaseTestModels):
    def test_custom_application_model(self):
        """
        If a custom application model is installed, it should be present in
        the related objects and not the swapped out one.

        See issue #90 (https://github.com/jazzband/django-oauth-toolkit/issues/90)
        """
        related_object_names = [
            f.name
            for f in UserModel._meta.get_fields()
            if (f.one_to_many or f.one_to_one) and f.auto_created and not f.concrete
        ]
        self.assertNotIn("oauth2_provider:application", related_object_names)
        self.assertIn("tests_sampleapplication", related_object_names)

    def test_custom_application_model_incorrect_format(self):
        # Patch oauth2 settings to use a custom Application model
        self.oauth2_settings.APPLICATION_MODEL = "IncorrectApplicationFormat"

        self.assertRaises(ValueError, get_application_model)

    def test_custom_application_model_not_installed(self):
        # Patch oauth2 settings to use a custom Application model
        self.oauth2_settings.APPLICATION_MODEL = "tests.ApplicationNotInstalled"

        self.assertRaises(LookupError, get_application_model)

    def test_custom_access_token_model(self):
        """
        If a custom access token model is installed, it should be present in
        the related objects and not the swapped out one.
        """
        # Django internals caches the related objects.
        related_object_names = [
            f.name
            for f in UserModel._meta.get_fields()
            if (f.one_to_many or f.one_to_one) and f.auto_created and not f.concrete
        ]
        self.assertNotIn("oauth2_provider:access_token", related_object_names)
        self.assertIn("tests_sampleaccesstoken", related_object_names)

    def test_custom_access_token_model_incorrect_format(self):
        # Patch oauth2 settings to use a custom AccessToken model
        self.oauth2_settings.ACCESS_TOKEN_MODEL = "IncorrectAccessTokenFormat"

        self.assertRaises(ValueError, get_access_token_model)

    def test_custom_access_token_model_not_installed(self):
        # Patch oauth2 settings to use a custom AccessToken model
        self.oauth2_settings.ACCESS_TOKEN_MODEL = "tests.AccessTokenNotInstalled"

        self.assertRaises(LookupError, get_access_token_model)

    def test_custom_refresh_token_model(self):
        """
        If a custom refresh token model is installed, it should be present in
        the related objects and not the swapped out one.
        """
        # Django internals caches the related objects.
        related_object_names = [
            f.name
            for f in UserModel._meta.get_fields()
            if (f.one_to_many or f.one_to_one) and f.auto_created and not f.concrete
        ]
        self.assertNotIn("oauth2_provider:refresh_token", related_object_names)
        self.assertIn("tests_samplerefreshtoken", related_object_names)

    def test_custom_refresh_token_model_incorrect_format(self):
        # Patch oauth2 settings to use a custom RefreshToken model
        self.oauth2_settings.REFRESH_TOKEN_MODEL = "IncorrectRefreshTokenFormat"

        self.assertRaises(ValueError, get_refresh_token_model)

    def test_custom_refresh_token_model_not_installed(self):
        # Patch oauth2 settings to use a custom AccessToken model
        self.oauth2_settings.REFRESH_TOKEN_MODEL = "tests.RefreshTokenNotInstalled"

        self.assertRaises(LookupError, get_refresh_token_model)

    def test_custom_grant_model(self):
        """
        If a custom grant model is installed, it should be present in
        the related objects and not the swapped out one.
        """
        # Django internals caches the related objects.
        related_object_names = [
            f.name
            for f in UserModel._meta.get_fields()
            if (f.one_to_many or f.one_to_one) and f.auto_created and not f.concrete
        ]
        self.assertNotIn("oauth2_provider:grant", related_object_names)
        self.assertIn("tests_samplegrant", related_object_names)

    def test_custom_grant_model_incorrect_format(self):
        # Patch oauth2 settings to use a custom Grant model
        self.oauth2_settings.GRANT_MODEL = "IncorrectGrantFormat"

        self.assertRaises(ValueError, get_grant_model)

    def test_custom_grant_model_not_installed(self):
        # Patch oauth2 settings to use a custom AccessToken model
        self.oauth2_settings.GRANT_MODEL = "tests.GrantNotInstalled"

        self.assertRaises(LookupError, get_grant_model)


class TestGrantModel(BaseTestModels):
    def setUp(self):
        super().setUp()
        self.application = Application.objects.create(
            name="Test Application",
            redirect_uris="",
            user=self.user,
            client_type=Application.CLIENT_CONFIDENTIAL,
            authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
        )

    def tearDown(self):
        self.application.delete()
        super().tearDown()

    def test_str(self):
        grant = Grant(code="test_code")
        self.assertEqual("%s" % grant, grant.code)

    def test_expires_can_be_none(self):
        grant = Grant(code="test_code")
        self.assertIsNone(grant.expires)
        self.assertTrue(grant.is_expired())

    def test_redirect_uri_can_be_longer_than_255_chars(self):
        long_redirect_uri = "http://example.com/{}".format("authorized/" * 25)
        self.assertTrue(len(long_redirect_uri) > 255)
        grant = Grant.objects.create(
            user=self.user,
            code="test_code",
            application=self.application,
            expires=timezone.now(),
            redirect_uri=long_redirect_uri,
            scope="",
        )
        grant.refresh_from_db()

        # It would be necessary to run test using another DB engine than sqlite
        # that transform varchar(255) into text data type.
        # https://sqlite.org/datatype3.html#affinity_name_examples
        self.assertEqual(grant.redirect_uri, long_redirect_uri)


class TestAccessTokenModel(BaseTestModels):
    def test_str(self):
        access_token = AccessToken(token="test_token")
        self.assertEqual("%s" % access_token, access_token.token)

    def test_user_can_be_none(self):
        app = Application.objects.create(
            name="test_app",
            redirect_uris="http://localhost http://example.com http://example.org",
            user=self.user,
            client_type=Application.CLIENT_CONFIDENTIAL,
            authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
        )
        access_token = AccessToken.objects.create(token="test_token", application=app, expires=timezone.now())
        self.assertIsNone(access_token.user)

    def test_expires_can_be_none(self):
        access_token = AccessToken(token="test_token")
        self.assertIsNone(access_token.expires)
        self.assertTrue(access_token.is_expired())


class TestRefreshTokenModel(BaseTestModels):
    def test_str(self):
        refresh_token = RefreshToken(token="test_token")
        self.assertEqual("%s" % refresh_token, refresh_token.token)


@pytest.mark.usefixtures("oauth2_settings")
class TestClearExpired(BaseTestModels):
    def setUp(self):
        super().setUp()
        # Insert two tokens on database.
        app = Application.objects.create(
            name="test_app",
            redirect_uris="http://localhost http://example.com http://example.org",
            user=self.user,
            client_type=Application.CLIENT_CONFIDENTIAL,
            authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
        )
        AccessToken.objects.create(
            token="555",
            expires=timezone.now(),
            scope=2,
            application=app,
            user=self.user,
            created=timezone.now(),
            updated=timezone.now(),
        )
        AccessToken.objects.create(
            token="666",
            expires=timezone.now(),
            scope=2,
            application=app,
            user=self.user,
            created=timezone.now(),
            updated=timezone.now(),
        )

    def test_clear_expired_tokens(self):
        self.oauth2_settings.REFRESH_TOKEN_EXPIRE_SECONDS = 60
        assert clear_expired() is None

    def test_clear_expired_tokens_incorect_timetype(self):
        self.oauth2_settings.REFRESH_TOKEN_EXPIRE_SECONDS = "A"
        with pytest.raises(ImproperlyConfigured) as excinfo:
            clear_expired()
        result = excinfo.value.__class__.__name__
        assert result == "ImproperlyConfigured"

    def test_clear_expired_tokens_with_tokens(self):
        self.client.login(username="test_user", password="123456")
        self.oauth2_settings.REFRESH_TOKEN_EXPIRE_SECONDS = 0
        ttokens = AccessToken.objects.count()
        expiredt = AccessToken.objects.filter(expires__lte=timezone.now()).count()
        assert ttokens == 2
        assert expiredt == 2
        clear_expired()
        expiredt = AccessToken.objects.filter(expires__lte=timezone.now()).count()
        assert expiredt == 0


@pytest.mark.django_db
@pytest.mark.oauth2_settings(presets.OIDC_SETTINGS_RW)
def test_id_token_methods(oidc_tokens):
    id_token = IDToken.objects.get(token=oidc_tokens.id_token)

    # Token was just created, so should be valid
    assert id_token.is_valid()

    # if expires is None, it should always be expired
    # the column is NOT NULL, but could be NULL in sub-classes
    id_token.expires = None
    assert id_token.is_expired()

    # if no scopes are passed, they should be valid
    assert id_token.allow_scopes(None)

    # if the requested scopes are in the token, they should be valid
    assert id_token.allow_scopes(["openid"])

    # if the requested scopes are not in the token, they should not be valid
    assert id_token.allow_scopes(["fizzbuzz"]) is False

    # we should be able to get a list of the scopes on the token
    assert id_token.scopes == {"openid": "OpenID connect"}

    # we should be able to extract the claims on the token
    # we only are checking the repeatable subset of claims..
    assert id_token.claims
    assert id_token.claims["sub"] == str(oidc_tokens.user.pk)
    assert id_token.claims["aud"] == oidc_tokens.application.client_id
    assert id_token.claims["iss"] == oidc_tokens.oauth2_settings.OIDC_ISS_ENDPOINT

    # the id token should stringify as the JWT token
    assert str(id_token) == oidc_tokens.id_token

    # revoking the token should delete it
    id_token.revoke()
    assert IDToken.objects.filter(token=oidc_tokens.id_token).count() == 0
