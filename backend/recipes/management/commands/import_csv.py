import csv
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from recipes.models import Ingredients


class Command(BaseCommand):
    help = 'Import CSV data into YourModel'

    def handle(self, *args, **kwargs):
        csv_file_path = os.path.join(
            settings.BASE_DIR,
            'data', 'ingredients.csv'
        )
        with open(csv_file_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                Ingredients.objects.create(
                    name=row[0],
                    measurement_unit=row[1],
                )
