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

# Dog outfit-slot cosmetics - real per-color walk-cycle art now exists for
# 4 of the original 5 planned colors (pink/teal/orange/green), extracted
# from a single combined ChatGPT generation (see the sibling kat_trap
# repo's CLAUDE.md, Currency & economy system section, for the full
# extraction story - first via a screenshot/chroma-key pipeline that
# shipped visibly blurry sprites, later replaced with a lossless direct
# PNG download once a real per-file macOS sandbox ACL blocking that
# download was worked around). Purple came back with the same frozen-pose
# defect seen in earlier single-color attempts and was dropped from that
# generation entirely - it stays a placeholder (still pointing at the
# default dog_v2.png, is_active=False) until it's regenerated on its own.
DOG_OUTFIT_ITEMS = [
    {
        'character': 'dog',
        'slug': 'tutu-purple',
        'name': 'Purple Tutu',
        'item_type': ItemType.COSMETIC,
        'slot': ItemSlot.OUTFIT,
        'sprite_src': './assets/dog_v2.png?v=4',
        'description': 'A sparkly purple tutu for Dummy.',
        'cost': 50,
        'min_level': 1,
        'is_active': False,
    },
] + [
    {
        'character': 'dog',
        'slug': f'tutu-{color}',
        'name': f'{color.capitalize()} Tutu',
        'item_type': ItemType.COSMETIC,
        'slot': ItemSlot.OUTFIT,
        'sprite_src': f'./assets/dog_v2_tutu_{color}.png?v=3',
        'description': f'A sparkly {color} tutu for Dummy.',
        'cost': 50,
        'min_level': 1,
        'is_active': True,
    }
    for color in ['pink', 'teal', 'orange', 'green']
]

# Cat outfit-slot cosmetics - same recolor approach as the dog's tutu set,
# extracted from a combined ChatGPT generation (see the sibling kat_trap
# repo's CLAUDE.md, Currency & economy system section). Cat's *default*
# look (cat_v2.png) already wears a pink tutu, so pink isn't sold here -
# these are the 4 non-default colors, matching the dog's own "skip the
# color the default already has" pattern. This generation also came back
# with only 5 real poses per color instead of the requested 6 - same
# shortfall as the dog's - so the sprite sheet's 6th frame duplicates the
# 5th rather than being a genuinely new pose (see Cat.js).
CAT_OUTFIT_ITEMS = [
    {
        'character': 'cat',
        'slug': f'tutu-{color}',
        'name': f'{color.capitalize()} Tutu',
        'item_type': ItemType.COSMETIC,
        'slot': ItemSlot.OUTFIT,
        'sprite_src': f'./assets/cat_v2_tutu_{color}.png?v=1',
        'description': f'A sparkly {color} tutu for Mia.',
        'cost': 50,
        'min_level': 1,
        'is_active': True,
    }
    for color in ['teal', 'orange', 'green', 'purple']
]


class Command(BaseCommand):
    help = 'Seeds a small PLACEHOLDER store catalog for testing. Safe to re-run.'

    def handle(self, *args, **options):
        for data in PLACEHOLDER_ITEMS + DOG_OUTFIT_ITEMS + CAT_OUTFIT_ITEMS:
            item, created = StoreItem.objects.update_or_create(
                character=data['character'], slug=data['slug'], defaults=data
            )
            self.stdout.write(f"{'Created' if created else 'Updated'}: {item}")
