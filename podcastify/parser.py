import email.utils as eut
import logging
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import quote

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from podcastify.config import Config

logger = logging.getLogger(__name__)


def rfc2822_date(dt: datetime) -> str:
    return eut.format_datetime(dt.astimezone(timezone.utc))


_NAME_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


def _is_valid_name(name: str) -> bool:
    return bool(_NAME_PATTERN.fullmatch(name)) and ".." not in name


class EpisodeModel(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    file: str = Field(
        description=(
            "Media filename (`.mp3`, `.m4a`, `.mp4`, `.ogg` or `.opus`), basename only, placed in `public/<name>/`; "
            "empty, `.` and `..` are rejected, and so is a second entry with the same basename"
        )
    )
    title: Optional[str] = Field(None, description="Episode title; defaults to the filename stem")
    description: Optional[str] = Field(None, description="Episode description")
    summary: Optional[str] = Field(None, description="Longer summary; falls back to `description`")
    subtitle: Optional[str] = Field(None, description="Brief subtitle")
    pub_date: Optional[datetime] = Field(
        None,
        description=(
            "ISO 8601 date or date-time, quoted or not; a value without a timezone is read as UTC, "
            "an invalid value is logged and ignored; defaults to the file modification time"
        ),
    )
    image: Optional[str] = Field(None, description="Episode image filename or URL")
    explicit: Optional[bool] = Field(None, description="Overrides the channel `explicit` when set")
    author_name: Optional[str] = Field(
        None, alias="author-name", description="Overrides the channel author for this episode"
    )
    season: Optional[int] = Field(None, description="Season number")
    episode: Optional[int] = Field(None, description="Episode number within the season")
    episode_type: Optional[str] = Field(None, description="`full`, `trailer` or `bonus`")
    guid: Optional[str] = Field(
        None,
        description=(
            "Unique identifier; defaults to the SHA-1 of `<podcast>/<filename>`; "
            "must be unique within the podcast, a duplicate rejects the whole config"
        ),
    )
    duration_hms: Optional[str] = Field(
        None,
        description="Pre-set duration as `H:MM:SS` or `M:SS`; read from the media file with `tinytag` when omitted",
    )

    @field_validator("file")
    @classmethod
    def validate_file(cls, v: str) -> str:
        if Path(v).name in ("", ".", ".."):
            raise ValueError(f"file must name a media file, got '{v}'")
        return v

    @field_validator("pub_date", mode="before")
    @classmethod
    def parse_pub_date(cls, v: Any) -> Optional[datetime]:
        if v is None or v == "":
            return None
        if isinstance(v, datetime):
            parsed = v
        elif isinstance(v, date):
            parsed = datetime(v.year, v.month, v.day)
        elif isinstance(v, str):
            try:
                parsed = datetime.fromisoformat(v.strip())
            except ValueError:
                logger.warning(f"Invalid pub_date '{v}'; using file modification time")
                return None
        else:
            logger.warning(f"Invalid pub_date '{v}'; using file modification time")
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed


class PodcastChannelModel(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    name: Optional[str] = Field(
        None,
        description=(
            "Optional; the name before `-podcast.yaml` is always the identifier, "
            "and a different `name` is ignored with a warning"
        ),
    )
    title: str = Field(description="Podcast title shown in podcast apps")
    author_name: Optional[str] = Field(
        None,
        alias="author-name",
        description="Author or creator name; with neither this nor `author`, the feed has no author element",
    )
    author: Optional[str] = Field(
        None, description="Legacy alias, used as the author name when `author-name` is absent or empty"
    )
    author_email: Optional[str] = Field(None, alias="author-email", description="Contact email for the podcast owner")
    subtitle: Optional[str] = Field(None, description="Brief subtitle shown in podcast apps")
    summary: Optional[str] = Field(None, description="Longer summary; falls back to `description` when omitted")
    description: str = Field(description="Short description of the podcast")
    language: str = Field("en", description="Language code, for example `en` or `fr`")
    explicit: Optional[bool] = Field(False, description="Whether the content is explicit")
    image: Optional[str] = Field(None, description="Cover image filename in `public/<name>/`, or a full URL")
    link: Optional[str] = Field(None, description="Website URL for the podcast; defaults to `PUBLIC_BASE_URL`")
    categories: Optional[Union[str, List[Any], Dict[str, Any]]] = Field(
        None, description="iTunes categories; see [Categories Format](#categories-format)"
    )
    type: Optional[str] = Field(None, description="`episodic` or `serial`")
    block: Optional[bool] = Field(None, description="If `true`, prevents the podcast from appearing in iTunes")
    complete: Optional[bool] = Field(None, description="If `true`, marks the podcast as complete (no new episodes)")
    new_feed_url: Optional[str] = Field(None, description="Redirect URL for subscribers if the feed moves")
    listed: bool = Field(
        True,
        description="List this feed on the generated index page; false hides it from the page only, not from its URL",
    )
    episodes: Optional[List[EpisodeModel]] = Field(
        None,
        description=("Explicit episode list; a non-empty list turns auto-discovery off, see [Episodes](#episodes)"),
    )

    @model_validator(mode="after")
    def map_legacy_author(self) -> "PodcastChannelModel":
        if not self.author_name and self.author:
            self.author_name = self.author
        return self

    @model_validator(mode="after")
    def reject_duplicate_episodes(self) -> "PodcastChannelModel":
        files: Dict[str, int] = {}
        guids: Dict[str, int] = {}
        for index, ep in enumerate(self.episodes or [], start=1):
            fname = Path(ep.file).name
            if fname in files:
                raise ValueError(f"duplicate episode file '{fname}' (episodes {files[fname]} and {index})")
            files[fname] = index
            if ep.guid:
                if ep.guid in guids:
                    raise ValueError(f"duplicate episode guid '{ep.guid}' (episodes {guids[ep.guid]} and {index})")
                guids[ep.guid] = index
        return self

    @field_validator("language", mode="before")
    @classmethod
    def default_language(cls, v: Any) -> Any:
        return v or "en"

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("episodic", "serial"):
            raise ValueError("type must be 'episodic' or 'serial'")
        return v


class PodcastFileModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    podcast: Optional[PodcastChannelModel] = None

    @model_validator(mode="before")
    @classmethod
    def accept_flat_or_nested(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        if isinstance(data.get("podcast"), dict):
            return data
        return {"podcast": data}


@dataclass(frozen=True)
class Episode:
    model: EpisodeModel
    path: Path
    published: datetime


def _unknown_keys(parsed: PodcastFileModel, channel: PodcastChannelModel) -> List[str]:
    keys = [*(parsed.model_extra or {}), *(channel.model_extra or {})]
    for index, episode in enumerate(channel.episodes or [], start=1):
        keys += [f"episodes[{index}].{key}" for key in episode.model_extra or {}]
    return keys


def validate_podcast_config(raw: Dict[str, Any]) -> Tuple[Optional[PodcastChannelModel], Optional[str]]:
    try:
        parsed = PodcastFileModel.model_validate(raw)
        channel = parsed.podcast
        if channel is None:
            return None, "missing podcast configuration"
        for key in _unknown_keys(parsed, channel):
            logger.warning(f"Unknown config key '{key}' ignored; check its spelling")
        return channel, None
    except ValidationError as e:
        return None, str(e)


class ConfigurationManager:
    @staticmethod
    def load_yaml(path: Path) -> Dict[str, Any]:
        try:
            with path.open("r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except (yaml.YAMLError, OSError) as e:
            logger.error(f"Failed to load config {path}: {e}")
            return {}

    @staticmethod
    def discover_podcast_configs() -> List[Tuple[str, Path]]:
        if not Config.PODCASTS_ROOT.exists():
            logger.warning(f"Podcasts directory not found: {Config.PODCASTS_ROOT}")
            logger.debug(f"Podcasts dir scan: {Config.PODCASTS_ROOT} does not exist")
            return []
        configs: List[Tuple[str, Path]] = []
        seen: Dict[str, Path] = {}
        for cfg in sorted(Config.PODCASTS_ROOT.iterdir()):
            if not cfg.is_file():
                continue
            name = cfg.name
            if name.endswith(("-podcast.yaml", "-podcast.yml")):
                pod_name = name.rsplit("-podcast.", 1)[0]
                if not _is_valid_name(pod_name):
                    logger.warning(
                        f"Skipping config {cfg.name}: podcast name '{pod_name}' must start with a "
                        "letter or digit and contain only letters, digits, '.', '_' and '-' "
                        "(no '..')"
                    )
                    continue
                if pod_name in seen:
                    logger.error(
                        f"Skipping config {cfg.name}: podcast name '{pod_name}' is already "
                        f"used by {seen[pod_name].name}"
                    )
                    continue
                logger.debug(f"Found podcast config: {cfg.name}")
                seen[pod_name] = cfg
                configs.append((pod_name, cfg))
        return configs


class EpisodeManager:
    @staticmethod
    def discover_episodes(
        podcast_name: str,
        validated: Optional[PodcastChannelModel] = None,
    ) -> List[Episode]:
        pub_dir = Config.PUBLIC_ROOT / podcast_name
        if validated and validated.episodes:
            return [EpisodeManager._episode(ep, pub_dir / Path(ep.file).name) for ep in validated.episodes]

        if not pub_dir.exists():
            return []

        return [
            EpisodeManager._episode(EpisodeModel(file=media.name), media)
            for media in sorted(pub_dir.iterdir())
            if media.suffix.lower() in Config.MEDIA_TYPES and media.is_file()
        ]

    @staticmethod
    def _episode(model: EpisodeModel, path: Path) -> Episode:
        if model.pub_date is not None:
            return Episode(model, path, model.pub_date)
        try:
            mtime = path.stat().st_mtime
        except OSError:
            mtime = 0.0
        return Episode(model, path, datetime.fromtimestamp(mtime, tz=timezone.utc))

    @staticmethod
    def media_type(path: Path) -> str:
        return Config.MEDIA_TYPES.get(path.suffix.lower(), Config.DEFAULT_MEDIA_TYPE)

    @staticmethod
    def media_url(podcast_name: str, file_name: str) -> str:
        return f"{Config.BASE_URL}/{quote(podcast_name, safe='')}/{quote(file_name, safe='')}"

    @staticmethod
    def resolve_image_url(podcast_name: str, img: Optional[str]) -> Optional[str]:
        if not img:
            return None
        if img.startswith(("http://", "https://")):
            return img
        img_path = Config.PUBLIC_ROOT / podcast_name / Path(img).name
        if img_path.exists():
            logger.debug(f"Resolved image: {img_path.name}")
            return EpisodeManager.media_url(podcast_name, img_path.name)
        logger.warning(f"Image file not found: {img_path}")
        return None
