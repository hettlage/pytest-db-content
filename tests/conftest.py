import pytest
import sqlite3

pytest_plugins = 'pytester'


SQLITE_URI_PROTOCOL = 'sqlite:///'


@pytest.fixture()
def sqlitedb(tmpdir):
    """
    Fixture for creating a simple SQLite test database.

    See the source code for the created tables. The table and column names are inconsistent on purposes, so that
    SQLAlchemy automapping naming can be tested.

    The database is populated with the same entries that are added when using the `populate` fixture.

    The URI of the created database is returned,

    Returns
    -------

    database_uri : str
        The database URI.

    """

    sqlite_file = str(tmpdir.join('tasks__TEST__.sqlite3'))

    connection = sqlite3.connect(sqlite_file)

    cursor = connection.cursor()
    cursor.execute('''
CREATE TABLE user (id INTEGER PRIMARY KEY,
                   first_name TEXT NOT NULL,
                   LastName TEXT NOT NULL)
''')
    cursor.execute('''
CREATE TABLE Tasks (id INTEGER NOT NULL,
                   userId INTEGER NOT NULL,
                   description TEXT NOT NULL,
                   priority INTEGER NOT NULL,
                   duration FLOAT NOT NULL,
                   done BOOLEAN NOT NULL,
                   due_date DATE NOT NULL,
                   due_time TIME NOT NULL,
                   reminder_due DATETIME NOT NULL,
                   PRIMARY KEY (id, userId))
''')
    connection.commit()

    yield SQLITE_URI_PROTOCOL + sqlite_file

    connection.close()


@pytest.fixture()
def sqlitepath(sqlitedb):
    """
    Fixture for the file path corresponding to the SQLite database URI ctreated by the sqlitedb fixture.

    Parameters
    ----------
    sqlitedb : str
        SQLite database URI.

    Returns
    -------
    path : str
        The file path.

    """

    return sqlitedb[len(SQLITE_URI_PROTOCOL):]  # omit the initial 'sqlite:///'


@pytest.fixture()
def dboption(sqlitedb):
    """
    Fixture for returning the command line option string which needs to be passed to the pytester `runpytest` function
    in order to specify the database URI.

    The option string is of the format `--database-uri=URI`, where `URI` denotes the database URI.

    Parameters
    ----------
    sqlitepath : str
        File path for the SQLite database.

    Returns
    -------
    option : str
        The option string.

    """

    return '--database-uri={}'.format(sqlitedb)


@pytest.fixture()
def populate(sqlitepath):
    """
    Fixture for dropping all table rows in the test database and repopulating the table with test entries.

    Parameters
    ----------
    sqlitedb : sqlitedb fixture
        The database fixture, i.e. the URI of the test database.

    Returns
    -------
    populate : func
        A function for repoulating the test database.

    """

    def _populate():
        _add_test_entries(sqlitepath)

    yield _populate


def _remove_all_entries(db_path):
    """
    Remove all entries from the test database tables.

    Parameters
    ----------
    db_path : str
        The file path of the test database.

    """

    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()
    cursor.execute('DELETE FROM user')
    cursor.execute('DELETE FROM Tasks')
    connection.commit()


def _add_test_entries(db_path):
    """
    Add some test data to the test database.

    Parameters
    ----------
    db_path : str
        The file path of the test database.

    """

    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()
    cursor.execute('''
INSERT INTO user (id, first_name, LastName)
       VALUES (1, 'Isaac', 'Newton')
    ''')
    cursor.execute('''
INSERT INTO user (id, first_name, LastName)
       VALUES (2, 'Albert', 'Einstein')
    ''')
    cursor.execute('''
INSERT INTO Tasks (id, userId, description, priority, duration, done, due_date, due_time, reminder_due)
       VALUES (1, 23, 'read book', 2, 5.5, 1, '2018-04-22', '17:13:08', '2018-04-24 12:00:00')
    ''')
    connection.commit()
