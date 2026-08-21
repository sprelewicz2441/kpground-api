from django.contrib import admin

from .models import CharacterWallet, DailyGiftClaim, EquippedItem, OwnedItem, StoreItem


@admin.register(CharacterWallet)
class CharacterWalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'character', 'coins', 'level', 'xp')
    list_filter = ('character',)
    search_fields = ('user__username',)


@admin.register(StoreItem)
class StoreItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'character', 'item_type', 'slot', 'cost', 'min_level', 'is_active')
    list_filter = ('character', 'item_type', 'is_active')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(OwnedItem)
class OwnedItemAdmin(admin.ModelAdmin):
    list_display = ('user', 'item', 'purchased_at')
    search_fields = ('user__username',)


@admin.register(EquippedItem)
class EquippedItemAdmin(admin.ModelAdmin):
    list_display = ('user', 'character', 'slot', 'item')
    list_filter = ('character', 'slot')
    search_fields = ('user__username',)


@admin.register(DailyGiftClaim)
class DailyGiftClaimAdmin(admin.ModelAdmin):
    list_display = ('user', 'claimed_date', 'coins_awarded_per_character')
    search_fields = ('user__username',)
