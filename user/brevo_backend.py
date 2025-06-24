# from django.conf import settings
# from django.contrib.auth.tokens import default_token_generator
# from django.contrib.sites.shortcuts import get_current_site
# from django.utils.encoding import force_bytes
# from django.utils.http import urlsafe_base64_encode
# from brevo import BrevoClient

# class BrevoPasswordResetEmail:
#     def __init__(self):
#         self.client = BrevoClient(api_key=settings.BREVO_API_KEY)

#     def send_email(self, user, request):
#         current_site = get_current_site(request)
#         site_name = current_site.name
#         domain = current_site.domain
        
#         context = {
#             'email': user.email,
#             'domain': domain,
#             'site_name': site_name,
#             'uid': urlsafe_base64_encode(force_bytes(user.pk)),
#             'user': user,
#             'token': default_token_generator.make_token(user),
#             'protocol': 'https' if request.is_secure() else 'http',
#             'username': user.get_username(),
#         }
        
#         reset_link = f"{context['protocol']}://{domain}/reset-password/{context['uid']}/{context['token']}/"
        
#         email_data = {
#     'to': [{'email': user.email}],
#     'templateId': settings.BREVO_TEMPLATE_ID,
#     'params': {
#         'reset_link': reset_link,
#         'username': context['username'],
#         'email': user.email,
#         'site_name': site_name,
#         'logo_url': 'https://yourdomain.com/static/images/logo.png',
#         'contact_url': 'https://yourdomain.com/contact',
#         'privacy_url': 'https://yourdomain.com/privacy',
#     }
# }
        
#         self.client.send_transactional_template(email_data)