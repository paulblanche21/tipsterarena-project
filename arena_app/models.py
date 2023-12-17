# models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.db.models import Avg
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin, Group, Permission
from django.utils import timezone


# USERS


class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=50, unique=True)
    price_monthly = models.DecimalField(max_digits=6, decimal_places=2)
    price_yearly = models.DecimalField(max_digits=6, decimal_places=2)

    def __str__(self):
        return self.name


class UserProfileManager(BaseUserManager):
    def create_user(self, email, username,
                    name, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, username=username,
                          name=name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, name,
                         password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, username, name,
                                password, **extra_fields)


class UserProfile(AbstractBaseUser, PermissionsMixin):
    name = models.CharField(max_length=255)
    username = models.CharField(max_length=30, unique=True)
    email = models.EmailField(unique=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    # Add additional fields for the user profile
    subscription_status = models.BooleanField(default=False)
    subscription_type = models.CharField(max_length=10, blank=True, null=True)
    subscription_plan = models.ForeignKey(SubscriptionPlan,
                                          on_delete=models.SET_NULL, null=True,
                                          blank=True)

    # Additional fields for the points system
    points_balance = models.IntegerField(default=1000)
    last_points_reset = models.DateField(auto_now_add=False,
                                         default=timezone.now)

    # New fields for tipster stats
    total_bets_placed = models.IntegerField(default=0)
    total_wins = models.IntegerField(default=0)

    # Properties to calculate win rate and average odds
    @property
    def win_rate(self):
        if self.total_bets_placed > 0:
            return (self.total_wins / self.total_bets_placed) * 100
        return 0

    @property
    def average_odds(self):
        return self.tip_set.aggregate(Avg('odds'))['odds__avg'] or 0
    
    # Update the points balance (can be called monthly or as needed)
    def reset_points(self):
        self.points_balance = 1000
        self.last_points_reset = timezone.now().date()
        self.save()

    groups = models.ManyToManyField(
        Group,
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.',
        related_name='user_profiles',
        related_query_name='user_profile',
    )

    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='user_profiles',
        related_query_name='user_profile',
    )

    objects = UserProfileManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'name']

    def __str__(self):
        return self.username

# SPORTS


class Sport(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name
    # Add any additional fields for sports (e.g., image, description, etc.)


class Team(models.Model):
    name = models.CharField(max_length=255, unique=True)
    sport = models.ForeignKey(Sport, on_delete=models.CASCADE)

    def __str__(self):
        return self.name
    # Add any additional fields for teams (e.g., logo, description, etc.)


class Fixture(models.Model):
    sport = models.ForeignKey(Sport, on_delete=models.CASCADE)
    team_home = models.ForeignKey(Team, on_delete=models.CASCADE,
                                  related_name='home_fixtures')
    team_away = models.ForeignKey(Team, on_delete=models.CASCADE,
                                  related_name='away_fixtures')
    date_time = models.DateTimeField()

    def __str__(self):
        return self.sport
    # Add any additional fields for fixtures (e.g., venue, status, etc.)


class Tip(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    sport = models.ForeignKey(Sport, on_delete=models.SET_NULL, null=True, blank=True)  # Link to Sport
    bet_type = models.CharField(max_length=100, null=True, blank=True)  # e.g., Match Odds, Correct Score
    odds = models.DecimalField(max_digits=6, decimal_places=2, null=True)
    points_bet = models.IntegerField(default=0) # Points wagered
    is_win = models.BooleanField(null=True, blank=True)  # True if win, False if loss, null if undecided
    created_at = models.DateTimeField(auto_now_add=True)
    additional_info = models.JSONField(blank=True, null=True)  # For storing dynamic bet details

    def __str__(self):
        user_username = self.user.username if self.user else 'Unknown User'
        sport_name = self.sport.name if self.sport else 'Unknown Sport'
        return f"{user_username} - {sport_name}"


class Follower(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='following')
    follower = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='followers')


class ChatMessage(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class Subscription(models.Model):
    SUBSCRIPTION_CHOICES = [
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]

    user = models.OneToOneField(get_user_model(), on_delete=models.CASCADE)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()  # Set when the subscription is activated
    status = models.BooleanField(default=True)  # True for active, False for inactive
    subscription_type = models.CharField(max_length=10, choices=SUBSCRIPTION_CHOICES)


class Result(models.Model):
    fixture = models.OneToOneField(Fixture, on_delete=models.CASCADE)
    team_home_score = models.PositiveIntegerField()
    team_away_score = models.PositiveIntegerField()

    def __str__(self):
        return self.fixture
    # Add any additional fields for results


class LiveScore(models.Model):
    fixture = models.OneToOneField(Fixture, on_delete=models.CASCADE)
    team_home_score = models.PositiveIntegerField()
    team_away_score = models.PositiveIntegerField()
    status = models.CharField(max_length=255)  # Ongoing, Finished, etc.

    def __str__(self):
        return self.fixture
    # Add any additional fields for live scores


class SportsOdds(models.Model):
    fixture = models.OneToOneField(Fixture, on_delete=models.CASCADE)
    team_home_odds = models.FloatField()
    team_away_odds = models.FloatField()
    draw_odds = models.FloatField()

    def __str__(self):
        return self.fixture
    # Add any additional fields for odds
