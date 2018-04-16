import os
import sqlite3
import pytest

# command line option

def test_help_message(testdir):
    """pytest's help message includes the --db-uri option."""

    result = testdir.runpytest('--help')

    result.stdout.fnmatch_lines([
        'db-content:',
        '*--db-uri=DB_URI*URI of the test database*'
    ])


def test_require_db_uri(testdir):
    """The testdb fixture requires the --db-uri option"""

    testdir.makepyfile("""
    def test_testdb(testdb):
        assert True
    """)

    result = testdir.runpytest()

    result.stdout.fnmatch_lines([
        'E*The db-content plugin requires*--db-uri*'
    ])
    result.assert_outcomes(error=1)


# testdb fixture


def test_testdb_available(testdir, tmpdir, dboption, sqlitedb):
    """pytest makes the testdb fixture available, and its value is the database URI."""

    testdir.makepyfile("""
    def test_testdb(testdb):
        assert testdb == '{db_uri}'
    """.format(db_uri=sqlitedb))

    result = testdir.runpytest(dboption)

    result.assert_outcomes(passed=1)


def test_testdb_starts_from_clean_slate(testdir, populate, dboption, sqlitepath):
    """The testdb fixture removes all table rows."""

    populate()
    assert _row_count(sqlitepath, 'user') > 0
    assert _row_count(sqlitepath, 'Tasks') > 0

    testdir.makepyfile('''
    def test_testdb(testdb):
        assert True
    ''')

    result = testdir.runpytest(dboption)

    print(result.stdout.str())
    print(result.stderr.str())

    assert _row_count(sqlitepath, 'user') == 0
    assert _row_count(sqlitepath, 'Tasks') == 0


def test_db_uri_must_include_test(testdir):
    """The --db-uri option must include the string '__TEST__'."""

    testdir.makepyfile("""
    def test_correct_db_uri(testdb):
        assert True
    """)

    result = testdir.runpytest('--db-uri=sqlite:////some/path/observations.sqlite')

    result.stdout.fnmatch_lines([
        'E*--db-uri*__TEST__*'
    ])
    result.assert_outcomes(error=1)


def test_error_for_invalid_db_uri(testdir):
    """There must be an error if there is a database connection error."""

    testdir.makepyfile('''
    def test_db_uri(testdb):
        assert True
    ''')

    result = testdir.runpytest('--db-uri=whatever__TEST__')

    result.assert_outcomes(error=1)

    result = testdir.runpytest('--db-uri=sqlite:////path/to/observations__TEST__.chsdfyj7rt4.sqlite')

    result.assert_outcomes(error=1)


def test_addrow_available(testdir):
    """pytest makes the addrow fixture available, and its value is a function."""

    testdir.makepyfile("""
    def test_addrow(addrow):
        assert callable(addrow)
    """)

    result = testdir.runpytest('--db-uri="..."')

    result.assert_outcomes(passed=1)


def test_cleantable_available(testdir):
    """pytest makes the addrow fixture available, and its value is a function."""

    testdir.makepyfile("""
    def test_cleantable(cleantable):
        assert callable(cleantable)
    """)

    result = testdir.runpytest('--db-uri="..."')

    result.assert_outcomes(passed=1)


def test_option_required(testdir):
    """pytest must be called with the --db-uri option if the testdb fixture is used."""

    testdir.makepyfile("""
    def test_testdb_used(testdb):
        assert True
    """)

    result = testdir.runpytest()

    result.stderr.fnmatch_lines([
        'E*called with the --db-uri option*'
    ])

    result.assert_outcomes(error=1)


def _row_count(db_path, table):
    """
    Get the number of rows in a table.

    Parameters
    ----------
    db_uri : str
        The database URI.
    table : str
        The table name.

    Returns
    -------
    count : int
        The number of rows in the table.

    """

    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()
    cursor.execute('SELECT COUNT(*) FROM `{}`'.format(table))
    return cursor.fetchone()[0]