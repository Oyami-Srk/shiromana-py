"""
This file provided class for media access
"""
from enum import Enum, unique
import datetime
import sqlite3


class Library:  # Placeholder
    pass


@unique
class MediaType(Enum):
    Image = 1
    Text = 2
    Audio = 3
    Video = 4
    Other = 10


class Media:
    id: int = None
    hash: str = None
    filename: str = None
    filesize: int = None
    caption: str = None
    time_add: str = None
    type: MediaType = None
    sub_type: str = None
    type_addition: str = None
    series_uuid: str = None
    series_no: int = None
    comment: str = None
    lib: Library = None
    detail: dict = None

    def __init__(self, lib: Library):
        self.lib = lib
        self.detail = {
            "Height": None,
            "Width": None,
            "Format": None,
            "DPI": None,
            "Rate": None,
            "Tags": None
        }

    def __str__(self):
        info = self.to_dict()
        ret_str = ""
        if info['caption'] is not None:
            ret_str = "Media Info -*- {} -*-:\n".format(info['caption'])
        else:
            ret_str = "Media Info:\n"
        ret_str += "Hash: {hash}\nFile name: {filename}\n".format(
            **info)
        ret_str += "Add Time: {}\n".format(
            datetime.datetime.fromisoformat(info['time_add']).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
        )
        ret_str += "Media Type: {}\n".format(info['type'].name)
        ret_str += "Media Size: {:.2f} KB\n".format(info['filesize'] / 1024)
        if info['sub_type'] is not None:
            ret_str += "Sub Type: {}\n".format(info['sub_type'])
        if info['type_addition'] is not None:
            ret_str += "Type addition: {}\n".format(info['type_addition'])
        if info['series_uuid'] is not None:
            ret_str += "Series UUID: {}\n".format(info['series_uuid'])
        if info['series_no'] is not None:
            ret_str += "Series NO: {}\n".format(info['series_no'])
        if info['comment'] is not None:
            ret_str += "Comment: {}\n".format(info['comment'])
        return ret_str

    def to_dict(self):
        return {
            "id": self.id,
            "hash": self.hash,
            "filename": self.filename,
            "filesize": self.filesize,
            "caption": self.caption,
            "time_add": self.time_add,
            "type": self.type,
            "sub_type": self.sub_type,
            "type_addition": self.type_addition,
            "series_uuid": self.series_uuid,
            "series_no": self.series_no,
            "comment": self.comment
        }

    @staticmethod
    def from_dict(d: dict, lib: Library):
        ret = Media(lib)
        ret.id = d['id']
        ret.hash = d['hash']
        ret.filename = d['filename']
        ret.filesize = d['filesize']
        ret.caption = d['caption']
        ret.type = d['type']
        ret.time_add = d['time_add']
        ret.sub_type = d['sub_type']
        ret.type_addition = d['type_addition']
        ret.series_uuid = d['series_uuid']
        ret.series_no = d['series_no']
        ret.comment = d['comment']
        return ret
