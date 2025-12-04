from pydantic import BaseModel


class AnimeItem(BaseModel):
    id: int
    title: str
    main_picture: dict[str, str] | None = None
    synopsis: str | None = None
    mean: float | None = None
    rank: int | None = None
    popularity: int | None = None
    num_list_users: int | None = None
    num_scoring_users: int | None = None
    nsfw: str | None = None
    media_type: str | None = None
    status: str | None = None
    genres: list[dict[str, int | str]] | None = None
    num_episodes: int | None = None
    start_season: dict[str, int | str] | None = None
    broadcast: dict[str, str] | None = None
    source: str | None = None
    average_episode_duration: int | None = None
    rating: str | None = None
    studios: list[dict[str, int | str]] | None = None
