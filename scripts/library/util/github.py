from git import Repo
from pathlib import Path
import logging

# from libs.constants.folders import FOLDER_DOCS_RAG_SOURCES
import shutil

log = logging.getLogger(__name__)


# Fetch all metadata from the GitHub repository for the metadata repo
def fetch_data_from_gh_repo(
    repo_url: str,
    repo_source_path: str,
    repo_branch: str,
    target_path: Path,
):
    # delete target path if it exists
    if target_path.exists():
        log.info(f"Deleting {target_path}")
        shutil.rmtree(target_path)

    # create the target path
    target_path.mkdir(parents=True, exist_ok=True)

    repo = Repo.init(target_path)
    origin = repo.create_remote("origin", repo_url)

    origin.fetch()
    git = repo.git()
    git.checkout(f"origin/{repo_branch}", "--", repo_source_path)
    print(
        f"Copied folder '{repo_source_path}' from {repo_url} ({repo_branch} branch) to '{target_path}'"
    )
