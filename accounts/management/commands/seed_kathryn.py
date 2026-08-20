from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from oauth2_provider.models import Application

from accounts.constants import KATHRYN_USERNAME, KATTRAP_CLIENT_ID
from kattrap.models import Character, CharacterWallet

User = get_user_model()


class Command(BaseCommand):
    help = (
        "Seeds the KatTrap OAuth2 application (public client, password "
        "grant) plus Kathryn's account and her three character wallets. "
        "Safe to re-run."
    )

    def handle(self, *args, **options):
        application, created = Application.objects.update_or_create(
            client_id=KATTRAP_CLIENT_ID,
            defaults={
                'name': 'KatTrap',
                'client_type': Application.CLIENT_PUBLIC,
                'authorization_grant_type': Application.GRANT_PASSWORD,
            },
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"{'Created' if created else 'Found'} OAuth application "
                f"'{application.name}' (client_id={application.client_id})"
            )
        )

        user, created = User.objects.get_or_create(username=KATHRYN_USERNAME)
        if created:
            # No password path exists for this account - it only ever
            # authenticates via the quick-login endpoint.
            user.set_unusable_password()
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Created user '{KATHRYN_USERNAME}'"))
        else:
            self.stdout.write(f"Found existing user '{KATHRYN_USERNAME}'")

        for character in Character.values:
            _, created = CharacterWallet.objects.get_or_create(user=user, character=character)
            if created:
                self.stdout.write(f'  + wallet created: {character}')
