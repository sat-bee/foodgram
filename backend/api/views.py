import random
import string

from djoser import views as djoser_views
from rest_framework import generics, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticatedOrReadOnly
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django.http import HttpResponse

from users.models import User
from recipes.models import (
    Tags,
    Ingredients,
    Recipe,
    Subscription,
    Cart,
    RecipeIngredient,
    Favorite,
    Shortcut
)
from .serializers import (
    UserSerializer,
    TagSerializer,
    IngredientSerializer,
    RecipeSerializer,
    SubscriptionSerializer,
    SubscriptionRecipeSerializer
)
from .filters import IngredientsFilter, RecipeFilter
from .permissions import OwnerOrReadOnly


class LimitPageNumberPagination(PageNumberPagination):
    page_size_query_param = 'limit'
    max_page_size = 6


class UserViewSet(djoser_views.UserViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class UserAvatarUpdateView(generics.UpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user

    def put(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not request.data or 'avatar' not in request.data:
            return Response(
                {"error": "Avatar field is required."},
                status=400
            )
        serializer = self.get_serializer(
            self.object, data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(
            {"avatar": self.object.avatar.url if self.object.avatar else None}
        )

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.avatar:
            self.object.avatar.delete(save=False)
            self.object.avatar = None
            self.object.save()
            return Response(
                {"message": "Avatar deleted successfully."},
                status=204
            )
        return Response({"message": "No avatar to delete."}, status=404)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    queryset = Tags.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    queryset = Ingredients.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientsFilter


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = (OwnerOrReadOnly,)
    pagination_class = LimitPageNumberPagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['get'], url_path='get-link')
    def get_short_link(self, request, pk=None):
        recipe = self.get_object()
        shortcut, created = Shortcut.objects.get_or_create(recipe=recipe)

        if created:
            shortcut.link = self.generate_short_link()
            shortcut.save()

        short_link = f"https://foodgram.example.org{shortcut.link}"
        return Response({"short-link": short_link}, status=status.HTTP_200_OK)

    def generate_short_link(self):
        """Generate a random short link string."""
        length = 6  # Length of the generated string
        characters = string.ascii_letters + string.digits
        return '/s/' + ''.join(random.choices(characters, k=length))

    @action(detail=False, methods=['get'], url_path='download_shopping_cart')
    def download_shopping_cart(self, request):
        user = request.user
        cart_items = Cart.objects.filter(user=user)

        ingredients_dict = {}

        for cart_item in cart_items:
            recipe_ingredients = (
                RecipeIngredient.objects
                .filter(recipe=cart_item.recipe)
            )
            for recipe_ingredient in recipe_ingredients:
                ingredient_name = recipe_ingredient.ingredient.name
                measurement_unit = (
                    recipe_ingredient.ingredient.measurement_unit
                )
                amount = recipe_ingredient.amount

                if ingredient_name in ingredients_dict:
                    ingredients_dict[ingredient_name]['amount'] += amount
                else:
                    ingredients_dict[ingredient_name] = {
                        'measurement_unit': measurement_unit,
                        'amount': amount
                    }

        response = HttpResponse(content_type='text/plain')
        response['Content-Disposition'] = (
            'attachment; filename="shopping_cart.txt"'
        )

        for name, details in ingredients_dict.items():
            response.write(
                "{} ({}) - {}\n"
                .format(
                    name,
                    details['measurement_unit'],
                    details['amount']
                )
            )

        return response

    def manage_item(
        self,
        request,
        pk=None,
        model_class=None,
        action_type=None
    ):
        recipe = self.get_object()
        user = request.user

        if action_type == 'cart':
            queryset = Cart.objects.filter(user=user, recipe=recipe)
        elif action_type == 'favorite':
            queryset = Favorite.objects.filter(user=user, recipe=recipe)
        else:
            return Response(
                {"detail": "Invalid action."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if request.method == 'POST':
            if queryset.exists():
                return Response(
                    {"detail": f"Recipe is already in {action_type}s."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if action_type == 'cart':
                Cart.objects.create(user=user, recipe=recipe)
            else:
                Favorite.objects.create(user=user, recipe=recipe)
            serializer = SubscriptionRecipeSerializer(recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        elif request.method == 'DELETE':
            item = queryset.first()
            if not item:
                return Response(
                    {"detail": f"Recipe is not in the {action_type}."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            item.delete()
            return Response(
                {"detail": f"Recipe removed from the {action_type}."},
                status=status.HTTP_204_NO_CONTENT
            )

    shopping_cart_action = {
        'detail': True,
        'methods': ['post', 'delete'],
        'url_path': 'shopping_cart',
        'permission_classes': [IsAuthenticatedOrReadOnly]
    }

    @action(**shopping_cart_action)
    def manage_shopping_cart(self, request, pk=None):
        return self.manage_item(
            request,
            pk,
            model_class=Cart,
            action_type='cart'
        )

    manage_favorite_action = {
        'detail': True,
        'methods': ['post', 'delete'],
        'url_path': 'favorite',
        'permission_classes': [IsAuthenticatedOrReadOnly]
    }

    @action(**manage_favorite_action)
    def manage_favorite(self, request, pk=None):
        return self.manage_item(
            request,
            pk,
            model_class=Favorite,
            action_type='favorite'
        )


class SubscriptionViewSet(viewsets.ModelViewSet):
    serializer_class = SubscriptionSerializer
    pagination_class = LimitPageNumberPagination

    def create(self, request, *args, **kwargs):
        author_id = kwargs.get('user_id')
        try:
            author = User.objects.get(id=author_id)
            if request.user == author:
                return Response(
                    {'error': 'User cannot subscribe to themselves.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if Subscription.objects.filter(
                user=request.user,
                author=author
            ).exists():
                return Response(
                    {'error': 'Subscription already exists.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            serializer = self.get_serializer(data={'author': author.id})
            serializer.is_valid(raise_exception=True)
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

    def list(self, request):
        current_user = request.user
        subscriptions = Subscription.objects.filter(user=current_user)

        paginator = self.pagination_class()
        paginated_subscriptions = paginator.paginate_queryset(
            subscriptions, request
        )

        serializer = SubscriptionSerializer(
            paginated_subscriptions,
            many=True,
            context={'request': request}
        )
        return paginator.get_paginated_response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        author_id = kwargs.get('user_id')
        try:
            author = User.objects.get(id=author_id)
            subscription = (
                Subscription.objects
                .get(user=request.user, author=author)
            )
            subscription.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Subscription.DoesNotExist:
            return Response(
                {'error': 'Subscription not found.'},
                status=status.HTTP_400_BAD_REQUEST
            )
