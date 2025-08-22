""""""

import os
import re
import pandas as pd
from io import BytesIO
import pickle

from py2store.stores.local_store import RelativePathFormatStore, PickleStore


class imdict(dict):
    def __hash__(self):
        return id(self)

    def _immutable(self, *args, **kws):
        raise TypeError("object is immutable")

    __setitem__ = _immutable
    __delitem__ = _immutable
    clear = _immutable
    update = _immutable
    setdefault = _immutable
    pop = _immutable
    popitem = _immutable


def assert_dir_exists(dirpath):
    assert os.path.isdir(dirpath), f"directory doesn't exist: {dirpath}"  # decouple


def mk_dir_if_does_not_exist(dirpath):
    if not os.path.isdir(dirpath):
        os.mkdir(dirpath)


# TODO: Local file system assumed: Decouple
class Mall:
    def __init__(self, rootdir, store_spec):
        assert_dir_exists(rootdir)  # decouple
        pjoin = lambda path: os.path.join(rootdir, path)
        self._attrs = list()
        for attr, specs in store_spec.items():
            self._attrs.append(attr)
            func = specs["func"]
            args = specs.get("args", [])
            kwargs = specs.get("kwargs", {})
            fullpath = pjoin(attr)
            mk_dir_if_does_not_exist(fullpath)  # decouple
            setattr(self, attr, func(pjoin(attr), *args, **kwargs))

    def __repr__(self):
        attr_lens = list()
        for attr in self._attrs:
            attr_lens.append(f"{attr}: {len(getattr(self, attr))}")
        s = ", ".join(attr_lens)
        return s


def df_from_data_given_ext(data, ext, **kwargs):
    if ext.startswith("."):
        ext = ext[1:]
    if ext in {"xls", "xlsx"}:
        kwargs = dict({"index": False}, **kwargs)
        return pd.read_excel(data, **kwargs)
    elif ext in {"csv"}:
        kwargs = dict({"index_col": False}, **kwargs)
        return pd.read_csv(data, **kwargs)
    elif ext in {"tsv"}:
        kwargs = dict({"sep": "\t", "index_col": False}, **kwargs)
        return pd.read_csv(data, **kwargs)
    elif ext in {"json"}:
        kwargs = dict({"orient": "records"}, **kwargs)
        return pd.read_json(data, **kwargs)
    elif ext in {"html"}:
        kwargs = dict({"index_col": False}, **kwargs)
        return pd.read_html(data, **kwargs)[0]
    elif ext in {"p", "pickle"}:
        return pickle.load(data, **kwargs)
    else:
        raise ValueError(f"Don't know how to handle extension: {ext}")


class DfStore(RelativePathFormatStore):
    def __init__(self, path_format, ext_specs=None):
        super().__init__(path_format, read="b", write="b")
        if ext_specs is None:
            ext_specs = {}
        self.ext_specs = ext_specs

    def __getitem__(self, k):
        _, ext = os.path.splitext(k)
        if ext.startswith("."):
            ext = ext[1:]
        kwargs = self.ext_specs.get(ext, {})
        data = BytesIO(super().__getitem__(k))
        return df_from_data_given_ext(data, ext, **kwargs)


DFLT_MALL_FACTORY = Mall

DFLT_MALL_SPEC = imdict(
    {
        "raw_data": {"func": DfStore},
        "xy_data": {"func": PickleStore},
        "learners": {"func": PickleStore},
        "models": {"func": PickleStore},
    }
)


class InvalidMallName(ValueError):
    pass


class MallAccess:
    _p_valid_mall_name = re.compile(r"^\w.*")

    def __init__(self, rootdir, mall_spec=DFLT_MALL_SPEC, mk_mall=DFLT_MALL_FACTORY):
        assert_dir_exists(rootdir)  # decouple
        self.mk_mall = mk_mall
        self.rootdir = rootdir
        self.mall_spec = mall_spec
        self.pjoin = lambda path: os.path.join(rootdir, path)

    def get_mall(self, name):
        space_root = self.pjoin(name)
        mk_dir_if_does_not_exist(space_root)
        return self.mk_mall(space_root, self.mall_spec)

    @classmethod
    def is_valid_mall_name(cls, name: str) -> bool:
        return bool(cls._p_valid_mall_name.match(name))

    def __call__(self, name: str):
        if self.is_valid_mall_name(name):
            return self.get_mall(name)
        else:
            raise InvalidMallName(f"Invalid Mall name: {name}")


if __name__ == "__main__":

    df_store_test_data_dir = os.path.expanduser("~/odir/skdash/test_df_store/data")
    if os.path.isdir(df_store_test_data_dir):
        df_store = DfStore(df_store_test_data_dir)
        ref_df = None
        ref_k = None
        for k, v in df_store.items():
            if ref_df is None:
                ref_df = v
                ref_k = k
            else:
                try:
                    assert all(
                        v.sort_index(axis=1) == ref_df.sort_index(axis=1)
                    ), f"The df for {k} was different than that of {ref_k}"
                except Exception as e:
                    print(f"with {k}")
                    raise
