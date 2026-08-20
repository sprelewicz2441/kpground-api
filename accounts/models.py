from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Shared identity across kpground and every game (kattrap, future games).

    Kept as a thin AbstractUser subclass with no extra fields for now -
    swapped in from day one anyway, since replacing Django's default user
    model after real data exists is a much bigger migration than starting
    with a custom one, even an empty one.
    """
