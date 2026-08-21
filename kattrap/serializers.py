from rest_framework import serializers

from .economy import XP_PER_LEVEL
from .models import Character, CharacterWallet, StoreItem


class CharacterWalletSerializer(serializers.ModelSerializer):
    # Computed rather than duplicating the XP_PER_LEVEL curve client-side -
    # CharacterWallet.add_xp() already leaves .xp as progress *within* the
    # current level, so xp / xp_to_next_level is directly a 0-1 fraction a
    # frontend progress bar can use with no further math.
    xp_to_next_level = serializers.SerializerMethodField()

    class Meta:
        model = CharacterWallet
        fields = ['character', 'coins', 'level', 'xp', 'xp_to_next_level']

    def get_xp_to_next_level(self, obj):
        return obj.level * XP_PER_LEVEL


class StoreItemSerializer(serializers.ModelSerializer):
    owned = serializers.SerializerMethodField()
    equipped = serializers.SerializerMethodField()

    class Meta:
        model = StoreItem
        fields = [
            'slug',
            'name',
            'item_type',
            'slot',
            'sprite_src',
            'description',
            'cost',
            'min_level',
            'owned',
            'equipped',
        ]

    def get_owned(self, obj):
        return obj.slug in self.context.get('owned_slugs', set())

    def get_equipped(self, obj):
        return obj.slug in self.context.get('equipped_slugs', set())


class ItemSlugRequestSerializer(serializers.Serializer):
    """Shape shared by every action that just names one store item -
    purchase and equip both take exactly this."""

    item_slug = serializers.SlugField()


class RoundSubmitSerializer(serializers.Serializer):
    character = serializers.ChoiceField(choices=Character.choices)
    result = serializers.ChoiceField(choices=[('win', 'Win'), ('loss', 'Loss')])
    coins_collected = serializers.IntegerField(min_value=0, default=0)
