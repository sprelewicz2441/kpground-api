from django.core.management.base import BaseCommand

from kattrap.models import ItemType, StoreItem

# PLACEHOLDER catalog for exercising the purchase flow end to end - not
# final game content. Real names/costs/cosmetics still need to be
# designed; one perk (matching the confirmed perk list) and one cosmetic
# per character, kept intentionally simple.
PLACEHOLDER_ITEMS = [
    {
        'character': 'cat',
        'slug': 'punch-knockback',
        'name': 'Bigger Punch Knockback',
        'item_type': ItemType.PERK,
        'description': "Cat mode's punch shoves the dog further away.",
        'cost': 40,
        'min_level': 2,
    },
    {
        'character': 'mouse',
        'slug': 'hole-radar',
        'name': 'Mouse Hole Radar',
        'item_type': ItemType.PERK,
        'description': 'Highlights the nearest escape hole on screen.',
        'cost': 35,
        'min_level': 2,
    },
    {
        'character': 'dog',
        'slug': 'longer-pause',
        'name': 'Longer Cat Pause',
        'item_type': ItemType.PERK,
        'description': 'The cat stays stunned longer after a collision.',
        'cost': 40,
        'min_level': 2,
    },
]


class Command(BaseCommand):
    help = 'Seeds a small PLACEHOLDER store catalog for testing. Safe to re-run.'

    def handle(self, *args, **options):
        for data in PLACEHOLDER_ITEMS:
            item, created = StoreItem.objects.update_or_create(
                character=data['character'], slug=data['slug'], defaults=data
            )
            self.stdout.write(f"{'Created' if created else 'Updated'}: {item}")
