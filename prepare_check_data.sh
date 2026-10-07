#!/usr/bin/env bash

set -ruo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"

request() {
  curl --fail --silent --show-error "$@"
  printf '\n'
}

echo ""
echo "Создаём профиль 1001"
request -X POST "$BASE_URL/api/players/1001" \
  -H 'Content-Type: application/json' \
  -d '{"name":"Alex","level":10,"region":"ru"}'

echo ""
echo "Добавляем достижение"
request -X POST "$BASE_URL/api/players/1001/achievements" \
  -H 'Content-Type: application/json' \
  -d '{"name":"first-win"}'

echo ""
echo "Регистрируем вход"
request -X POST "$BASE_URL/api/players/1001/login"

echo ""
echo "Добавляем игрока в лидерборд"
request -X POST "$BASE_URL/api/leaderboard/score" \
  -H 'Content-Type: application/json' \
  -d '{"player_id":"1001","score":100}'

echo ""
echo "Изменяем уровень и создаём уведомление"
request -X PATCH "$BASE_URL/api/players/1001/level" \
  -H 'Content-Type: application/json' \
  -d '{"delta":1}'

echo ""
echo "Создаём 10 профилей через pipeline"
request -X POST "$BASE_URL/api/players/batch" \
  -H 'Content-Type: application/json' \
  -d '{
    "players": [
      {"id":"2001","name":"Player 1","level":1,"region":"ru"},
      {"id":"2002","name":"Player 2","level":2,"region":"ru"},
      {"id":"2003","name":"Player 3","level":3,"region":"ru"},
      {"id":"2004","name":"Player 4","level":4,"region":"ru"},
      {"id":"2005","name":"Player 5","level":5,"region":"ru"},
      {"id":"2006","name":"Player 6","level":6,"region":"ru"},
      {"id":"2007","name":"Player 7","level":7,"region":"ru"},
      {"id":"2008","name":"Player 8","level":8,"region":"ru"},
      {"id":"2009","name":"Player 9","level":9,"region":"ru"},
      {"id":"2010","name":"Player 10","level":10,"region":"ru"}
    ]
  }'

echo ""
echo "Заполняем кеш профиля 1001"
request "$BASE_URL/api/players/1001"

echo "Данные подготовлены. Сразу запустите: python3 dz1_check.py"
