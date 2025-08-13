#  Foodgram: управление рецептами.
[![Main Foodgram workflow](https://github.com/sat-bee/foodgram/actions/workflows/main.yml/badge.svg)](https://github.com/sat-bee/foodgram/actions/workflows/main.yml)

https://taskitest.ddns.net
51.250.25.211
admin@admin.admin
admin

## Описание.

Foodgram - платфома позволяющая размещать рецепты, подписываться на авторов рецептов, заносить рецепты в избранное и формировать общий список покупок по выброным рецептам.

## Установка.

Клонировать репозиторий и перейти в него в командной строке:
```bash
git clone https://github.com/sat-bee/foodgram.git
```

В корне репозитория создайте файл .env на основе .env.example
```bash
cp .env.example .env
```
со следующим содержимым:
```
POSTGRES_DB=имя базы Postgres
POSTGRES_USER=пользователь для подключения к базе данных
POSTGRES_PASSWORD=пароль для подключения к базе данных
DB_HOST=ip адрес по которому доступна база данных
DB_PORT=порт базы данных
SECRET_KEY=серктный ключ
```

Убедитесь что у вас установлен Windows Subsystem for Linux [с официального сайта Microsoft](https://learn.microsoft.com/ru-ru/windows/wsl/install)

Убедитесь что у вас установлен Docker - [официальный сайт проекта](https://www.docker.com/products/docker-desktop/)

Запустите WSL
```bash
wsl
```

В корне репозитория Kittygram_final разверните проект
```bash
docker compose -f docker-compose.yml up
```

Проект будет доступен по адресу http://localhost:8000

## Примеры API запросов.

Создание рецепта:

```
POST /api/recipes/
```
```
{
"ingredients": [
{
"id": "int",
"amount": "int"
}
],
"tags": [
"int",
"int"
],
"image": "data:image/png;base64,",
"name": "string",
"text": "string",
"cooking_time": "int"
}
```

Получение рецепта:

```
GET /api/recipes/
```

Удаление рецепта:

```
DELETE /api/recipes/{id}/
```


