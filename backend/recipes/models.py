from django.db import models
from users.models import User


class Tags(models.Model):
    name = models.CharField(
        verbose_name='Тег',
        max_length=32,
        unique=True,
        error_messages={
            'unique': 'Данный тег уже используется',
        },
    )
    slug = models.SlugField(
        max_length=32,
        unique=True,
        error_messages={
            'unique': 'Данный тег уже используется',
        },
        null=True,
    )

    class Meta:
        verbose_name = 'Тэг'
        verbose_name_plural = 'Тэги'

    def __str__(self):
        return self.name


class Ingredients(models.Model):
    name = models.CharField(
        verbose_name='Ингредиент',
        max_length=128,
    )
    measurement_unit = models.CharField(
        verbose_name='Единица измерения',
        max_length=64,
    )

    class Meta:
        verbose_name = 'Ингридиент'
        verbose_name_plural = 'Ингредиенты'

    def __str__(self):
        return self.name


class Recipe(models.Model):
    tags = models.ManyToManyField(
        Tags,
        verbose_name='тег',
        help_text='',
        related_name='recipe',
    )
    author = models.ForeignKey(
        User, related_name='recipe',
        on_delete=models.CASCADE,
        verbose_name='Автор',
    )
    ingredients = models.ManyToManyField(
        Ingredients,
        verbose_name='ингридиент',
        help_text='',
        related_name='recipe',
    )
    name = models.CharField(
        max_length=256,
        verbose_name='Название'
    )
    image = models.ImageField(
        verbose_name='изображение',
        upload_to='recipes/images/',
        null=True,
        default=None
    )
    text = models.TextField(
        verbose_name='Текст',
    )
    cooking_time = models.PositiveIntegerField(
        verbose_name='Время готовки',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Время создания',
    )

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
    )
    ingredient = models.ForeignKey(
        Ingredients,
        on_delete=models.CASCADE,
    )
    amount = models.PositiveIntegerField(
        verbose_name='Рецепт',
    )

    class Meta:
        verbose_name = 'Ингредиенты в рецепте'
        verbose_name_plural = 'Ингредиенты в рецепте'


class Subscription(models.Model):
    author = models.ForeignKey(
        User, related_name='subscription',
        on_delete=models.CASCADE,
    )
    user = models.ForeignKey(
        User, related_name='subscriber',
        on_delete=models.CASCADE,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'author'],
                name='unique_user_author'
            ),
        ]
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'


class Cart(models.Model):
    user = models.ForeignKey(
        User, related_name='cart',
        on_delete=models.CASCADE,
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
    )

    class Meta:
        verbose_name = 'Карзина покупок'
        verbose_name_plural = 'Карзины покупок'


class Favorite(models.Model):
    user = models.ForeignKey(
        User, related_name='favorite',
        on_delete=models.CASCADE
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE
    )

    class Meta:
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'


class Shortcut(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE
    )
    link = models.CharField(
        max_length=10,
    )

    class Meta:
        verbose_name = 'Ссылка'
        verbose_name_plural = 'Ссылки'
