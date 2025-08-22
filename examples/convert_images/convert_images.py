from PIL import Image  # To install: pip install Pillow
import pyheif  # To install: pip install pyheif
from py2store import LocalBinaryStore  # To install: pip install py2store
from io import BytesIO
import os

pjoin = os.path.join

from py2store import wrap_kvs


def to_image(k, v):
    if k.endswith('.heic'):
        v = pyheif.read_heif(BytesIO(v))
        return Image.frombytes(v.mode, v.size, v.data)
    else:
        b = BytesIO(v)
        b.name = k
        return Image.open(b)  # the loading


def image_bytes(k, v):
    b = BytesIO()
    b.name = k
    v.save(b)  # the saving
    b.seek(0)
    return b.read()


ImageStore = wrap_kvs(LocalBinaryStore, 'ImageStore', preset=image_bytes, postget=to_image)


def _extension_path_format(root, ext):
    if not ext.startswith('.'):
        ext = '.' + ext
    return pjoin(root, "{}" + ext)


import re


def convert_images(source_dir, target_dir=None, source_ext='.heic', target_ext='.jpg'):
    assert source_ext != target_ext
    source = ImageStore(_extension_path_format(source_dir, source_ext))
    target = ImageStore(_extension_path_format(target_dir or source_dir, target_ext))
    for source_k in source:
        target_k = re.sub(source_ext + '$', target_ext, source_k)
        assert target_k != source_k, f"same source and target key: {source_k}"
        print(f"{source_k} -> {target_k}")
        try:
            target[target_k] = source[source_k]
        except BaseException as e:
            print(f"!!! Problem with {source_k}: {e}")

if __name__ == '__main__':
    import argh  # To install: pip install argh
    argh.dispatch_command(convert_images)