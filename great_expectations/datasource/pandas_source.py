import copy
import time
from six import string_types

import pandas as pd

from .datasource import Datasource
from .filesystem_path_generator import SubdirReaderGenerator
from .batch_generator import EmptyGenerator
from great_expectations.dataset.pandas_dataset import PandasDataset

from great_expectations.exceptions import BatchKwargsError


class PandasDatasource(Datasource):
    """
    A PandasDatasource makes it easy to create, manage and validate expectations on
    Pandas dataframes.

    Use with the SubdirReaderGenerator for simple cases.
    """

    def __init__(self, name="pandas", data_context=None, generators=None, **kwargs):
        if generators is None:
            # Provide a gentle way to build a datasource with a sane default,
            # including ability to specify the base_directory and reader_options
            base_directory = kwargs.pop("base_directory", "/data")
            reader_options = kwargs.pop("reader_options", {})
            generators = {
                "default": {
                    "type": "subdir_reader",
                    "base_directory": base_directory,
                    "reader_options": reader_options
                }
            }
        super(PandasDatasource, self).__init__(name, type_="pandas",
                                               data_context=data_context,
                                               generators=generators)
        self._build_generators()

    def _get_generator_class(self, type_):
        if type_ == "subdir_reader":
            return SubdirReaderGenerator
        elif type_ == "memory":
            return EmptyGenerator
        else:
            raise ValueError("Unrecognized BatchGenerator type %s" % type_)

    def _get_data_asset(self, data_asset_name, batch_kwargs, expectation_suite, **kwargs):
        batch_kwargs.update(kwargs)
        if "path" in batch_kwargs:
            reader_options = batch_kwargs.copy()
            path = reader_options.pop("path")  # We need to remove from the reader
            reader_options.pop("timestamp")    # ditto timestamp
            if path.endswith((".csv", ".tsv")):
                df = pd.read_csv(path, **reader_options)
            elif path.endswith(".parquet"):
                df = pd.read_parquet(path, **reader_options)
            elif path.endswith((".xls", ".xlsx")):
                df = pd.read_excel(path, **reader_options)
            else:
                raise BatchKwargsError("Unrecognized path: no available reader.",
                                       batch_kwargs)
        elif "df" in batch_kwargs and isinstance(batch_kwargs["df"], (pd.DataFrame, pd.Series)):
            df = batch_kwargs.pop("df")  # We don't want to store the actual dataframe in kwargs
        else:
            raise BatchKwargsError("Invalid batch_kwargs: path or df is required for a PandasDatasource",
                                   batch_kwargs)

        return PandasDataset(df,
                             expectation_suite=expectation_suite,
                             data_context=self._data_context,
                             data_asset_name=data_asset_name,
                             batch_kwargs=batch_kwargs)

    def build_batch_kwargs(self, *args, **kwargs):
        if len(args) > 0:
            if isinstance(args[0], (pd.DataFrame, pd.Series)):
                kwargs.update({
                    "df": args[0],
                    "timestamp": time.time()
                })
            elif isinstance(args[0], string_types):
                kwargs.update({
                    "path": args[0],
                    "timestamp": time.time()
                })
        else:
            kwargs.update({
                "timestamp": time.time()
            })
        return kwargs