import pytest


def test_testdb_available(testdir, testdb):
    """pytest makes the testdb fixture available, and its value is the database URI."""

    db_uri = 'whatever'

    testdir.makepyfile("""
    def test_testdb(testdb):
        assert testdb == '{db_uri}'
    """.format(db_uri=db_uri))

    result = testdir.runpytest('--db-uri={db_uri}'.format(db_uri=db_uri))

    result.assert_outcomes(passed=1)


def test_addrow_available(testdir, addrow):
    """pytest makes the addrow fixture available, and its value is a function."""

    testdir.makepyfile("""
    def test_addrow(addrow):
        assert callable(addrow)
    """)

    result = testdir.runpytest('--db-uri="..."')

    result.assert_outcomes(passed=1)


def test_cleantable_available(testdir, cleantable):
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
