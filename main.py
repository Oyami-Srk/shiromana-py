import media_library
import os
import shutil
import config
from media import Media, MediaType

if __name__ == '__main__':
    shutil.rmtree("test.mlib", ignore_errors=True)
    lib = media_library.create_library(".", "test")
    del lib
    lib = media_library.open_library("test.mlib")
    print(lib)
    id_1 = lib.add_media("test/1.jpg", MediaType.Image)
    id_2 = lib.add_media("test/2.jpg", MediaType.Image)
    id_3 = lib.add_media("test/3.jpg", MediaType.Image)
    lib.remove_media(id_2)
    id_2 = lib.add_media("test/2.jpg", MediaType.Image)
    id_4 = lib.add_media("test/4.jpg", MediaType.Image)
    id_5 = lib.add_media("test/5.jpg", MediaType.Image)
    series_uuid = lib.create_series("Test", "for test")
    print("Create new series with uuid: " + series_uuid)
    lib.add_to_series(id_1, series_uuid, 1)
    lib.add_to_series(id_2, series_uuid, 6)
    lib.add_to_series(id_3, series_uuid)
    lib.update_media(id_3, {"caption": "test caption"})
    lib.update_series_no(id_3, 3, True)
    lib.trim_series_no(series_uuid)
    media = lib.get_media(id_4)
    print(media)
