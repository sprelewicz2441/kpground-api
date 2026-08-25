from django.core.management.base import BaseCommand

from kattrap.models import ItemSlot, ItemType, StoreItem

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

# Dog outfit-slot cosmetics - a reference image (5 tutu colors) locked in
# which 5 looks to ship, but that image was a single repeated pose with a
# colored background baked in per column, not game-ready art (no real
# walk-cycle, no clean transparent background) - see the sibling kat_trap
# repo's CLAUDE.md, Currency & economy system section, for that decision.
# sprite_src points at the *default* dog_v2.png for every one of these
# (matching js/utils/outfits.js's own DEFAULT_SPRITE_SRC exactly) - purely
# a placeholder so the purchase/equip plumbing has real rows to exercise;
# equipping one today has zero visual effect. is_active=False keeps them
# out of the live store until real per-color art replaces this sprite_src
# - flip to True (or just re-run this command after updating sprite_src)
# once that art exists, no other code changes needed anywhere.
DOG_OUTFIT_ITEMS = [
    {
        'character': 'dog',
        'slug': f'tutu-{color}',
        'name': f'{color.capitalize()} Tutu',
        'item_type': ItemType.COSMETIC,
        'slot': ItemSlot.OUTFIT,
        'sprite_src': './assets/dog_v2.png?v=4',
        'description': f'A sparkly {color} tutu for Dummy.',
        'cost': 50,
        'min_level': 1,
        'is_active': False,
    }
    for color in ['purple', 'pink', 'teal', 'orange', 'green']
]


class Command(BaseCommand):
    help = 'Seeds a small PLACEHOLDER store catalog for testing. Safe to re-run.'

    def handle(self, *args, **options):
        for data in PLACEHOLDER_ITEMS + DOG_OUTFIT_ITEMS:
            item, created = StoreItem.objects.update_or_create(
                character=data['character'], slug=data['slug'], defaults=data
            )
            self.stdout.write(f"{'Created' if created else 'Updated'}: {item}")
