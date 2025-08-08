from django_filters import rest_framework as filters

from recipes.models import Ingredients, Recipe, Tags, Cart, Favorite


class IngredientsFilter(filters.FilterSet):
    name = filters.CharFilter(lookup_expr='startswith')

    class Meta:
        model = Ingredients
        fields = ('name',)


class RecipeFilter(filters.FilterSet):
    author = filters.NumberFilter(field_name='author', lookup_expr='exact')
    tags = filters.ModelMultipleChoiceFilter(
        field_name='tags__slug',
        queryset=Tags.objects.all(),
        to_field_name='slug'
    )
    is_in_shopping_cart = filters.BooleanFilter(
        method='filter_in_shopping_cart'
    )
    is_favorited = filters.BooleanFilter(method='filter_favorited')

    class Meta:
        model = Recipe
        fields = ('author', 'tags', 'is_in_shopping_cart', 'is_favorited')

    def filter_in_shopping_cart(self, queryset, name, value):
        user = self.request.user
        if user.is_authenticated and value:
            cart_recipes = (
                Cart.objects
                .filter(user=user)
                .values_list('recipe_id', flat=True)
            )
            return queryset.filter(id__in=cart_recipes)
        return queryset

    def filter_favorited(self, queryset, name, value):
        user = self.request.user
        if user.is_authenticated and value:
            favorite_recipes = (
                Favorite.objects
                .filter(user=user)
                .values_list('recipe_id', flat=True)
            )
            return queryset.filter(id__in=favorite_recipes)
        return queryset
