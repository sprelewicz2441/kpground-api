from rest_framework import serializers

from .models import Character, CharacterWallet, StoreItem


class CharacterWalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = CharacterWallet
        fields = ['character', 'coins', 'level', 'xp']


class StoreItemSerializer(serializers.ModelSerializer):
    owned = serializers.SerializerMethodField()

    class Meta:
        model = StoreItem
        fields = ['slug', 'name', 'item_type', 'description', 'cost', 'min_level', 'owned']

    def get_owned(self, obj):
        return obj.slug in self.context.get('owned_slugs', set())


class PurchaseRequestSerializer(serializers.Serializer):
    item_slug = serializers.SlugField()


class RoundSubmitSerializer(serializers.Serializer):
    character = serializers.ChoiceField(choices=Character.choices)
    result = serializers.ChoiceField(choices=[('win', 'Win'), ('loss', 'Loss')])
    coins_collected = serializers.IntegerField(min_value=0, default=0)
