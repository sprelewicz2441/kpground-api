from django.conf import settings
from django.db import models

from .economy import XP_PER_LEVEL


class Character(models.TextChoices):
    CAT = 'cat', 'Cat'
    MOUSE = 'mouse', 'Mouse'
    DOG = 'dog', 'Dog'


class CharacterWallet(models.Model):
    """Coins, level, and XP for one (user, character) pair.

    Deliberately siloed per character, not per account - a user has three
    independent wallets (Cat/Mouse/Dog), each earned only by playing that
    character. The future "aggregate" store (not built yet) just sums all
    three of a user's wallets rather than reading a fourth balance.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wallets'
    )
    character = models.CharField(max_length=10, choices=Character.choices)
    coins = models.PositiveIntegerField(default=0)
    level = models.PositiveIntegerField(default=1)
    xp = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('user', 'character')

    def __str__(self):
        return f'{self.user} / {self.character}: {self.coins} coins, lvl {self.level}'

    def add_xp(self, amount):
        """Adds XP and levels up as many times as earned this call, using
        a flat XP_PER_LEVEL-per-level threshold (see economy.py)."""
        self.xp += amount
        while self.xp >= self.level * XP_PER_LEVEL:
            self.xp -= self.level * XP_PER_LEVEL
            self.level += 1


class ItemType(models.TextChoices):
    COSMETIC = 'cosmetic', 'Cosmetic'
    PERK = 'perk', 'Perk'


class ItemSlot(models.TextChoices):
    """Which equip slot a cosmetic occupies. Only 'outfit' exists today -
    every cosmetic is a complete look, worn as a whole (see the project's
    own decision: full alternate sprite sheets per outfit now, not
    independently-purchasable pieces). Structured as a real choices field
    from day one specifically so a future move to a real per-piece
    wardrobe (hat/top/accessory, each its own slot) is just new slot
    values on new items - EquippedItem below already supports a user
    having one equipped item per slot per character, simultaneously,
    with zero schema changes needed when that day comes.
    """

    OUTFIT = 'outfit', 'Outfit'


class StoreItem(models.Model):
    """One character's store catalog entry.

    Bought with that character's own coins (via its CharacterWallet);
    min_level gates purchase against that same character's wallet.level -
    a Cat item is never gated by Mouse or Dog progress. slot only applies
    to cosmetics (blank for perks) - see ItemSlot above.
    """

    character = models.CharField(max_length=10, choices=Character.choices)
    slug = models.SlugField()
    name = models.CharField(max_length=100)
    item_type = models.CharField(max_length=10, choices=ItemType.choices)
    slot = models.CharField(max_length=20, choices=ItemSlot.choices, blank=True)
    # Frontend asset path for this look (e.g. 'assets/cat_witch.png') -
    # only meaningful for outfit-slot cosmetics. Blank/unused until real
    # outfit art exists; added now alongside slot/EquippedItem so wiring
    # up real cosmetics later needs zero further schema changes, only
    # populating this field and building the frontend swap logic.
    sprite_src = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    cost = models.PositiveIntegerField()
    min_level = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('character', 'slug')

    def __str__(self):
        return f'[{self.character}] {self.name} ({self.cost} coins, lvl {self.min_level}+)'


class EquippedItem(models.Model):
    """Tracks the currently-worn cosmetic per (user, character, slot).

    Only one row per (user, character, slot) - equipping a new item in an
    already-occupied slot replaces this row rather than adding a second
    one. No row at all means "wearing the default look" for that slot.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='equipped_items'
    )
    character = models.CharField(max_length=10, choices=Character.choices)
    slot = models.CharField(max_length=20, choices=ItemSlot.choices)
    item = models.ForeignKey(StoreItem, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user', 'character', 'slot')

    def __str__(self):
        return f'{self.user} / {self.character} [{self.slot}]: {self.item.name}'


class OwnedItem(models.Model):
    """A permanently-owned StoreItem for a user."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='owned_items'
    )
    item = models.ForeignKey(StoreItem, on_delete=models.CASCADE)
    purchased_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'item')

    def __str__(self):
        return f'{self.user} owns {self.item}'


class DailyGiftClaim(models.Model):
    """One row per day a user claims the daily gift.

    The unique constraint on (user, claimed_date) is what actually
    prevents a double claim on the same day - not application logic alone.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='daily_gift_claims'
    )
    claimed_date = models.DateField()
    coins_awarded_per_character = models.PositiveIntegerField()

    class Meta:
        unique_together = ('user', 'claimed_date')

    def __str__(self):
        return f'{self.user} claimed gift on {self.claimed_date}'
