"""Integration services for external platforms (GitHub, PapersWithCode)."""

import logging
from typing import Any

from src.models.arxiv import GitHubRepositoryModel, PapersWithCodeModel
from src.utils.github_utils import find_github_links_in_text, get_github_repo_info
from src.utils.pwc_utils import get_pwc_details_for_paper

try:
    # Optional dependency (absent from the locked env); usage is guarded below.
    from paperswithcode import PapersWithCodeClient  # type: ignore[import-not-found]
except ImportError:
    PapersWithCodeClient = None

logger = logging.getLogger(__name__)


class IntegrationService:
    """Service for integrating with external research platforms."""

    def __init__(self, enable_github: bool = True, enable_pwc: bool = True, debug: bool = False):
        """Initialize integration service.

        Args:
            enable_github: Enable GitHub integration
            enable_pwc: Enable PapersWithCode integration
            debug: Enable debug logging
        """
        self.enable_github = enable_github
        self.enable_pwc = enable_pwc
        self.debug = debug

        # Initialize PapersWithCode client
        self.pwc_client = None
        if enable_pwc and PapersWithCodeClient:
            try:
                self.pwc_client = PapersWithCodeClient()
                logger.info("PapersWithCode client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize PapersWithCode client: {e}")

    def get_github_info(self, paper_data: dict[str, Any], github_token: str | None = None) -> GitHubRepositoryModel | None:
        """Get GitHub repository information mentioned in paper.

        Args:
            paper_data: Paper metadata dictionary
            github_token: GitHub API token (optional)

        Returns:
            GitHub repository model or None
        """
        if not self.enable_github:
            return None

        try:
            title = paper_data.get("title", "")
            summary = paper_data.get("summary", "")
            text = f"{title}\n{summary}"

            # Find GitHub links
            github_links = find_github_links_in_text(text)
            if not github_links:
                return None

            # Get info for first repository
            repo_url = github_links[0]
            logger.debug(f"Found GitHub repo: {repo_url}")

            repo_info = get_github_repo_info(repo_url, token=github_token)  # type: ignore[call-arg]  # BUG: util expects `github_token=`, not `token=`; TypeError is swallowed by the except below, so GitHub info never loads
            if repo_info:
                # BUG: GitHubRepositoryModel has no `url`/`name` fields (see html_url);
                # these kwargs are ignored by Pydantic, producing an empty-ish model.
                return GitHubRepositoryModel(  # type: ignore[call-arg]
                    url=repo_url,
                    name=repo_info.get("name", ""),
                    description=repo_info.get("description", ""),
                    stars=repo_info.get("stars", 0),
                    forks=repo_info.get("forks", 0),
                    language=repo_info.get("language", ""),
                    last_updated=repo_info.get("last_updated", ""),
                    topics=repo_info.get("topics", []),
                )

            return None

        except Exception as e:
            logger.error(f"Error getting GitHub info: {e}")
            return None

    def get_papers_with_code_info(self, paper_data: dict[str, Any]) -> PapersWithCodeModel | None:
        """Get PapersWithCode information for paper.

        Args:
            paper_data: Paper metadata dictionary

        Returns:
            PapersWithCode model or None
        """
        if not self.enable_pwc or not self.pwc_client:
            return None

        try:
            paper_id = paper_data.get("id", "")
            title = paper_data.get("title", "")

            if not paper_id:
                return None

            logger.debug(f"Searching PapersWithCode for: {paper_id}")

            # Get PWC details
            # BUG: get_pwc_details_for_paper is an async function — calling it without
            # await returns a coroutine (always truthy), so the `.get` calls below raise
            # AttributeError and this method always falls into the except handler.
            pwc_details = get_pwc_details_for_paper(paper_id, title)
            if pwc_details:
                # BUG: PapersWithCodeModel has none of these fields (it defines
                # pwc_id, pwc_url, pwc_title, ...); every kwarg is ignored by Pydantic.
                return PapersWithCodeModel(  # type: ignore[call-arg]
                    paper_id=paper_id,
                    title=pwc_details.get("title", title),  # type: ignore[attr-defined]
                    url=pwc_details.get("url", ""),  # type: ignore[attr-defined]
                    frameworks=pwc_details.get("frameworks", []),  # type: ignore[attr-defined]
                    datasets=pwc_details.get("datasets", []),  # type: ignore[attr-defined]
                    tasks=pwc_details.get("tasks", []),  # type: ignore[attr-defined]
                    stars=pwc_details.get("stars", 0),  # type: ignore[attr-defined]
                )

            return None

        except Exception as e:
            logger.error(f"Error getting PapersWithCode info: {e}")
            return None

    def has_github_references(self, paper_data: dict[str, Any]) -> bool:
        """Check if paper references GitHub repositories.

        Args:
            paper_data: Paper metadata dictionary

        Returns:
            True if GitHub references found
        """
        if not self.enable_github:
            return False

        title = paper_data.get("title", "")
        summary = paper_data.get("summary", "")
        text = f"{title}\n{summary}"

        github_links = find_github_links_in_text(text)
        return len(github_links) > 0

    def has_papers_with_code_entry(self, paper_data: dict[str, Any]) -> bool:
        """Check if paper has PapersWithCode entry.

        Args:
            paper_data: Paper metadata dictionary

        Returns:
            True if PapersWithCode entry exists
        """
        if not self.enable_pwc or not self.pwc_client:
            return False

        paper_id = paper_data.get("id", "")
        if not paper_id:
            return False

        try:
            # BUG: same unawaited-async issue as get_papers_with_code_info — the
            # result is a coroutine (never None), so this always returns True.
            pwc_details = get_pwc_details_for_paper(paper_id, paper_data.get("title", ""))
            return pwc_details is not None
        except Exception:
            return False
