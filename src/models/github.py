"""GitHub repository and trending data models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import Field, field_validator

from .base import BaseModel, TimestampedModel


class TrendingPeriod(str, Enum):
    """Enum for GitHub trending periods."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class RepositoryLanguage(str, Enum):
    """Enum for supported programming languages.
    
    This enum supports all major programming languages that GitHub tracks.
    Values are normalized to lowercase with hyphens for consistency.
    """

    # Special categories
    ALL = "all"
    
    # Major programming languages
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    C = "c"
    CPP = "cpp"
    CSHARP = "csharp"
    GO = "go"
    RUST = "rust"
    PHP = "php"
    RUBY = "ruby"
    SWIFT = "swift"
    KOTLIN = "kotlin"
    SCALA = "scala"
    DART = "dart"
    R = "r"
    MATLAB = "matlab"
    PERL = "perl"
    LUA = "lua"
    HASKELL = "haskell"
    CLOJURE = "clojure"
    ELIXIR = "elixir"
    ERLANG = "erlang"
    F_SHARP = "fsharp"
    OBJECTIVE_C = "objective-c"
    
    # Web technologies  
    HTML = "html"
    CSS = "css"
    SCSS = "scss"
    SASS = "sass"
    LESS = "less"
    VUE = "vue"
    
    # Shell and scripting
    SHELL = "shell"
    BASH = "bash"
    POWERSHELL = "powershell"
    BATCH = "batchfile"
    
    # Data and config languages
    SQL = "sql"
    JSON = "json"
    YAML = "yaml"
    XML = "xml"
    TOML = "toml"
    INI = "ini"
    
    # Specialized languages
    JUPYTER_NOTEBOOK = "jupyter-notebook"
    CUDA = "cuda"
    HCL = "hcl"  # Terraform
    DOCKERFILE = "dockerfile"
    MAKEFILE = "makefile"
    CMAKE = "cmake"
    
    # Assembly and low-level
    ASSEMBLY = "assembly"
    WEBASSEMBLY = "webassembly"
    
    # Functional languages
    LISP = "lisp"
    SCHEME = "scheme"
    ML = "ml"
    OCAML = "ocaml"
    
    # Other notable languages
    FORTRAN = "fortran"
    COBOL = "cobol"
    ADA = "ada"
    PASCAL = "pascal"
    DELPHI = "delphi"
    VERILOG = "verilog"
    VHDL = "vhdl"
    
    @classmethod
    def from_github_language(cls, language: str | None) -> 'RepositoryLanguage':
        """Convert GitHub language string to RepositoryLanguage enum.
        
        Handles case-insensitive matching and common variations.
        Returns ALL if language is None or not recognized.
        """
        if not language:
            return cls.ALL
            
        # Normalize the language string
        normalized = language.lower().strip()
        
        # Direct mapping for common GitHub language variations
        language_map = {
            # Case variations
            "python": cls.PYTHON,
            "javascript": cls.JAVASCRIPT,
            "typescript": cls.TYPESCRIPT,
            "java": cls.JAVA,
            "c": cls.C,
            "c++": cls.CPP,
            "cpp": cls.CPP,
            "c#": cls.CSHARP,
            "csharp": cls.CSHARP,
            "go": cls.GO,
            "rust": cls.RUST,
            "php": cls.PHP,
            "ruby": cls.RUBY,
            "swift": cls.SWIFT,
            "kotlin": cls.KOTLIN,
            "scala": cls.SCALA,
            "dart": cls.DART,
            "r": cls.R,
            "matlab": cls.MATLAB,
            "perl": cls.PERL,
            "lua": cls.LUA,
            "haskell": cls.HASKELL,
            "clojure": cls.CLOJURE,
            "elixir": cls.ELIXIR,
            "erlang": cls.ERLANG,
            "f#": cls.F_SHARP,
            "fsharp": cls.F_SHARP,
            "objective-c": cls.OBJECTIVE_C,
            "objc": cls.OBJECTIVE_C,
            
            # Web technologies
            "html": cls.HTML,
            "css": cls.CSS,
            "scss": cls.SCSS,
            "sass": cls.SASS,
            "less": cls.LESS,
            "vue": cls.VUE,
            
            # Shell and scripting
            "shell": cls.SHELL,
            "bash": cls.BASH,
            "powershell": cls.POWERSHELL,
            "batchfile": cls.BATCH,
            "batch": cls.BATCH,
            
            # Data and config
            "sql": cls.SQL,
            "json": cls.JSON,
            "yaml": cls.YAML,
            "yml": cls.YAML,
            "xml": cls.XML,
            "toml": cls.TOML,
            "ini": cls.INI,
            
            # Specialized
            "jupyter notebook": cls.JUPYTER_NOTEBOOK,
            "jupyter-notebook": cls.JUPYTER_NOTEBOOK,
            "cuda": cls.CUDA,
            "hcl": cls.HCL,
            "terraform": cls.HCL,
            "dockerfile": cls.DOCKERFILE,
            "makefile": cls.MAKEFILE,
            "cmake": cls.CMAKE,
            
            # Assembly
            "assembly": cls.ASSEMBLY,
            "webassembly": cls.WEBASSEMBLY,
            "wasm": cls.WEBASSEMBLY,
            
            # Others
            "fortran": cls.FORTRAN,
            "cobol": cls.COBOL,
            "ada": cls.ADA,
            "pascal": cls.PASCAL,
            "delphi": cls.DELPHI,
            "verilog": cls.VERILOG,
            "vhdl": cls.VHDL,
        }
        
        # Try to find a match
        mapped_language = language_map.get(normalized)
        if mapped_language:
            return mapped_language
            
        # If no exact match, try to find enum member by value matching
        for member in cls:
            if member.value.lower() == normalized:
                return member
                
        # If still no match, return ALL (most permissive)
        return cls.ALL


class GitHubRepositoryOwner(BaseModel):
    """Model for GitHub repository owner information."""

    login: str = Field(description="Owner username")
    type: str = Field(description="Owner type (User/Organization)")
    html_url: str | None = Field(default=None, description="Owner profile URL")
    avatar_url: str | None = Field(default=None, description="Owner avatar URL")


class GitHubRepositoryModel(TimestampedModel):
    """Model for GitHub repository data from RSS feeds."""

    # Core repository info
    repository_id: int | None = Field(default=None, description="GitHub repository ID")
    name: str = Field(description="Repository name")
    full_name: str = Field(description="Full repository name (owner/repo)")
    description: str | None = Field(default=None, description="Repository description")
    html_url: str = Field(description="Repository URL")

    # Repository metadata
    language: str | None = Field(
        default=None, description="Primary programming language"
    )
    stars_count: int = Field(default=0, description="Number of stars")
    forks_count: int = Field(default=0, description="Number of forks")
    watchers_count: int = Field(default=0, description="Number of watchers")
    open_issues_count: int = Field(default=0, description="Number of open issues")

    # Repository settings
    default_branch: str | None = Field(default=None, description="Default branch name")
    topics: list[str] = Field(
        default_factory=list, description="Repository topics/tags"
    )
    license_name: str | None = Field(default=None, description="License name")
    size: int = Field(default=0, description="Repository size in KB")

    # Repository status
    archived: bool = Field(default=False, description="Whether repository is archived")
    disabled: bool = Field(default=False, description="Whether repository is disabled")
    has_wiki: bool = Field(default=False, description="Whether repository has wiki")
    has_pages: bool = Field(
        default=False, description="Whether repository has GitHub Pages"
    )
    has_downloads: bool = Field(
        default=False, description="Whether repository has downloads"
    )

    # Owner information
    owner: GitHubRepositoryOwner | None = Field(
        default=None, description="Repository owner"
    )

    # Timestamps
    repository_created_at: datetime | None = Field(
        default=None, description="Repository creation date"
    )
    repository_updated_at: datetime | None = Field(
        default=None, description="Repository last update date"
    )
    pushed_at: datetime | None = Field(default=None, description="Last push date")

    # Trending context
    trending_period: TrendingPeriod = Field(
        description="Trending period (daily/weekly/monthly)"
    )
    trending_language: RepositoryLanguage = Field(description="Language filter applied")

    # RSS feed metadata
    rss_title: str | None = Field(default=None, description="RSS feed entry title")
    rss_link: str | None = Field(default=None, description="RSS feed entry link")
    rss_published: datetime | None = Field(
        default=None, description="RSS entry publication date"
    )
    rss_summary: str | None = Field(
        default=None, description="RSS entry summary/description"
    )

    # Source tracking
    source: str = Field(
        default="github_trending_rss", description="Data source identifier"
    )
    source_url: str | None = Field(default=None, description="Original RSS feed URL")

    @field_validator("topics", mode="before")
    @classmethod
    def parse_topics(cls, v: Any) -> list[str]:
        """Parse topics from various formats."""
        if isinstance(v, str):
            # Handle comma-separated topics
            return [topic.strip() for topic in v.split(",") if topic.strip()]
        elif isinstance(v, list):
            return [str(topic).strip() for topic in v if str(topic).strip()]
        return []

    @field_validator("trending_language", mode="before")
    @classmethod
    def parse_trending_language(cls, v: Any) -> RepositoryLanguage:
        """Parse trending language from GitHub API response.
        
        Handles case-insensitive matching and converts GitHub language names
        to our normalized enum values.
        """
        if isinstance(v, RepositoryLanguage):
            return v
        if isinstance(v, str):
            return RepositoryLanguage.from_github_language(v)
        return RepositoryLanguage.ALL

    @field_validator(
        "repository_created_at",
        "repository_updated_at",
        "pushed_at",
        "rss_published",
        mode="before",
    )
    @classmethod
    def parse_datetime(cls, v: Any) -> datetime | None:
        """Parse datetime fields from various formats."""
        if v is None:
            return None

        if isinstance(v, datetime):
            return v

        if isinstance(v, str):
            # Try to parse ISO format datetime
            try:
                # Remove timezone suffix if present and parse
                if v.endswith("Z"):
                    v = v[:-1] + "+00:00"
                return datetime.fromisoformat(v.replace("Z", "+00:00"))
            except ValueError:
                # Try other common formats
                try:
                    return datetime.strptime(v, "%Y-%m-%dT%H:%M:%S")
                except ValueError:
                    try:
                        return datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        return None

        return None

    def get_trending_display_name(self) -> str:
        """Get display name for trending category."""
        period_map = {
            TrendingPeriod.DAILY: "Daily",
            TrendingPeriod.WEEKLY: "Weekly",
            TrendingPeriod.MONTHLY: "Monthly",
        }

        language_map = {
            RepositoryLanguage.ALL: "All Languages",
            RepositoryLanguage.PYTHON: "Python",
            RepositoryLanguage.JUPYTER_NOTEBOOK: "Jupyter Notebook",
            RepositoryLanguage.CUDA: "CUDA",
            RepositoryLanguage.HCL: "Terraform (HCL)",
        }

        period_name = period_map.get(self.trending_period, self.trending_period)
        language_name = language_map.get(self.trending_language, self.trending_language)

        return f"{period_name} - {language_name}"

    def to_dashboard_dict(self) -> dict[str, Any]:
        """Convert to dictionary suitable for dashboard display."""
        return {
            "id": self.id,
            "name": self.name,
            "full_name": self.full_name,
            "description": self.description or "No description available",
            "url": self.html_url,
            "language": self.language or "Unknown",
            "stars": self.stars_count,
            "forks": self.forks_count,
            "owner": self.owner.login if self.owner else "Unknown",
            "owner_type": self.owner.type if self.owner else "Unknown",
            "topics": self.topics,
            "license": self.license_name,
            "trending_category": self.get_trending_display_name(),
            "trending_period": self.trending_period,
            "trending_language": self.trending_language,
            "created_at": (
                self.repository_created_at.isoformat()
                if self.repository_created_at
                else None
            ),
            "updated_at": (
                self.repository_updated_at.isoformat()
                if self.repository_updated_at
                else None
            ),
            "fetched_at": self.created_at.isoformat(),
            "rss_published": (
                self.rss_published.isoformat() if self.rss_published else None
            ),
        }


class GitHubTrendingFeed(BaseModel):
    """Model for GitHub trending RSS feed configuration."""

    name: str = Field(description="Feed display name")
    url: str = Field(description="RSS feed URL")
    period: TrendingPeriod = Field(description="Trending period")
    language: RepositoryLanguage = Field(description="Programming language filter")
    description: str | None = Field(default=None, description="Feed description")

    def get_output_filename(self) -> str:
        """Get standardized output filename for this feed."""
        lang_part = self.language.replace("-", "_")
        return f"github_trending_{self.period}_{lang_part}.json"
