import asyncio
import datetime
import json

from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from redis.asyncio.sentinel import Sentinel
from redis.exceptions import RedisError

from app.schemas import (
    AchievementCreate,
    BatchPlayersCreate,
    LeaderboardScoreCreate,
    LevelUpdate,
    PlayerProfileUpsert,
)


BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "frontend"

app = FastAPI(title="GameHub",)
api = APIRouter(prefix="/api")


sentinel = Sentinel(
    [
        ("redis-sentinel-1", 26379),
        ("redis-sentinel-2", 26379),
        ("redis-sentinel-3", 26379),
    ],
    socket_timeout=1,
)

redis_client = sentinel.master_for(
    "mymaster",
    decode_responses=True,
    socket_timeout=1,
)


@app.on_event("startup")
async def check_redis_connection() -> None:
    for attempt in range(5):
        try:
            print("[redis] PING")
            await redis_client.ping()
            break
        except RedisError as exc:
            if attempt == 4:
                raise

            print(f"[redis] connection failed: {exc}")
            await asyncio.sleep(1)


@api.post("/players/batch")
async def create_players_batch(payload: BatchPlayersCreate):
    commands = []
    async with redis_client.pipeline(transaction=False) as pipe:
        for player in payload.players:
            pipe.hset(
                f"player:{player.id}",
                mapping={
                    "name": player.name,
                    "level": player.level,
                    "region": player.region,
                    "created_at": int(datetime.datetime.now().timestamp()),
                }
            )
            commands.append(
                f"HSET player:{player.id} name {player.name} level "
                f"{player.level} region {player.region} created_at {int(datetime.datetime.now().timestamp())}"
            )
        await pipe.execute()
    return {"status": "ok", "commands": commands}


@api.post("/players/{player_id}")
async def upsert_player(player_id: str, payload: PlayerProfileUpsert):
    created_at = int(datetime.datetime.now().timestamp())

    await redis_client.hset(
        f"player:{player_id}",
        mapping={
            "name": payload.name,
            "level": payload.level,
            "region": payload.region,
            "created_at": created_at,
        }
    )
    await redis_client.delete(f"cache:player:{player_id}")

    return {
        "status": "ok",
        "commands": [
            f"HSET player:{player_id} name {payload.name} level {payload.level} "
            f"region {payload.region} created_at {created_at}",
            f"DEL cache:player:{player_id}",
        ]
    }


@api.get("/players/{player_id}")
async def get_player(player_id: str):
    commands = []

    player = await redis_client.get(
        f"cache:player:{player_id}"
    )
    commands.append(f"GET cache:player:{player_id}")

    if player is None:
        player = await redis_client.hgetall(
            f"player:{player_id}"
        )
        commands.append(f"HGETALL player:{player_id}")

        await redis_client.set(
            f"cache:player:{player_id}",
            json.dumps(player),
            ex=60
        )
        commands.append(f"SET cache:player:{player_id} {json.dumps(player)} EX 60")

    else:
        player = json.loads(player)

    return {"status": "ok", "commands": commands, "player": player}
    

@api.patch("/players/{player_id}/level")
async def update_player_level(player_id: str, payload: LevelUpdate):
    commands = []
    notification_timestamp = int(datetime.datetime.now().timestamp())
    notification_min_id = f"{(notification_timestamp - 7 * 24 * 60 * 60) * 1000}-0"
    notification_message = f"Level changed by {payload.delta}"

    player_exists = await redis_client.exists(f"player:{player_id}")
    commands.append(f"EXISTS player:{player_id}")
    if not player_exists:
        raise HTTPException(status_code=404, detail="Player not found")

    async with redis_client.pipeline(transaction=True) as pipe:
        commands.append("MULTI")  # не уверен, что это до конца правда, но для учебного проекта как будто ок
        
        pipe.hincrby(
            f"player:{player_id}", "level", payload.delta
        )
        commands.append(f"HINCRBY player:{player_id} level {payload.delta}")
        
        pipe.delete(f"cache:player:{player_id}")
        commands.append(f"DEL cache:player:{player_id}")
        
        pipe.xadd(
            "notifications",
            {
                "player_id": player_id,
                "type": "level_changed",
                "message": notification_message,
                "timestamp": notification_timestamp,
            },
            minid=notification_min_id,
            approximate=True,
        )
        commands.append(
            f"XADD notifications MINID ~ {notification_min_id} * "
            f"player_id {player_id} type level_changed "
            f"message {notification_message} "
            f"timestamp {notification_timestamp}"
        )
        
        await pipe.execute()
        commands.append("EXEC")

    return {"status": "ok", "commands": commands}


@api.post("/players/{player_id}/login")
async def register_login(player_id: str):
    lua_script = """
        local key = KEYS[1]

        redis.call("INCR", key)
        redis.call("EXPIRE", key, 86400)
    """
    await redis_client.eval(lua_script, 1, f"logins:{player_id}")
    return {
        "status": "ok",
        "commands": [
            f"EVAL {lua_script} 1 logins:{player_id}",
        ],
    }


@api.post("/leaderboard/score")
async def add_score(payload: LeaderboardScoreCreate):
    await redis_client.zincrby(
        "tournament:main",
        payload.score,
        payload.player_id,
    )
    return {"status": "ok", "commands": [f"ZINCRBY tournament:main {payload.score} {payload.player_id}"]}


@api.get("/leaderboard/top")
async def get_leaderboard_top(limit: int = Query(default=10, ge=1, le=100)):
    leaderboard = await redis_client.zrevrange("tournament:main", 0, limit - 1, withscores=True)
    return {
        "status": "ok",
        "commands": [f"ZREVRANGE tournament:main 0 {limit - 1} WITHSCORES"],
        "leaderboard": leaderboard
    }


@api.get("/leaderboard/rank/{player_id}")
async def get_player_rank(player_id: str):
    rank = await redis_client.zrank("tournament:main", player_id)
    return {
        "status": "ok",
        "commands": [f"ZRANK tournament:main {player_id}"],
        "rank": rank
    }


@api.post("/players/{player_id}/achievements")
async def add_achievement(player_id: str, payload: AchievementCreate):
    await redis_client.sadd(f"achievements:{player_id}", payload.name)
    return {
        "status": "ok",
        "commands": [f"SADD achievements:{player_id} {payload.name}"]
    }


@api.get("/players/{player_id}/achievements/{name}")
async def has_achievement(player_id: str, name: str):
    has_achievement = await redis_client.sismember(f"achievements:{player_id}", name)
    return {
        "status": "ok",
        "commands": [f"SISMEMBER achievements:{player_id} {name}"],
        "has_achievement": has_achievement
    }


@api.get("/players/{first_player_id}/achievements/common/{second_player_id}")
async def get_common_achievements(first_player_id: str, second_player_id: str):
    common_achievements = await redis_client.sinter(
        f"achievements:{first_player_id}",
        f"achievements:{second_player_id}"
    )
    return {
        "status": "ok",
        "commands": [f"SINTER achievements:{first_player_id} achievements:{second_player_id}"],
        "common_achievements": common_achievements
    }


app.include_router(api)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")
