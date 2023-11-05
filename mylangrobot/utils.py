import os
import platform

import requests
from tqdm import tqdm


def get_cache_directory(app_name: str) -> str:
    """Get cache directory path."""
    home = os.path.expanduser("~")

    if platform.system() == "Windows":
        base = os.environ.get("LOCALAPPDATA", home)
    elif platform.system() == "Darwin":
        base = os.path.join(home, "Library", "Caches")
    else:
        base = os.environ.get("XDG_CACHE_HOME", os.path.join(home, ".cache"))

    cache_dir = os.path.join(base, app_name)
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    return cache_dir


SAM_WEIGHTS_URL = "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth"


def download_sam_model_to_cache(app_name: str, url: str = SAM_WEIGHTS_URL) -> str:
    cache_dir = get_cache_directory(app_name)
    if os.path.exists(os.path.join(cache_dir, url.split("/")[-1])):
        return os.path.join(cache_dir, url.split("/")[-1])

    file_name = url.split("/")[-1]
    file_path = os.path.join(cache_dir, file_name)

    response = requests.get(url, stream=True)

    # Total size in bytes.
    total_size = int(response.headers.get("content-length", 0))
    block_size = 1024  # 1 Kibibyte
    progress_bar = tqdm(total=total_size, unit="iB", unit_scale=True)

    with open(file_path, "wb") as file:
        for data in response.iter_content(block_size):
            progress_bar.update(len(data))
            file.write(data)
    progress_bar.close()

    # Check if the whole file was downloaded
    if total_size != 0 and progress_bar.n != total_size:
        raise RuntimeError("Failed to download file")
    return file_path
