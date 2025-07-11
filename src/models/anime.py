from typing import Dict, List, Optional, Union

from pydantic import BaseModel


class AnimeItem(BaseModel):
    id: int
    title: str
    main_picture: Optional[Dict[str, str]] = None
    synopsis: Optional[str] = None
    mean: Optional[float] = None
    rank: Optional[int] = None
    popularity: Optional[int] = None
    num_list_users: Optional[int] = None
    num_scoring_users: Optional[int] = None
    nsfw: Optional[str] = None
    media_type: Optional[str] = None
    status: Optional[str] = None
    genres: Optional[List[Dict[str, Union[int, str]]]] = None
    num_episodes: Optional[int] = None
    start_season: Optional[Dict[str, Union[int, str]]] = None
    broadcast: Optional[Dict[str, str]] = None
    source: Optional[str] = None
    average_episode_duration: Optional[int] = None
    rating: Optional[str] = None
    studios: Optional[List[Dict[str, Union[int, str]]]] = None
