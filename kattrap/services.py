from django.db import transaction
from django.utils import timezone

from .economy import DAILY_GIFT_COINS_PER_CHARACTER, LOSS_COINS, LOSS_XP, WIN_COINS, WIN_XP
from .models import Character, CharacterWallet, DailyGiftClaim, OwnedItem, StoreItem

# In-play coin pickups are tallied client-side during a round and
# submitted once at round end (see submit_round) rather than one network
# call per pickup. This caps what a single submission can credit so a
# malformed/tampered client can't hand itself an arbitrary balance - not
# a full anti-cheat system, just a sane ceiling.
MAX_COINS_COLLECTED_PER_ROUND = 50


class PurchaseError(Exception):
    """Raised for any purchase-rejection reason; message is user-facing."""


def get_or_create_wallets(user):
    """Ensures a wallet exists for all three characters, returns them
    keyed by character. Called lazily rather than requiring every new
    account to be seeded up front - only Kathryn's account is pre-seeded."""
    wallets = {w.character: w for w in CharacterWallet.objects.filter(user=user)}
    for character in Character.values:
        if character not in wallets:
            wallets[character] = CharacterWallet.objects.create(user=user, character=character)
    return wallets


def ordered_wallets(wallets_by_character):
    return [wallets_by_character[c] for c in Character.values]


@transaction.atomic
def submit_round(user, character, result, coins_collected):
    coins_collected = min(coins_collected, MAX_COINS_COLLECTED_PER_ROUND)
    wallet, _ = CharacterWallet.objects.select_for_update().get_or_create(
        user=user, character=character
    )
    base_coins = WIN_COINS if result == 'win' else LOSS_COINS
    base_xp = WIN_XP if result == 'win' else LOSS_XP
    wallet.coins += base_coins + coins_collected
    wallet.add_xp(base_xp)
    wallet.save()
    return wallet


def has_claimed_daily_gift_today(user):
    return DailyGiftClaim.objects.filter(user=user, claimed_date=timezone.localdate()).exists()


@transaction.atomic
def claim_daily_gift(user):
    """Returns the per-character amount credited, or None if today's gift
    was already claimed. The DailyGiftClaim unique_together(user,
    claimed_date) constraint is the real guard against a double claim -
    get_or_create here just surfaces that as a clean "already claimed"
    result instead of an IntegrityError."""
    claim, created = DailyGiftClaim.objects.get_or_create(
        user=user,
        claimed_date=timezone.localdate(),
        defaults={'coins_awarded_per_character': DAILY_GIFT_COINS_PER_CHARACTER},
    )
    if not created:
        return None

    wallets = get_or_create_wallets(user)
    for wallet in wallets.values():
        locked = CharacterWallet.objects.select_for_update().get(pk=wallet.pk)
        locked.coins += DAILY_GIFT_COINS_PER_CHARACTER
        locked.save()

    return DAILY_GIFT_COINS_PER_CHARACTER


@transaction.atomic
def purchase_item(user, character, item_slug):
    try:
        item = StoreItem.objects.get(character=character, slug=item_slug, is_active=True)
    except StoreItem.DoesNotExist:
        raise PurchaseError('That item does not exist.')

    wallet, _ = CharacterWallet.objects.select_for_update().get_or_create(
        user=user, character=character
    )

    if OwnedItem.objects.filter(user=user, item=item).exists():
        raise PurchaseError('You already own this item.')
    if wallet.level < item.min_level:
        raise PurchaseError(f'Requires level {item.min_level}.')
    if wallet.coins < item.cost:
        raise PurchaseError('Not enough coins.')

    wallet.coins -= item.cost
    wallet.save()
    OwnedItem.objects.create(user=user, item=item)
    return wallet
