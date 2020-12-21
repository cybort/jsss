from jsss.getGoogleDriveContents import getGDriveLargeContents
from pathlib import Path
from typing import Optional
import shutil

import fsspec
from fsspec.utils import get_protocol
from torchaudio.datasets.utils import extract_archive


def try_to_acquire_archive_contents(
    path_contents_local: Path,
    path_archive_local: Path,
    adress_archive: Optional[str],
    download: bool = False,
    gdrive_id: Optional[str] = None,
    file_size_GB: float = 0.
) -> bool:
    """
    Try to acquire the contents of the archive.
    Priority:
      1. (already extracted) local contents
      2. locally stored archive
      3. adress-specified (local|remote) archive through fsspec
    `gdrive_id` is hack for google drive archive.

    Returns:
        True if success_acquisition else False
    """
    # validation
    if path_contents_local.is_file():
        raise RuntimeError(f"contents ({str(path_contents_local)}) should be directory or empty, but it is file.")
    if path_archive_local.is_dir():
        raise RuntimeError(f"archive ({str(path_archive_local)}) should be file or empty, but it is directory.")

    if path_contents_local.exists():
        # contents directory already exists.
        return True
    elif path_archive_local.exists():
        extract_archive(str(path_archive_local), str(path_contents_local))
        return True
    else:
        if adress_archive:
            # validation for gdrive
            fs: fsspec.AbstractFileSystem = fsspec.filesystem(get_protocol(adress_archive))
            archiveExists = fs.exists(adress_archive)
            archiveIsFile = fs.isfile(adress_archive)

            if archiveExists and (not archiveIsFile):
                raise RuntimeError(f"Archive ({adress_archive}) should be file or empty, but it is directory.")

            if archiveExists and download:
                # A dataset file exist, so pull and extract.
                path_archive_local.parent.mkdir(parents=True, exist_ok=True)
                fs.get_file(adress_archive, path_archive_local)
                extract_archive(str(path_archive_local), str(path_contents_local))
                return True
            else:
                # no corresponding archive. Failed to acquire.
                return False
        else:
            # gdrive contents.
            # Archive file should exists.
            if download:
                if gdrive_id is None:
                    raise RuntimeError("`grive_id` should exist when `adress_archive` is `None`")
                getGDriveLargeContents(gdrive_id, path_archive_local, file_size_GB)
                extract_archive(str(path_archive_local), str(path_contents_local))
                return True
            else:
                return False


def save_archive(path_contents: Path, path_archive_local: Path, adress_archive: str) -> None:
    """
    Save contents as ZIP archive.

    Args:
        path_contents: Contents root directory path
        path_archive_local: Local path of newly generated archive file
        adress_archive: Saved adress
        compression: With-compression if True else no-compression
    """
    shutil.make_archive(str(path_archive_local.with_suffix("")), "zip", root_dir=path_contents)

    # write (==upload) the archive
    with open(path_archive_local, mode="rb") as stream_zip:
        with fsspec.open(f"simplecache::{adress_archive}", "wb") as f:
            f.write(stream_zip.read())
