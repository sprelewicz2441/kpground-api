"""Tunable KatTrap economy numbers.

Plain module constants, not DB-configurable, until there's an actual need
to retune these without a deploy. Phase 1 (current): flat coins/XP per
round outcome. A performance-scaled bonus (time survived, close-call
escapes, etc.) is planned as an addition on top of this later, not a
replacement for it.
"""

# Coins awarded to the played character's wallet at round end.
# Loss amount is deliberately very minimal (but non-zero) - losing should
# still feel like progress, not a dead end, especially for a young player.
WIN_COINS = 20
LOSS_COINS = 2

# XP awarded to the played character's wallet at round end, same shape as
# coins above.
WIN_XP = 20
LOSS_XP = 5

# Flat amount credited to EACH of the three character wallets (not
# summed/split) on a single daily-gift claim.
DAILY_GIFT_COINS_PER_CHARACTER = 10

# XP required to advance from level N to N+1 is XP_PER_LEVEL * N (a linear
# curve - simplest starting point, revisit once real play data exists).
XP_PER_LEVEL = 50
