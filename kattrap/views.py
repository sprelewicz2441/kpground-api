from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Character, ItemSlot, OwnedItem, StoreItem
from .serializers import (
    CharacterWalletSerializer,
    ItemSlugRequestSerializer,
    RoundSubmitSerializer,
    StoreItemSerializer,
)
from .services import (
    EquipError,
    PurchaseError,
    claim_daily_gift,
    equip_item,
    get_equipped,
    get_or_create_wallets,
    has_claimed_daily_gift_today,
    ordered_wallets,
    purchase_item,
    submit_round,
    unequip_slot,
)


def _equipped_response(equipped_by_slot):
    # Every item here is, by definition, both owned (equipping requires
    # ownership - see equip_item()) and equipped - pass that as context so
    # StoreItemSerializer's owned/equipped fields reflect reality instead
    # of defaulting to False from missing context.
    slugs = {item.slug for item in equipped_by_slot.values()}
    context = {'owned_slugs': slugs, 'equipped_slugs': slugs}
    return Response(
        {
            slot: StoreItemSerializer(item, context=context).data
            for slot, item in equipped_by_slot.items()
        }
    )


class WalletsView(APIView):
    """All three of the current user's wallets - lazily creates any that
    don't exist yet (e.g. a brand-new non-Kathryn account) rather than
    requiring every user to be seeded up front."""

    def get(self, request):
        wallets = ordered_wallets(get_or_create_wallets(request.user))
        return Response(CharacterWalletSerializer(wallets, many=True).data)


class StoreView(APIView):
    def get(self, request, character):
        if character not in Character.values:
            return Response({'detail': 'Unknown character.'}, status=404)
        items = StoreItem.objects.filter(character=character, is_active=True)
        owned_slugs = set(
            OwnedItem.objects.filter(user=request.user, item__character=character).values_list(
                'item__slug', flat=True
            )
        )
        equipped_slugs = {item.slug for item in get_equipped(request.user, character).values()}
        serializer = StoreItemSerializer(
            items, many=True, context={'owned_slugs': owned_slugs, 'equipped_slugs': equipped_slugs}
        )
        return Response(serializer.data)


class PurchaseView(APIView):
    def post(self, request, character):
        if character not in Character.values:
            return Response({'detail': 'Unknown character.'}, status=404)
        serializer = ItemSlugRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            wallet = purchase_item(
                request.user, character, serializer.validated_data['item_slug']
            )
        except PurchaseError as exc:
            return Response({'detail': str(exc)}, status=400)
        return Response(CharacterWalletSerializer(wallet).data)


class EquippedView(APIView):
    def get(self, request, character):
        if character not in Character.values:
            return Response({'detail': 'Unknown character.'}, status=404)
        return _equipped_response(get_equipped(request.user, character))


class EquipItemView(APIView):
    def post(self, request, character):
        if character not in Character.values:
            return Response({'detail': 'Unknown character.'}, status=404)
        serializer = ItemSlugRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            equipped = equip_item(request.user, character, serializer.validated_data['item_slug'])
        except EquipError as exc:
            return Response({'detail': str(exc)}, status=400)
        return _equipped_response(equipped)


class UnequipView(APIView):
    def post(self, request, character):
        if character not in Character.values:
            return Response({'detail': 'Unknown character.'}, status=404)
        slot = request.data.get('slot', ItemSlot.OUTFIT)
        return _equipped_response(unequip_slot(request.user, character, slot))


class DailyGiftStatusView(APIView):
    def get(self, request):
        return Response({'claimed_today': has_claimed_daily_gift_today(request.user)})


class DailyGiftClaimView(APIView):
    def post(self, request):
        amount = claim_daily_gift(request.user)
        if amount is None:
            return Response({'detail': 'Daily gift already claimed today.'}, status=400)
        wallets = ordered_wallets(get_or_create_wallets(request.user))
        return Response(
            {
                'coins_awarded_per_character': amount,
                'wallets': CharacterWalletSerializer(wallets, many=True).data,
            }
        )


class RoundSubmitView(APIView):
    def post(self, request):
        serializer = RoundSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        wallet = submit_round(
            request.user,
            serializer.validated_data['character'],
            serializer.validated_data['result'],
            serializer.validated_data['coins_collected'],
        )
        return Response(CharacterWalletSerializer(wallet).data)
