from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain.schema import Document
from pathlib import Path
from library.util.io import get_files_in_folder
import logging
from library.util.github import fetch_data_from_gh_repo
from library.constants.folders import FOLDER_DOCS_RAG_SOURCES


log = logging.getLogger(__name__)


# Load the documents from the GitHub repository
def load_docs_from_github(
    repo_url: str, repo_source_path: str, target_path: Path, glob_pattern: str = "*.md"
):
    tf_docs_all = []

    # Fetch the data from the GitHub repository of Terraform provider for SAP BTP
    repo_url = "https://github.com/SAP/terraform-provider-btp.git"
    repo_source_path = "docs"
    tf_source_path = Path(FOLDER_DOCS_RAG_SOURCES, "tf_provider_btp").resolve()
    fetch_data_from_gh_repo(
        repo_url=repo_url,
        repo_branch="main",
        repo_source_path=repo_source_path,
        target_path=tf_source_path,
    )

    files = get_files_in_folder(
        folder=Path(target_path, repo_source_path), glob_pattern=glob_pattern
    )

    for file in files:
        document = TextLoader(file_path=str(file)).load()
        tf_docs_all.extend(document)
    print(
        f"Loaded {len(tf_docs_all)} documents from the folder '{repo_source_path}' of the GitHub repo '{repo_url}'"
    )
    return tf_docs_all


# Split the docs into chunks
def split_docs_into_chunks(
    documents: list[Document], chunk_size: int = 500, chunk_overlap: int = 0
):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        add_start_index=True,
    )
    chunks = text_splitter.split_documents(documents)
    log.info(f"Split {len(documents)} documents into {len(chunks)} chunks.")

    return chunks


def load_docs(tf_source_path: Path, glob_pattern: str = "*.md"):
    tf_docs_all = []
    files = get_files_in_folder(folder=tf_source_path, glob_pattern=glob_pattern)
    for file in files:
        document = TextLoader(file_path=str(file)).load()
        tf_docs_all.extend(document)

    return tf_docs_all
