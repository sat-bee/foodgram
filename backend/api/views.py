import random
import string

from django.db.models import Count, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser import views as djoser_views
from recipes.models import (Cart, Favorite, Ingredient, Recipe,
                            RecipeIngredient, Subscription, Tag)
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import (AllowAny, IsAuthenticated,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.response import Response

from users.models import User
from .filters import IngredientsFilter, RecipeFilter
from .permissions import OwnerOrReadOnly
from .serializers import (CartSerializer, FavoriteSerializer,
                          IngredientSerializer, RecipeSerializer,
                          SubscriptionRecipeSerializer, SubscriptionSerializer,
                          TagSerializer, UserSerializer)


class LimitPageNumberPagination(PageNumberPagination):
    page_size_query_param = 'limit'
    max_page_size = 6


class UserViewSet(djoser_views.UserViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.action == 'retrieve':
            self.permission_classes = [AllowAny]
        else:
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()


class UserAvatarUpdateView(generics.UpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user

    def put(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not request.data or 'avatar' not in request.data:
            return Response(
                {'error': 'Avatar field is required.'},
                status=400
            )
        serializer = self.get_serializer(
            self.object, data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(
            {'avatar': self.object.avatar.url if self.object.avatar else None}
        )

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.avatar:
            self.object.avatar.delete(save=False)
            self.object.save()
            return Response(
                {'message': 'Avatar deleted successfully.'},
                status=204
            )
        return Response({'message': 'No avatar to delete.'}, status=404)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientsFilter


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = (
        Recipe.objects
        .select_related('author')
        .prefetch_related('tags', 'ingredients')
    )
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

        if recipe.link == '':
            recipe.link = self.generate_short_link()
            recipe.save()

        short_link = f'https://taskitest.ddns.net{recipe.link}'
        return Response({'short-link': short_link}, status=status.HTTP_200_OK)

    def generate_short_link(self):
        length = 6  # Length of the generated string
        characters = f'{string.ascii_letters}{string.digits}'
        while True:
            new_link = '/s/' + ''.join(random.choices(characters, k=length))
            if not Recipe.objects.filter(link=new_link).exists():
                return new_link

    @action(detail=False, methods=['get'], url_path='download_shopping_cart')
    def download_shopping_cart(self, request):
        user = request.user
        ingredients = (
            RecipeIngredient.objects
            .filter(recipe__cart__user=user)
            .values('ingredient__name', 'ingredient__measurement_unit')
            .annotate(total_amount=Sum('amount'))
        )
        ingredients_dict = {
            item['ingredient__name']: {
                'measurement_unit': item['ingredient__measurement_unit'],
                'amount': item['total_amount']
            }
            for item in ingredients
        }
        return self.create_shopping_cart_response(ingredients_dict)

    def create_shopping_cart_response(self, ingredients_dict):
        response = HttpResponse(content_type='text/plain')
        response['Content-Disposition'] = (
            'attachment; filename="shopping_cart.txt"'
        )
        for name, details in ingredients_dict.items():
            response.write(
                '{} ({}) - {}\n'.format(
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
        serializer_class=None,
    ):
        recipe = self.get_object()
        user = request.user
        queryset = model_class.objects.filter(user=user, recipe=recipe)

        if request.method == 'POST':
            if queryset.exists():
                return Response(
                    {'detail': (
                        f'Recipe is already in '
                        f'{model_class.__name__.lower()}.'
                    )},
                    status=status.HTTP_400_BAD_REQUEST
                )

            serializer = serializer_class(
                data={
                    'user': user.id,
                    'recipe': recipe.id
                }
            )
            if serializer.is_valid():
                serializer.save()
                return Response(
                    SubscriptionRecipeSerializer(recipe).data,
                    status=status.HTTP_201_CREATED
                )
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        elif request.method == 'DELETE':
            if not queryset.exists():
                return Response(
                    {'detail': (
                        f'Recipe is not in the {model_class.__name__.lower()}.'
                    )},
                    status=status.HTTP_400_BAD_REQUEST
                )
            queryset.delete()
            return Response(
                {'detail': (
                    f'Recipe removed from the {model_class.__name__.lower()}.'
                )},
                status=status.HTTP_204_NO_CONTENT
            )

    @action(
        detail=True,
        methods=['post', 'delete'],
        url_path='shopping_cart',
        permission_classes=[IsAuthenticatedOrReadOnly]
    )
    def manage_shopping_cart(self, request, pk=None):
        return self.manage_item(
            request,
            pk,
            model_class=Cart,
            serializer_class=CartSerializer,
        )

    @action(
        detail=True,
        methods=['post', 'delete'],
        url_path='favorite',
        permission_classes=[IsAuthenticatedOrReadOnly]
    )
    def manage_favorite(self, request, pk=None):
        return self.manage_item(
            request,
            pk,
            model_class=Favorite,
            serializer_class=FavoriteSerializer,
        )


class SubscriptionViewSet(viewsets.ModelViewSet):
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerializer
    pagination_class = LimitPageNumberPagination

    def get_queryset(self):
        return (
            Subscription.objects
            .annotate(recipes_count=Count('author__recipe'))
        )

    def create(self, request, *args, **kwargs):
        author_id = kwargs.get('user_id')
        author = get_object_or_404(User, id=author_id)
        serializer = self.get_serializer(data={'author': author.id})
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

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
