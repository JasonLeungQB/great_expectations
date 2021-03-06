import os
import shutil

import pytest

from great_expectations import DataContext
from great_expectations.data_context.util import safe_mmkdir
from great_expectations.datasource import SqlAlchemyDatasource, Datasource
from great_expectations.exceptions import BatchKwargsError
from great_expectations.datasource.types import SqlAlchemyDatasourceQueryBatchKwargs
from great_expectations.datasource.generator import QueryGenerator


def test_basic_operation():
    # We should be able to include defined queries as part of configuration
    generator = QueryGenerator(
        queries={
            "my_asset": "SELECT * FROM my_table WHERE value = $condition",
            "my_simple_asset": "SELECT c1, c2 FROM my_table"
        }
    )

    # Returned assets should be typed and processed by template language
    batch_kwargs = generator.yield_batch_kwargs("my_asset", query_params={'condition': "foo"})
    assert isinstance(batch_kwargs, SqlAlchemyDatasourceQueryBatchKwargs)
    assert batch_kwargs.query == "SELECT * FROM my_table WHERE value = foo"

    # Without a template, everything should still work
    batch_kwargs = generator.yield_batch_kwargs("my_simple_asset")
    assert isinstance(batch_kwargs, SqlAlchemyDatasourceQueryBatchKwargs)
    assert batch_kwargs.query == "SELECT c1, c2 FROM my_table"

    # When a data asset is configured to require a template but it is not available, we should
    # fail with an informative message
    with pytest.raises(BatchKwargsError) as exc:
        generator.yield_batch_kwargs("my_asset")
        assert "missing template key" in exc.value.message


def test_add_query():
    generator = QueryGenerator()
    generator.add_query("my_asset", "select * from my_table where val > $condition")

    batch_kwargs = generator.yield_batch_kwargs("my_asset", query_params={"condition": 5})
    assert isinstance(batch_kwargs, SqlAlchemyDatasourceQueryBatchKwargs)
    assert batch_kwargs.query == "select * from my_table where val > 5"


def test_partition_id():
    generator = QueryGenerator(
        queries={
            "my_asset": "SELECT * FROM my_table WHERE value = $partition_id",
        }
    )

    batch_kwargs = generator.build_batch_kwargs_from_partition_id("my_asset", "foo")
    assert isinstance(batch_kwargs, SqlAlchemyDatasourceQueryBatchKwargs)
    assert batch_kwargs.query == "SELECT * FROM my_table WHERE value = foo"


def test_get_available_data_asset_names_for_query_path(empty_data_context):

    # create queries path
    context_path = empty_data_context.root_directory
    safe_mmkdir(os.path.join(context_path, "datasources/mydatasource/generators/mygenerator/queries"))
    shutil.copy("./tests/test_fixtures/dummy.sql", str(os.path.join(context_path, "datasources", "mydatasource",
                                                                    "generators", "mygenerator", "queries")))

    data_source = Datasource(name="mydatasource", data_context=empty_data_context)
    generator = QueryGenerator(name="mygenerator", datasource=data_source)
    sql_list = generator.get_available_data_asset_names()
    assert "dummy" in sql_list
