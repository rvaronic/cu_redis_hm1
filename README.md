# GameHub Redis

Учебный REST API на FastAPI, в котором Redis используется как основное
хранилище и кеш.

## Архитектура

- FastAPI-приложение и минималистичный фронтенд;
- отдельный consumer уведомлений;
- один Redis master и две реплики;
- три Redis Sentinel с кворумом `2`;
- общая Docker-сеть `gamehub-net`.

Приложение и consumer находят текущий master через Sentinel. При запуске
FastAPI проверяет соединение командой `PING` с пятью попытками.

## Запуск

```bash
docker compose up --build
```

После запуска:

- фронтенд: <http://localhost:8000>;
- Swagger: <http://localhost:8000/docs>;
- логи consumer: `docker compose logs -f notification-consumer`.

Остановить систему:

```bash
docker compose down
```

Удалить систему вместе с Redis volumes:

```bash
docker compose down -v
```

## Структуры данных

| Данные | Ключ | Тип | TTL |
|---|---|---|---|
| Профиль | `player:{id}` | Hash | без ограничения |
| Счётчик входов | `login:{id}` | String | 24 часа |
| Кеш профиля | `cache:player:{id}` | String с JSON | 60 секунд |
| Лидерборд | `tournament:main` | Sorted Set | без ограничения |
| Достижения | `achievements:{id}` | Set | без ограничения |
| Уведомления | `notifications` | Stream | 7 дней |

Уведомление содержит поля `player_id`, `type`, `message` и `timestamp`.

## API

| Метод | Путь | Redis-операции |
|---|---|---|
| `POST` | `/api/players/{id}` | `HSET`, `DEL` кеша |
| `GET` | `/api/players/{id}` | `GET`, при cache miss: `HGETALL`, `SET EX 60` |
| `PATCH` | `/api/players/{id}/level` | `HINCRBY`, `DEL`, `XADD` |
| `POST` | `/api/players/{id}/login` | Lua: `INCR`, `EXPIRE 86400` |
| `POST` | `/api/leaderboard/score` | `ZINCRBY` |
| `GET` | `/api/leaderboard/top?limit=10` | `ZREVRANGE ... WITHSCORES` |
| `GET` | `/api/leaderboard/rank/{player_id}` | `ZRANK` |
| `POST` | `/api/players/{id}/achievements` | `SADD` |
| `GET` | `/api/players/{id}/achievements/{name}` | `SISMEMBER` |
| `GET` | `/api/players/{id1}/achievements/common/{id2}` | `SINTER` |
| `POST` | `/api/players/batch` | пачка `HSET` через pipeline |
