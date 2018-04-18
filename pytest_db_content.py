# -*- coding: utf-8 -*-

from datetime import datetime, date, time
import pytest
from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import class_mapper, sessionmaker


# This will be the SQLAlchemy Session class. It will be set by the testdb fixture.
SessionClass = None

# This will be the dictionary of automapped SQLAlchemy ORM classes. It will be set by the testdb fixture.
orm_classes = None


def pytest_addoption(parser):
    group = parser.getgroup('db-content')
    group.addoption(
        '--db-uri',
        action='store',
        dest='db_uri',
        help='URI of the test database, in a format SQLAlchemy understands'
    )


@pytest.fixture(scope='session')
def testdb(pytestconfig):
    """
    A session-scoped fixture for connecting to the database from a clean slate.

    After the connection is established, all the rows of all the tables are deleted.

    The use of this fixtures requires that pytest was called with the --db-uri command line option. The URI for the
    database must be in a format SQLAlchemy understands. Example of valid URIs are

    `sqlite:///path/to/observations.sqlite3`

    or

    `mysql://observer:topsecret@my.server.org/observations`

    The database URI is returned as the fixture value.

    Parameters
    ----------
    pytestconfig : fixture
        The pytestconfig fixture.

    Returns
    -------
    db_uri : TestDatabase
        An object for accessing the test database.

    """

    db_uri = pytestconfig.getoption('db_uri', None)
    if not db_uri:
        raise ValueError('The db-content plugin requires the --db-uri command line option.')
    if '__TEST__' not in db_uri:
        raise ValueError('The database URI passed with the --db-uri command line option must include the string \'__TEST__\'')

    engine = create_engine(db_uri)

    Base = automap_base()
    Base.prepare(engine, reflect=True)
    global orm_classes
    orm_classes = Base.classes

    global SessionClass
    SessionClass = sessionmaker(bind=engine)

    yield TestDatabase(db_uri, SessionClass, orm_classes)


class TestDatabase:
    """
    Access to the test database used by the testdb fixture.

    Parameters:
    -------
    database_uri : str
        The URI of the test database.

    Session : class
        The class used for creating SQLAlchemy database sessions.

    orm_classes : dict like
        A dictionary-like object of table names and corresponding SQLAlchemy ORM classes.

    """

    def __init__(self, database_uri, Session, orm_classes):
        self._database_uri = database_uri
        self.Session = Session
        self.orm_classes = orm_classes

        self.clean()


    @property
    def database_uri(self):
        """
        The database URI, in a format understood by SQLAlchemy.

        Returns
        -------
        uri : str
            The database URI.

        """

        return self._database_uri

    def fetch_all(self, table):
        """
        Fetch all rows from a table.

        The table rows are returned as a list of dictionaries, where each dictionary consists of the column names and
        values for a row. The order of the dictionaries in this list is undefined and must not be relied on.

        The `table` parameter must be the name of an existing table.

        For example, assume a table Book has the following content.

        ====  ========  =======
        id    item      price
        ====  ========  =======
        1     ball      15.30
        2     book      21.00
        3     bottle    11.32
        ====  ========  =======

        Then `fetch_all('Book')` returns the a list of dictionaries `{'id': 1, 'item': 'ball', 'price': 15.30}`,
        `{'id': 2, 'item': 'book', 'price': 21.00}` and `{'id': 3, 'item': 'bottle', 'price': 11.32}`, in any order.

        Parameters:
        -----------
        table : str
            The name of the table whose rows are fetched.

        Returns
        -------
        rows : list of dict
            All the table rows as dictionaries of column names abd values.

        """

        if table not in self.orm_classes:
            raise ValueError('{} is not a valid table name.'.format(table))

        session = self.Session()
        orm_class = self.orm_classes[table]

        column_names = class_mapper(orm_class).columns.keys()

        return [{column: getattr(o, column) for column in column_names} for o in session.query(orm_class)]

    def add_row(self, table, **kwargs):
        """
        Add a row to a table in the test database.

        This function expects the name of the table as the first parameter. All other parameters must be column names
        of that table, and the parameter values are taken as the corresponding column values.

        If a non-primary key column name is not included in the parameters the data type of the column is used to make
        a judicious guess as to what should be an appropriate value, and that value is assigned. These values are not
        random, and the same value may be re-used several times. Hence you should not omit columns which have, or form
        part of, a uniqueness constraint.

        All primary key columns must be included among the parameters, a failure to do results in an error.

        Contrary to rows added with the `tmprow` fixture, a table row added with this method will not be deleted
        between tests within a pytest session.

        Parameters
        ----------
        table : str
            The name of the table to which the row is added.
        kwargs : keyword arguments
            The column values for the added row.

        """

        _add_row(table, kwargs, self.orm_classes, self.Session())

    def clean(self, table=None):
        """
        Remove all rows from one or all tables.

        If a valid table name is passed, the rows ofd thaty table are deleted. If no table name is passed the rows of
        all tables are deleted.

        An error is raised if an invalids table name is passed.

        Parameters
        ----------
        table : str, optional
            The name of the table whose rows are deleted.

        """

        # get the tables to clean
        if table:
            if table not in orm_classes:
                raise ValueError('{} is not a valid table name.'.format(table))
            cleaned_tables = [table]
        else:
            cleaned_tables = orm_classes.keys()

        # delete all rows
        session = self.Session()
        for cleaned_table in cleaned_tables:
            orm_class = orm_classes[cleaned_table]
            session.query(orm_class).delete()
        session.commit()


@pytest.fixture(scope='function')
def tmprow(testdb):
    """
    A fixture for adding a temporary row to a table in the test database.

    `tmprow` returns a function which expects the name of the table as the first parameter. All other parameters must
    be column names of that table, and the parameter values are taken as the corresponding column values.

    If a non-primary key column name is not included in the parameters the data type of the column is used to make
    a judicious guess as to what should be an appropriate value, and that value is assigned. These values are not
    random, and the same value may be re-used several times. Hence you should not omit columns which have, or form
    part of, a uniqueness constraint.

    All primary key columns must be included among the parameters, a failure to do results in an error.

    Contrary to rows added with the `add_row` method of a `TestData` instance, a table row added with this method
    will be deleted after a test function is finished.

    Parameters
    ----------
    testdb : fixture
        The testdb fixture.

    Returns
    -------
    tmprow : func
        A function for adding a table row.

    """

    rows = []
    session = testdb.Session()

    def _tmprow(table, **kwargs):
        # add the row and store it, so that it can be deleted later
        rows.append(_add_row(table, kwargs, testdb.orm_classes, session))

    yield _tmprow

    # delete all rows, in the reverse order of how they were added
    # (reversing the order should take care of foreign key constraints)
    for row in reversed(rows):
        session.delete(row)
    session.commit()


def _add_row(table, column_values, orm_classes, session):
    """
    Add a row to a table.

    See the documentation of TestDatabase.add_row or of the tmprow fixture for more details.

    Parameters
    ----------
    table : str
        The name of the table to which the row is added.
    column_values : dict
        A dictionary of column names and values.
    orm_classes : dict-like
        The table names and corresponding SQLAlchemy ORM classes.
    session : Session
        The SQLAlchemy session to use.

    Returns
    -------
    row : SQLAlchemy ORM object
        An ORM object representing the new row.

    """

    # check that the table name exists
    if table not in orm_classes:
        raise ValueError('{} is not a valid table name.'.format(table))

    # copy the given column values, as we might have to modify the dictionary
    columns = {key: column_values[key] for key in column_values}

    # check that all column names actually exist
    orm_class = orm_classes[table]
    table_column_names = class_mapper(orm_class).columns.keys()
    for column_name in columns:
        if column_name not in table_column_names:
            raise ValueError('There is no column {column} in the table {table}'.format(column=column_name, table=table))

    # add missing columns (other than primary keys)
    primary_keys = [primary_key.name for primary_key in inspect(orm_class).primary_key]
    missing_primary_keys = []
    for column_name in table_column_names:
        if column_name not in columns:
            if column_name not in primary_keys:
                columns[column_name] = _default_value(orm_class, column_name)
            else:
                missing_primary_keys.append(column_name)

    # no primary key must be missing
    if len(missing_primary_keys) > 0:
        if len(missing_primary_keys) == 1:
            error = 'The following primary key column is missing: '
        else:
            error = 'The following primary key columns are missing: '
        error += ', '.join(sorted(missing_primary_keys))
        raise ValueError(error)

    # create the table row
    row = orm_class(**columns)
    session.add(row)
    session.commit()

    return row


def _default_value(orm_class, column_name):
    python_type = inspect(orm_class).columns[column_name].type.python_type

    if python_type is bool:
        return False

    if python_type in [int, float]:
        return 1

    if python_type is datetime:
        return datetime(2000, 1, 1, 0, 0, 0, 0)

    if python_type is date:
        return date(2000, 1, 1)

    if python_type is time:
        return time(0, 0, 0, 0)

    return 'A'
