import base64

from rest_framework import serializers
from django.core.files.base import ContentFile
from rest_framework.exceptions import NotAuthenticated
from rest_framework.validators import UniqueValidator

from users.models import User
from recipes.models import (
    Tags,
    Ingredients,
    Recipe,
    RecipeIngredient,
    Subscription,
    Favorite,
    Cart
)
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

    def update(self, instance, validated_data):
        instance.username = validated_data.get('username', instance.username)
        instance.email = validated_data.get('email', instance.email)
        instance.first_name = validated_data.get(
            'first_name', instance.first_name
        )
        instance.last_name = validated_data.get(
            'last_name', instance.last_name
        )
        instance.avatar = validated_data.get('avatar', instance.avatar)
        instance.save()
        return instance

    def to_representation(self, instance):
        if not isinstance(instance, User):
            raise NotAuthenticated('Необходимо авторизоваться.')
        return super().to_representation(instance)


class TagSerializer(serializers.ModelSerializer):

    class Meta:
        model = Tags
        fields = ('id', 'name', 'slug')


class IngredientSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ingredients
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
    id = serializers.PrimaryKeyRelatedField(queryset=Ingredients.objects.all())
    amount = serializers.IntegerField()

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Amount must be a positive number."
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
        queryset=Tags.objects.all(),
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
                "At least one ingredient is required."
            )
        ingredient_ids = [ingredient['id'] for ingredient in ingredients_data]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError(
                "Duplicate ingredients are not allowed."
            )

        tags_data = attrs.get('tags')
        if not tags_data:
            raise serializers.ValidationError(
                "At least one tag is required."
            )
        if len(tags_data) != len(set(tags_data)):
            raise serializers.ValidationError(
                "Duplicate tags are not allowed."
            )

        cooking_time = attrs.get('cooking_time')
        if cooking_time is None or cooking_time <= 0:
            raise serializers.ValidationError(
                "Cooking time must be a positive number."
            )

        image = attrs.get('image')
        if not image:
            raise serializers.ValidationError(
                "Image is a required field."
            )
        return attrs

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)

        for ingredient_data in ingredients_data:
            ingredient = ingredient_data['id']
            amount = ingredient_data['amount']
            RecipeIngredient.objects.create(
                recipe=recipe, ingredient=ingredient, amount=amount
            )

        recipe.tags.set(tags_data)
        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('ingredients', None)
        tags_data = validated_data.pop('tags', None)

        instance.name = validated_data.get('name', instance.name)
        instance.text = validated_data.get('text', instance.text)
        instance.cooking_time = validated_data.get(
            'cooking_time', instance.cooking_time
        )
        instance.image = validated_data.get('image', instance.image)
        instance.save()

        if tags_data is not None:
            instance.tags.set(tags_data)
        if ingredients_data is not None:
            instance.recipeingredient_set.all().delete()
            for ingredient_data in ingredients_data:
                ingredient = ingredient_data['id']
                amount = ingredient_data['amount']
                RecipeIngredient.objects.create(
                    recipe=instance, ingredient=ingredient, amount=amount
                )

        return instance

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['tags'] = TagSerializer(
            instance.tags.all(), many=True
        ).data
        representation['author'] = UserSerializer(
            instance.author,
            context=self.context
        ).data
        representation['ingredients'] = [
            RecipeIngredientSerializer(
                recipe_ingredient,
                context=self.context
            ).data
            for recipe_ingredient in instance.recipeingredient_set.all()
        ]
        return representation


class SubscriptionSerializer(serializers.ModelSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(
        source='author.recipe.count',
        read_only=True
    )

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
        if recipes_limit is not None:
            try:
                recipes_limit = int(recipes_limit)
                recipes = recipes[:recipes_limit]
            except ValueError:
                pass
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
        return representation
