import csv
import os

from django.conf import settings
from django.core.management.base import BaseCommand
from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Import CSV data into Ingredients'

    def handle(self, *args, **kwargs):
        csv_file_path = os.path.join(
            settings.BASE_DIR,
            'data', 'ingredients.csv'
        )
        ingredients_list = []
        with open(csv_file_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                ingredients_list.append(
                    Ingredient(
                        name=row[0],
                        measurement_unit=row[1],
                    )
                )
        Ingredient.objects.bulk_create(ingredients_list)
