import base64

from django.core.files.base import ContentFile
from recipes.models import (Cart, Favorite, Ingredient, Recipe,
                            RecipeIngredient, Subscription, Tag)
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from users.models import User
from .validators import username_validator


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]

            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)

        return super().to_internal_value(data)


class UserCreateSerializer(serializers.ModelSerializer):
    username = serializers.CharField(
        max_length=150,
        validators=(
            username_validator,
            UniqueValidator(queryset=User.objects.all()),
        )
    )

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'password',
        )
        extra_kwargs = {
            'password': {'write_only': True},
        }

    def create(self, validated_data):
        user = User(**validated_data)
        user.set_password(validated_data['password'])
        user.save()
        return user


class UserSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField(required=False, allow_null=True)
    is_subscribed = serializers.SerializerMethodField()
    username = serializers.CharField(
        validators=(username_validator,)
    )

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'avatar',
            'is_subscribed',
        )

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        current_user = request.user if request else None
        return (
            current_user.is_authenticated
            and Subscription.objects.filter(
                author=obj, user=current_user
            ).exists()
        )


class TagSerializer(serializers.ModelSerializer):

    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class IngredientSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class RecipeIngredientSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='ingredient.id')
    name = serializers.CharField(source='ingredient.name')
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class IngredientAmountSerializer(serializers.Serializer):
    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    amount = serializers.IntegerField()

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                'Amount must be a positive number.'
            )
        return value


class SubscriptionRecipeSerializer(serializers.ModelSerializer):
    image = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time',)


class RecipeSerializer(serializers.ModelSerializer):
    ingredients = IngredientAmountSerializer(many=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
    )
    image = Base64ImageField(required=False, allow_null=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients', 'name', 'image',
            'text', 'cooking_time', 'is_favorited', 'is_in_shopping_cart',
        )
        read_only_fields = ('author',)

    def get_is_favorited(self, obj):
        return self._check_user_recipe_status(obj, Favorite)

    def get_is_in_shopping_cart(self, obj):
        return self._check_user_recipe_status(obj, Cart)

    def _check_user_recipe_status(self, obj, model):
        request = self.context.get('request')
        current_user = request.user if request else None
        return (
            current_user.is_authenticated
            and model.objects.filter(
                user=current_user, recipe=obj
            ).exists()
        )

    def validate(self, attrs):
        ingredients_data = attrs.get('ingredients')
        if not ingredients_data:
            raise serializers.ValidationError(
                'At least one ingredient is required.'
            )
        ingredient_ids = [ingredient['id'] for ingredient in ingredients_data]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError(
                'Duplicate ingredients are not allowed.'
            )

        tags_data = attrs.get('tags')
        if not tags_data:
            raise serializers.ValidationError(
                'At least one tag is required.'
            )
        if len(tags_data) != len(set(tags_data)):
            raise serializers.ValidationError(
                'Duplicate tags are not allowed.'
            )

        cooking_time = attrs.get('cooking_time')
        if cooking_time is None or cooking_time <= 0:
            raise serializers.ValidationError(
                'Cooking time must be a positive number.'
            )

        image = attrs.get('image')
        if not image:
            raise serializers.ValidationError(
                'Image is a required field.'
            )
        return attrs

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        self._set_ingredients_and_tags(recipe, ingredients_data, tags_data)
        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')
        instance = super().update(instance, validated_data)
        self._set_ingredients_and_tags(instance, ingredients_data, tags_data)
        return instance

    def _set_ingredients_and_tags(self, recipe, ingredients_data, tags_data):
        if recipe.recipeingredient_set.exists():
            recipe.recipeingredient_set.all().delete()
        recipe_ingredients = (
            RecipeIngredient(
                recipe=recipe,
                ingredient=ingredient_data['id'],
                amount=ingredient_data['amount'],
            )
            for ingredient_data in ingredients_data
        )
        RecipeIngredient.objects.bulk_create(recipe_ingredients)
        recipe.tags.set(tags_data)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['tags'] = TagSerializer(
            instance.tags.all(), many=True
        ).data
        representation['author'] = UserSerializer(
            instance.author,
            context=self.context
        ).data
        representation['ingredients'] = (
            RecipeIngredientSerializer(
                recipe_ingredient,
                context=self.context
            ).data
            for recipe_ingredient in instance.recipeingredient_set.all()
        )
        return representation


class SubscriptionSerializer(serializers.ModelSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Subscription
        fields = ('author', 'recipes', 'recipes_count')
        read_only_fields = ('user',)

    def get_recipes(self, obj):
        recipes_limit = (
            self.context['request']
            .query_params
            .get('recipes_limit')
        )
        recipes = Recipe.objects.filter(author=obj.author)

        if recipes_limit is not None and recipes_limit.isdigit():
            recipes_limit = int(recipes_limit)
            recipes = recipes[:recipes_limit]

        return SubscriptionRecipeSerializer(
            recipes, many=True,
            context=self.context
        ).data

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation.update(UserSerializer(
            instance.author,
            context=self.context
        ).data)
        representation.pop('author', None)
        representation['recipes_count'] = (
            representation.get('recipes_count', 0)
        )
        return representation

    def validate_author(self, value):
        if self.context['request'].user == value:
            raise serializers.ValidationError(
                'User cannot subscribe to themselves.'
            )
        return value

    def validate(self, attrs):
        user = self.context['request'].user
        author = attrs.get('author')

        if Subscription.objects.filter(user=user, author=author).exists():
            raise serializers.ValidationError('Subscription already exists.')

        return attrs


class BaseRecipeActionSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ['user', 'recipe']

    def create(self, validated_data):
        return self.Meta.model.objects.create(**validated_data)


class CartSerializer(BaseRecipeActionSerializer):
    class Meta(BaseRecipeActionSerializer.Meta):
        model = Cart


class FavoriteSerializer(BaseRecipeActionSerializer):
    class Meta(BaseRecipeActionSerializer.Meta):
        model = Favorite
