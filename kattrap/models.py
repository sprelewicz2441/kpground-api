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


class StoreItem(models.Model):
    """One character's store catalog entry.

    Bought with that character's own coins (via its CharacterWallet);
    min_level gates purchase against that same character's wallet.level -
    a Cat item is never gated by Mouse or Dog progress.
    """

    character = models.CharField(max_length=10, choices=Character.choices)
    slug = models.SlugField()
    name = models.CharField(max_length=100)
    item_type = models.CharField(max_length=10, choices=ItemType.choices)
    description = models.TextField(blank=True)
    cost = models.PositiveIntegerField()
    min_level = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('character', 'slug')

    def __str__(self):
        return f'[{self.character}] {self.name} ({self.cost} coins, lvl {self.min_level}+)'


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
