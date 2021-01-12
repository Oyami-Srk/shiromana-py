import os

LIBRARY_EXT = ".mlib"
METADATA_FN = "metadata.json"
DATABASE_FN = "index.db"
MEDIA_DATABASE_FN = "media.db"
SHARED_DATABASE_FN = "shared.db"
FINGERPRINT_FN = ".shiromana"
MEDIAS_FOLDER = "medias"
MEDIAS_HASH_LEVEL = 1
MEDIAS_FOLDER_MAX_FILES = 10000  # only for warning
HASH_ALGO = "MD5"
LOCKFILE = ".LOCK"


# Type is composed with MainType, SubType, TypeAddition
# Main Type is restricted


def acquire_lock(path: str) -> bool:
    if not os.path.exists(path):
        raise Exception("Not Exists")
    if os.path.exists(path + "/" + LOCKFILE):
        return False
    with open(path + "/" + LOCKFILE, "w") as f:
        f.write('')
    return True


def release_lock(path: str) -> bool:
    if not os.path.exists(path):
        raise Exception("Not Exists")
    if not os.path.exists(path + "/" + LOCKFILE):
        return False
    os.remove(path + "/" + LOCKFILE)
    return True
