from django.core.validators import MinValueValidator
from django.db import models

from users.models import User


class Tag(models.Model):
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


class Ingredient(models.Model):
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
        return f'{self.name} ({self.measurement_unit})'


class Recipe(models.Model):
    tags = models.ManyToManyField(
        Tag,
        verbose_name='тег',
        related_name='recipes',
    )
    author = models.ForeignKey(
        User, related_name='recipes',
        on_delete=models.CASCADE,
        verbose_name='Автор',
    )
    ingredients = models.ManyToManyField(
        Ingredient,
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
        default=''
    )
    text = models.TextField(
        verbose_name='Текст',
    )
    cooking_time = models.PositiveSmallIntegerField(
        verbose_name='Время готовки',
        validators=[MinValueValidator(1)],
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Время создания',
    )
    link = models.CharField(
        max_length=10,
        default='',
        verbose_name='Ссылка',
    )

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} - {self.author.username}'


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт',
        related_name='recipe_ingredients'
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        verbose_name='Ингредиент',
        related_name='recipe_ingredients'
    )
    amount = models.PositiveSmallIntegerField(
        verbose_name='Количество',
        validators=[MinValueValidator(1)],
    )

    class Meta:
        verbose_name = 'Ингредиенты в рецепте'
        verbose_name_plural = 'Ингредиенты в рецепте'

    def __str__(self):
        return (
            f'{self.recipe.name} - '
            f'{self.ingredient.name} '
            f'{self.amount} '
            f'{self.ingredient.measurement_unit}'
        )


class Subscription(models.Model):
    author = models.ForeignKey(
        User, related_name='subscriptions',
        on_delete=models.CASCADE,
        verbose_name='автор',
    )
    user = models.ForeignKey(
        User, related_name='subscribers',
        on_delete=models.CASCADE,
        verbose_name='подписчик',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'author'],
                name='unique_user_author'
            ),
        ]
        ordering = ['-id']
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'

    def __str__(self):
        return f'{self.user.username} подписан на {self.author.username}'


class Cart(models.Model):
    user = models.ForeignKey(
        User, related_name='carts',
        on_delete=models.CASCADE,
        verbose_name='пользователь',
    )
    recipe = models.ForeignKey(
        Recipe, related_name='carts',
        on_delete=models.CASCADE,
        verbose_name='рецепт',
    )

    class Meta:
        verbose_name = 'Карзина покупок'
        verbose_name_plural = 'Карзины покупок'

    def __str__(self):
        return f'{self.user.username} - {self.recipe.name}'


class Favorite(models.Model):
    user = models.ForeignKey(
        User, related_name='favorites',
        on_delete=models.CASCADE,
        verbose_name='пользователь',
    )
    recipe = models.ForeignKey(
        Recipe, related_name='favorites',
        on_delete=models.CASCADE,
        verbose_name='рецепт',
    )

    class Meta:
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'

    def __str__(self):
        return f'{self.user.username} - {self.recipe.name}'
