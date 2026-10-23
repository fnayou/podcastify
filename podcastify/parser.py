import email.utils as eut
import logging
import re
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

    file: str
    title: Optional[str] = None
    description: Optional[str] = None
    summary: Optional[str] = None
    subtitle: Optional[str] = None
    pub_date: Optional[datetime] = None
    image: Optional[str] = None
    explicit: Optional[bool] = None
    author_name: Optional[str] = Field(None, alias="author-name")
    season: Optional[int] = None
    episode: Optional[int] = None
    episode_type: Optional[str] = None
    guid: Optional[str] = None
    duration_hms: Optional[str] = None

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

    name: Optional[str] = None
    title: str
    author_name: Optional[str] = Field(None, alias="author-name")
    author: Optional[str] = None
    author_email: Optional[str] = Field(None, alias="author-email")
    subtitle: Optional[str] = None
    summary: Optional[str] = None
    description: str
    language: Optional[str] = "en"
    explicit: Optional[bool] = False
    image: Optional[str] = None
    link: Optional[str] = None
    categories: Optional[Union[str, List[Any], Dict[str, Any]]] = None
    type: Optional[str] = None
    block: Optional[bool] = None
    complete: Optional[bool] = None
    new_feed_url: Optional[str] = None
    episodes: Optional[List[EpisodeModel]] = None

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


def validate_podcast_config(raw: Dict[str, Any]) -> Tuple[Optional[PodcastChannelModel], Optional[str]]:
    try:
        parsed = PodcastFileModel.model_validate(raw)
        channel = parsed.podcast
        if channel is None:
            return None, "missing podcast configuration"
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
    ) -> List[Dict[str, Any]]:
        pub_dir = Config.PUBLIC_ROOT / podcast_name
        eps = [ep.model_dump(by_alias=True) for ep in validated.episodes or []] if validated else []
        if eps:
            discovered: List[Dict[str, Any]] = []
            for e in eps:
                fname = Path(e.get("file", "")).name
                ep = dict(e)
                ep["__resolved_path"] = pub_dir / fname
                ep["__published"] = EpisodeManager._published(ep)
                discovered.append(ep)
            return discovered

        if not pub_dir.exists():
            return []

        discovered = []
        for media in sorted(pub_dir.iterdir()):
            if media.suffix.lower() not in Config.MEDIA_TYPES or not media.is_file():
                continue
            ep = {
                "file": media.name,
                "title": media.stem,
                "__resolved_path": media,
            }
            ep["__published"] = EpisodeManager._published(ep)
            discovered.append(ep)
        return discovered

    @staticmethod
    def _published(episode: Dict[str, Any]) -> datetime:
        pub_date = episode.get("pub_date")
        if isinstance(pub_date, datetime):
            return pub_date
        try:
            mtime = Path(episode["__resolved_path"]).stat().st_mtime
        except OSError:
            mtime = 0.0
        return datetime.fromtimestamp(mtime, tz=timezone.utc)

    @staticmethod
    def media_type(path: Path) -> str:
        return Config.MEDIA_TYPES.get(path.suffix.lower(), Config.DEFAULT_MEDIA_TYPE)

    @staticmethod
    def media_url(podcast_name: str, file_name: str) -> str:
        return f"{Config.BASE_URL}/{quote(podcast_name, safe='')}/{quote(file_name, safe='')}"

    @staticmethod
    def resolve_image_url(podcast_name: str, meta: Dict[str, Any]) -> Optional[str]:
        img = meta.get("image")
        if not img:
            return None
        if isinstance(img, str) and img.startswith(("http://", "https://")):
            return img
        img_path = Config.PUBLIC_ROOT / podcast_name / Path(img).name
        if img_path.exists():
            logger.debug(f"Resolved image: {img_path.name}")
            return EpisodeManager.media_url(podcast_name, img_path.name)
        logger.warning(f"Image file not found: {img_path}")
        return None
