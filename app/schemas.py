from pydantic import BaseModel, Field


class PlayerProfileUpsert(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    level: int = Field(ge=0)
    region: str = Field(min_length=1, max_length=50)


class LevelUpdate(BaseModel):
    delta: int


class LeaderboardScoreCreate(BaseModel):
    player_id: str = Field(min_length=1)
    score: float


class AchievementCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class BatchPlayerCreate(PlayerProfileUpsert):
    id: str = Field(min_length=1)


class BatchPlayersCreate(BaseModel):
    players: list[BatchPlayerCreate] = Field(min_length=1)
