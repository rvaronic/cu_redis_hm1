import asyncio

from redis.asyncio.sentinel import Sentinel
from redis.exceptions import RedisError, ResponseError

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
    socket_timeout=10,
)


async def create_group() -> None:
    print(
        "[redis] XGROUP CREATE notifications "
        "notifications-group $ MKSTREAM"
    )

    try:
        await redis_client.xgroup_create(
            name="notifications",
            groupname="notifications-group",
            id="$",
            mkstream=True,
        )
    except ResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            print(f"[redis] failed to create notifications-group: {exc}")
            raise

        print("[redis] notifications-group already exists")
    else:
        print("[redis] notifications-group created")
        


async def process_message(
    message_id: str,
    fields: dict[str, str],
) -> None:
    print(
        f"[notification] id={message_id} "
        f"player_id={fields.get('player_id')} "
        f"type={fields.get('type')} "
        f"message={fields.get('message')} "
        f"timestamp={fields.get('timestamp')}"
    )


async def consume() -> None:
    await create_group()

    while True:
        try:
            print(
                "[redis] XREADGROUP GROUP notifications-group "
                "consumer-1 COUNT 10 BLOCK 5000 "
                "STREAMS notifications >"
            )

            streams = await redis_client.xreadgroup(
                groupname="notifications-group",
                consumername="consumer-1",
                streams={"notifications": ">"},
                count=10,
                block=5000,
            )

            for _, messages in streams:
                for message_id, fields in messages:
                    try:
                        await process_message(message_id, fields)

                        print(
                            "[redis] XACK notifications "
                            f"notifications-group {message_id}"
                        )
                        await redis_client.xack(
                            "notifications",
                            "notifications-group",
                            message_id,
                        )
                    except Exception as exc:
                        print(
                            f"[consumer] failed to process "
                            f"{message_id}: {exc}"
                        )
        except RedisError as exc:
            print(f"[redis] temporarily unavailable: {exc}")
            await asyncio.sleep(1)


async def main() -> None:
    await consume()


if __name__ == "__main__":
    asyncio.run(main())
