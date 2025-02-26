from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.utils import perform_login
from allauth.exceptions import ImmediateHttpResponse
from django.shortcuts import redirect
from django.contrib.auth import get_user_model

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        """
        Invoked just after a user successfully authenticates via a
        social provider, but before the login is actually processed
        and the user is logged in.
        """
        # Check if the email associated with the social login exists
        email_address = sociallogin.account.extra_data['email']
        User = get_user_model()

        try:
            user = User.objects.get(email=email_address)
            if not user.has_usable_password():
                # If the user has no password set, set a dummy password
                user.set_password(User.objects.make_random_password())
                user.save()
            perform_login(request, user, email_verification=sociallogin.email_addresses[0].verified)
            raise ImmediateHttpResponse(redirect('account_inactive'))
        except User.DoesNotExist:
            pass
