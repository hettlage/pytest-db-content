# -*- coding: utf-8 -*-

import pytest
from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker


# This will be the SQLAlchemy Session class. It will be set by the testdb fixture.
Session = None

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
    A fixture for connecting to the database from a clean slate.

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
        pytestconfig fixture

    Returns
    -------
    db_uri : str
        The database URI.

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

    global Session
    Session = sessionmaker(bind=engine)

    _clean_database()

    yield db_uri


@pytest.fixture()
def addrow():
    def _addrow():
        return '42'

    yield _addrow


@pytest.fixture()
def cleantable():
    def _cleantable():
        return '42'

    yield _cleantable


def _clean_database():
    """
    Remove all the rows from all the tables in the test database.

    """

    session = Session()
    for orm_class in orm_classes.values():
        query = session.query(orm_class)
        query.delete()
        session.commit()
