"""
This file provides method to manage library of medias.
Library could be linked by connection (network or just local file).
"""
import os
import datetime
from uuid import uuid1 as __uuid1
import sqlite3
import json
import hashlib
import shutil
import random

import config
from media import Media, MediaType


def gen_uuid() -> str:
    return str(__uuid1(random.getrandbits(48) | 0x010000000000)).upper()


# master_name is abstract library's name. library set the same name
# could be linked together
def create_library(path: str, lib_name: str, master_name: str = "", local_name: str = ""):
    library_path = os.path.join(path, lib_name + config.LIBRARY_EXT)
    if os.path.exists(library_path):
        raise Exception("Already Exists")

    os.mkdir(library_path)
    library_uuid = gen_uuid()

    lib_metadata = {
        "UUID": library_uuid,
        "master_name": master_name,  # Abstract master library's name. Shared with all local library linked together
        "local_name": local_name,  # Local library's name. Used to manipulate library
        "library_name": lib_name,  # Local library's file name, Used to locate the library
        "summary": LibrarySummary().to_dict(),
        "schema": "Default"  # Implement for some custom folder structure.
    }

    cwd = os.getcwd()
    if not config.acquire_lock(library_path):
        raise Exception("Create failed: Lock cannot be acquired.")
    os.chdir(library_path)
    with open(config.METADATA_FN, "w") as f:
        json.dump(lib_metadata, f)

    conn_db = sqlite3.connect(config.DATABASE_FN)
    conn_db.executescript(
        """
        CREATE TABLE media(
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL UNIQUE,
            hash CHAR(32) NOT NULL UNIQUE,
            filename TEXT NOT NULL,
            caption TEXT,
            time_add TIMESTAMP NOT NULL DEFAULT(STRFTIME('%Y-%m-%d %H:%M:%f+00:00', 'NOW')),
            type INTEGER NOT NULL,
            sub_type CHAR(32),
            type_addition TEXT,
            series_uuid CHAR(36),
            series_no INTEGER,
            comment TEXT,
            FOREIGN KEY(series_uuid) REFERENCES series(uuid)
        );

        CREATE TABLE series(
           uuid CHAR(36) PRIMARY KEY NOT NULL UNIQUE,
           caption TEXT,
           media_count INTEGER,
           comment TEXT
        );

        CREATE TABLE library(
            uuid CHAR(36) PRIMARY KEY NOT NULL UNIQUE,
            path TEXT NOT NULL,
            comment TEXT
        );
        """
    )
    conn_db.commit()
    conn_db.execute(
        """
        INSERT INTO library (uuid, path) VALUES
        (?, ?)
        """,
        (library_uuid, os.getcwd())
    )
    conn_db.commit()
    conn_shared = sqlite3.connect(config.SHARED_DATABASE_FN)
    conn_media = sqlite3.connect(config.MEDIA_DATABASE_FN)
    with open(config.FINGERPRINT_FN, "w") as f:
        f.write(library_uuid)
    os.mkdir(config.MEDIAS_FOLDER)
    conn_db.close()
    conn_shared.close()
    conn_media.close()
    os.chdir(cwd)
    config.release_lock(library_path)


def open_library(path: str):
    if not os.path.exists(path):
        raise Exception("Not Exists")
    if not all(i in os.listdir(path) for i in
               [config.FINGERPRINT_FN, config.DATABASE_FN, config.MEDIA_DATABASE_FN, config.METADATA_FN,
                config.MEDIAS_FOLDER]):
        raise Exception("Not Library")

    if not config.acquire_lock(path):
        raise Exception("Open failed: Cannot acquire lock.")

    cwd = os.getcwd()
    os.chdir(path)

    library_metadata = {}
    with open(config.METADATA_FN, "r") as f:
        library_metadata = json.load(f)

    library_uuid = ""
    with open(config.FINGERPRINT_FN, "r") as f:
        library_uuid = f.read(36)
    if library_metadata['UUID'].strip() != library_uuid:
        raise Exception("UUID Mismatch")

    lib = Library()
    lib.path = path
    lib.library_name = library_metadata['library_name']
    lib.local_name = library_metadata['local_name']
    lib.master_name = library_metadata['master_name']
    lib.uuid = library_metadata['UUID']
    lib.schema = library_metadata['schema']
    lib.summary = LibrarySummary.from_dict(library_metadata['summary'])
    lib.index_db = sqlite3.connect(config.DATABASE_FN)
    os.chdir(cwd)
    return lib


class LibrarySummary:
    media_count = 0
    group_count = 0
    session_count = 0
    media_size = 0  # in kb

    def __init__(self):
        pass

    def to_dict(self) -> dict:
        return {
            "media_count": self.media_count,
            "group_count": self.group_count,
            "session_count": self.session_count,
            "media_size": self.media_size
        }

    @staticmethod
    def from_dict(d: dict):
        lib = LibrarySummary()
        lib.media_count = d['media_count']
        lib.group_count = d['group_count']
        lib.session_count = d['session_count']
        lib.media_size = d['media_size']
        return lib

    def __str__(self):
        return "Library Summary:\nMedia count: {}\nGroup count: {}\nSession count: {}\nMedia Size: {} KB\n".format(
            self.media_count, self.group_count, self.session_count, self.media_size)


class Library:
    index_db: sqlite3.Connection = None
    shared_db: sqlite3.Connection = None
    media_db: sqlite3.Connection = None
    path: str = None
    summary: LibrarySummary = LibrarySummary()
    uuid: str = None
    master_name: str = None
    local_name: str = None
    library_name: str = None
    schema: str = None

    def __init__(self):
        pass

    def __del__(self):
        self.index_db.commit()
        self.index_db.close()
        config.release_lock(self.path)

    def add_media(self, path: str, kind: MediaType, sub_kind: str = None, kind_addition: str = None, caption=None,
                  comment: str = None) -> int:
        """
        :param path: path to media indicated how to access media file
        :param kind: media type (use kind to avoid built-in name)
        :param sub_kind: media sub type
        :param kind_addition: type additional message
        :param caption: title of this media
        :param comment: media comment
        :return: integer for media id used for index media
        """
        kind = kind.value
        if not os.path.isfile(path):
            raise Exception("Not Exists or Not a File")
        with open(path, "rb") as f:
            file_hash = getattr(hashlib, config.HASH_ALGO.lower())(f.read()).hexdigest().upper()
        filename = os.path.basename(path)
        ext = os.path.splitext(path)[-1]
        new_path = file_hash[:2] + '/' + file_hash[2:] + ext
        new_path = self.path + '/' + config.MEDIAS_FOLDER + '/' + new_path
        if os.path.exists(new_path):
            raise Exception("Already Exists")
        os.makedirs(self.path + '/' + config.MEDIAS_FOLDER + '/' + file_hash[:2], exist_ok=True)
        shutil.copy(path, new_path)
        cur = self.index_db.cursor()
        cur.execute(
            """
            INSERT INTO media (hash, filename, caption, type, sub_type, type_addition, comment)
            VALUES (?,?,?,?,?,?,?);
            """,
            (file_hash, filename, caption, kind, sub_kind, kind_addition, comment)
        )
        ret_id = cur.lastrowid
        cur.close()
        self.index_db.commit()
        return ret_id

    def remove_media(self, id: int):
        """
        :param id: media id
        :return: None
        """
        cur = self.index_db.cursor()
        cur.execute(
            """
            SELECT hash, filename FROM media WHERE id = ?;
            """,
            (id,)
        )
        (file_hash, fn) = cur.fetchall()[0]
        ext = os.path.splitext(fn)[-1]
        fp = self.path + "/{}/{}/{}".format(config.MEDIAS_FOLDER, file_hash[:2], file_hash[2:] + ext)
        if not os.path.exists(fp):
            raise Exception("Fetal: Media stored in Database doesn't exist in filesystem")
        cur.execute(
            """
            DELETE FROM media WHERE id = ?;
            """,
            (id,)
        )
        cur.close()
        self.index_db.commit()
        os.remove(fp)

    def update_media(self, id: int, new: dict):
        """
        :param id: media id
        :param new: data to be updated, key is database's key
        :return: None
        """
        cur = self.index_db.cursor()
        for (key, value) in new.items():
            if key not in ["filename", "caption", "type", "sub_type", "type_addition", "comment"]:
                continue
            cur.execute(
                """
                UPDATE media
                SET {} = ?
                WHERE id = ?;
                """.format(key),
                (value, id)
            )
        cur.close()
        self.index_db.commit()

    def create_series(self, caption: str = "", comment: str = "") -> str:
        """
        :param caption: series' caption
        :param comment: series' comment
        :return: series' uuid
        """
        cur = self.index_db.cursor()
        uuid = gen_uuid()
        cur.execute(
            """
            INSERT INTO series (uuid, caption, comment, media_count)
            VALUES (?,?,?,?);
            """,
            (uuid, caption, comment, 0)
        )
        cur.close()
        self.index_db.commit()
        return uuid

    def delete_series(self, uuid: str):
        cur = self.index_db.cursor()
        cur.execute(
            """
            DELETE FROM series WHERE uuid = ?;
            """,
            (uuid,)
        )

    def add_to_series(self, media_id: int, series_uuid: str, media_no: int = None):
        cur = self.index_db.cursor()
        cur.execute(
            """
            SELECT series_no FROM media WHERE series_uuid = ? AND id != ?;
            """,
            (series_uuid, media_id)
        )
        other_no = [x[0] for x in cur.fetchall()]

        if media_no in other_no:
            cur.close()
            raise Exception("Media no occupied.")
        cur.execute(
            """
            UPDATE media
            SET series_uuid = ?, series_no = ?
            WHERE id = ?;
            """,
            (series_uuid, media_no, media_id)
        )
        cur.execute(
            """
            UPDATE series
            SET media_count = media_count + 1
            WHERE uuid = ?;
            """,
            (series_uuid,)
        )
        cur.close()
        self.index_db.commit()

    def remove_from_series(self, media_id: int):
        cur = self.index_db.cursor()
        cur.execute(
            """
            SELECT series_uuid FROM media WHERE id = ?;
            """,
            (media_id,)
        )
        series_uuid = cur.fetchall()[0][0]
        if len(series_uuid) != 36:
            cur.close()
            return
        cur.execute(
            """
            UPDATE media
            SET series_uuid = NULL, series_no = NULL
            WHERE id = ?;
            """,
            (media_id,)
        )
        cur.execute(
            """
            UPDATE series
            SET media_count = media_count - 1
            WHERE uuid = ?;
            """,
            (series_uuid,)
        )
        cur.close()
        self.index_db.commit()

    def update_series_no(self, media_id: int, media_no: int, insert: bool = False):
        cur = self.index_db.cursor()
        cur.execute(
            """
            SELECT series_uuid FROM media WHERE id = ?;
            """,
            (media_id,)
        )
        series_uuid = cur.fetchall()[0][0]
        if len(series_uuid) != 36:
            cur.close()
            raise Exception("Not add to series.")
        else:
            cur.execute(
                """
                SELECT series_no FROM media WHERE series_uuid = ? AND id != ?;
                """,
                (series_uuid, media_id)
            )
            other_no = [x[0] for x in cur.fetchall()]
            if media_no not in other_no:
                cur.execute(
                    """
                    UPDATE media SET series_no = ? WHERE id = ?;
                    """,
                    (media_no, media_id)
                )
            else:
                if not insert:
                    cur.close()
                    raise Exception("Media no occupied")
                # insert media no
                cur.execute(
                    """
                    UPDATE media
                    SET series_no = series_no + 1
                    WHERE series_uuid = ? AND series_no >= ?;
                    """,
                    (series_uuid, media_no)
                )
                cur.execute(
                    """
                    UPDATE media
                    SET series_no = ?
                    WHERE id = ?;
                    """,
                    (media_no, media_id)
                )

        cur.close()
        self.index_db.commit()

    def trim_series_no(self, series_uuid: str):
        """
        Dude, you should rarely use this function for the GOD's sake.
        """
        cur = self.index_db.cursor()
        cur.execute(
            """
            SELECT id, series_no FROM media WHERE series_uuid = ?;
            """,
            (series_uuid,)
        )
        id_no_list = [list(x) for x in cur.fetchall()]
        id_no_list.sort(key=lambda x: x[1])
        id_no_list[0][1] = 1
        for i in range(1, len(id_no_list)):
            id_no_list[i][1] = id_no_list[i - 1][1] + 1
        for (media_id, media_no) in id_no_list:
            cur.execute(
                """
                UPDATE media SET series_no = ? WHERE id = ?;
                """,
                (media_no, media_id)
            )
        cur.close()
        self.index_db.commit()

    def get_media(self, media_id: int) -> Media:
        cur = self.index_db.cursor()
        cur.execute(
            """
            SELECT * FROM media WHERE id = ?;
            """,
            (media_id,)
        )
        media = cur.fetchall()[0]
        cur.close()
        return Media.from_dict(
            {
                "hash": media[1],
                "filename": media[2],
                "caption": media[3],
                "time_add": media[4],
                "type": MediaType(media[5]),
                "sub_type": media[6],
                "type_addition": media[7],
                "series_uuid": media[8],
                "series_no": media[9],
                "comment": media[10]
            },
            self
        )

    def link_library(self):
        pass

    def unlink_library(self):
        pass

    def sync(self, master_table):
        pass

    def __str__(self):
        return """Library name: {}\nMaster name: {}\nLocal name: {}\nUUID: {}\nPath: {}\nschema: {}\n{}""".format(
            self.library_name,
            self.master_name,
            self.local_name,
            self.uuid,
            self.path,
            self.schema,
            str(self.summary)
        )
