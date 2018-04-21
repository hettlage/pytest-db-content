import os
import sqlite3
import pytest


# command line option


def test_help_message(testdir):
    """pytest's help message includes the --database-uri option."""

    result = testdir.runpytest('--help')

    result.stdout.fnmatch_lines([
        'db-content:',
        '*--database-uri=DATABASE_URI*'
    ])


def test_require_database_uri(testdir):
    """The testdb fixture requires the --database-uri option"""

    testdir.makepyfile('''
    def test_testdb(testdb):
        assert True
    ''')

    result = testdir.runpytest()

    result.stdout.fnmatch_lines([
        'E*The db-content plugin requires*--database-uri*'
    ])
    result.assert_outcomes(error=1)


# testdb fixture


def test_testdb_available(testdir, dboption):
    """pytest makes the testdb fixture available, and it has a non-null value."""

    testdir.makepyfile('''
    def test_testdb(testdb):
        assert testdb is not None
    ''')

    result = testdir.runpytest(dboption)

    result.assert_outcomes(passed=1)


def test_database_uri_must_include_test(testdir):
    """The --database-uri option must include the string '__TEST__'."""

    testdir.makepyfile('''
    def test_correct_database_uri(testdb):
        assert True
    ''')

    result = testdir.runpytest('--database-uri=sqlite:////some/path/observations.sqlite')

    result.stdout.fnmatch_lines([
        'E*--database-uri*__TEST__*'
    ])
    result.assert_outcomes(error=1)


def test_error_for_invalid_database_uri(testdir):
    """There must be an error if there is a database connection error."""

    testdir.makepyfile('''
    def test_database_uri(testdb):
        assert True
    ''')

    result = testdir.runpytest('--database-uri=whatever__TEST__')

    result.assert_outcomes(error=1)

    result = testdir.runpytest('--database-uri=sqlite:////path/to/observations__TEST__.chsdfyj7rt4.sqlite')

    result.assert_outcomes(error=1)


def test_testdb_starts_from_clean_slate(testdir, populate, dboption, sqlitepath):
    """The testdb fixture removes all table rows."""

    populate()
    assert _row_count(sqlitepath, 'user') > 0
    assert _row_count(sqlitepath, 'Tasks') > 0

    testdir.makepyfile('''
    def test_testdb(testdb):
        assert len(testdb.fetch_all('user')) == 0
        assert len(testdb.fetch_all('Tasks')) == 0
    ''')

    result = testdir.runpytest(dboption)

    result.assert_outcomes(passed=1)


# TestDatabase.database_uri


def test_test_db_has_database_uri(testdir, dboption, sqlitedb):
    """The test_db fixture has a database_uri field with the database URI."""

    testdir.makepyfile('''
    def test_testdb(testdb):
        assert testdb.database_uri == '{database_uri}'
    '''.format(database_uri=sqlitedb))

    result = testdir.runpytest(dboption)

    result.assert_outcomes(passed=1)


# TestDatabase.fetch_all


def test_fetch_all_invalid_table_name(testdir, dboption):
    """An error is raised if fetch_all is called with an invalid table name. """

    testdir.makepyfile('''
    def test_invalid_table_name(testdb):
        testdb.fetch_all('c56tyb')
    ''')

    result = testdir.runpytest(dboption)

    result.stdout.fnmatch_lines([
        'E*c56tyb is not a valid table name*'
    ])
    result.assert_outcomes(failed=1)


def test_fetch_all_returns_rows(testdir, dboption, sqlitepath):
    """TestDatabase.fetchAll returns all the rows of a table."""

    testdir.makepyfile("""
    from hypothesis import given
    import hypothesis.strategies as s
    import sqlite3
    
    
    @given(values=s.lists(s.tuples(s.from_regex(r'^[A-Za-z0-9]*$'), s.from_regex(r'^[A-Za-z0-9]*$'))))
    def test_user_content(values, testdb):
        # add unique id to Hypothesis-generated values
        inserted_rows = [(index + 1, row[0], row[1]) for index, row in enumerate(values)]
    
        connection = sqlite3.connect('{path}')
        cursor = connection.cursor()
    
        # delete any rows (just in case)
        cursor.execute('DELETE FROM user')
        cursor.execute('DELETE FROM Tasks')
        connection.commit()
    
        # add the Hypothesis generated data to the user table
        for row in inserted_rows:
            cursor.execute('''
            INSERT INTO user (id, first_name, LastName) VALUES ('{{id}}', '{{first_name}}', '{{last_name}}')
        '''.format(id=row[0], first_name=row[1], last_name=row[2]))
            connection.commit()
        
        # add one row to the Tasks table
        cursor.execute('''
        INSERT INTO Tasks (id, userId, description, priority, duration, done, due_date, due_time, reminder_due)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (1, 17, 'read', 1, 2.3, 0, '2000-01-01', '13:00:00', '2000-02-05 15:00:00'))
        connection.commit()
        
        # turn inserted user rows into dictionaries
        inserted_dicts = [{{'id': row[0], 'first_name': row[1], 'LastName': row[2]}} for row in inserted_rows]
     
        # use fetch_all to get the rows 
        fetched_rows = testdb.fetch_all('user')
       
        # compare inserted and fetched rows
        sorted_inserted_rows = sorted(inserted_dicts, key=lambda row: row['id'])
        sorted_fetched_rows = sorted(fetched_rows, key=lambda row: row['id'])
    
        assert sorted_fetched_rows == sorted_inserted_rows
    """.format(path=sqlitepath))

    result = testdir.runpytest(dboption)

    result.assert_outcomes(passed=1)


# TestData.add_row


def test_add_row_invalid_table_name(testdir, dboption):
    """An error is raised if TestDatabase.add_row is called with an invalid table name."""

    testdir.makepyfile('''
    def test_invalid_table_name(testdb):
        testdb.add_row('gh67ygt')
        
        assert True
    ''')

    result = testdir.runpytest(dboption)

    result.stdout.fnmatch_lines([
        'E*gh67ygt is not a valid table name*'
    ])
    result.assert_outcomes(failed=1)


def test_add_row_invalid_column_name(testdir, dboption):
    """An error is raised if TestDatabase.add_row is called with an invalid table name."""

    testdir.makepyfile('''
    def test_invalid_table_name(testdb):
        testdb.add_row('user', occupation='accountant')
    ''')

    result = testdir.runpytest(dboption)

    result.stdout.fnmatch_lines([
        'E*no column occupation in the table user*'
    ])
    result.assert_outcomes(failed=1)


def test_add_row_requires_primary_key_columns(testdir, dboption):
    """An error is raised if TestData.add_row is called without all primary key columns."""

    # id missing for user table

    testdir.makepyfile('''
    def test_one_primary_key_missing(testdb):
        testdb.add_row('user')
    ''')

    result = testdir.runpytest(dboption)

    result.stdout.fnmatch_lines([
        'E*following primary key column is missing*: id'
    ])
    result.assert_outcomes(failed=1)

    # userId missing for Tasks table

    testdir.makepyfile('''
    def test_one_primary_key_missing(testdb):
        testdb.add_row('Tasks', id=1)
    ''')

    result = testdir.runpytest(dboption)

    result.stdout.fnmatch_lines([
        'E*following primary key column is missing*: userId'
    ])
    result.assert_outcomes(failed=1)

    # id and userId missing for Tasks table

    testdir.makepyfile('''
    def test_one_primary_key_missing(testdb):
        testdb.add_row('Tasks')
    ''')

    result = testdir.runpytest(dboption)

    result.stdout.fnmatch_lines([
        'E*following primary key columns are missing*: id, userId'
    ])
    result.assert_outcomes(failed=1)


def test_add_row_adds_rows(testdir, dboption, sqlitepath):
    """TestDatabase.add_row adds a row to a table."""

    testdir.makepyfile("""
    from hypothesis import given
    import hypothesis.strategies as s
    import sqlite3
    
    
    @given(values=s.lists(s.tuples(s.from_regex(r'^[A-Za-z0-9]*$'), s.from_regex(r'^[A-Za-z0-9]*$'))))
    def test_user_content(values, testdb):
        # add unique id to Hypothesis-generated values
        inserted_rows = [(index + 1, row[0], row[1]) for index, row in enumerate(values)]
    
        connection = sqlite3.connect('{path}')
        cursor = connection.cursor()
    
        # delete any rows (just in case)
        cursor.execute('DELETE FROM user')
        cursor.execute('DELETE FROM Tasks')
        connection.commit()
    
        # add the Hypothesis generated data to the user table
        for row in inserted_rows:
            testdb.add_row('user', id=row[0], first_name=row[1], LastName=row[2])
        
        # turn inserted user rows into dictionaries
        inserted_dicts = [{{'id': row[0], 'first_name': row[1], 'LastName': row[2]}} for row in inserted_rows]
     
        # use fetch_all to get the rows 
        fetched_rows = testdb.fetch_all('user')
       
        # compare inserted and fetched rows
        sorted_inserted_rows = sorted(inserted_dicts, key=lambda row: row['id'])
        sorted_fetched_rows = sorted(fetched_rows, key=lambda row: row['id'])
    
        assert sorted_fetched_rows == sorted_inserted_rows
        assert len(testdb.fetch_all('Tasks')) == 0
    """.format(path=sqlitepath))

    result = testdir.runpytest(dboption)

    result.assert_outcomes(passed=1)


def test_add_row_adds_missing_columns(testdir, dboption, sqlitepath):
    """Missing non-primary key columns are added to a new table row."""

    testdir.makepyfile('''
    import datetime
    import sqlite3
    
    def test_missing_columns(testdb):
        connection = sqlite3.connect('{path}')
        cursor = connection.cursor()

        # delete any rows (just in case)
        cursor.execute('DELETE FROM Tasks')
        connection.commit()
    
        # add a new row
        testdb.add_row('Tasks', id=1, userId=2)
        
        # fetch the added row
        fetched_row = testdb.fetch_all('Tasks')[0]
        
        assert type(fetched_row['priority']) is int
        assert type(fetched_row['duration']) is float
        assert type(fetched_row['done']) is bool
        assert type(fetched_row['due_date']) is datetime.date
        assert type(fetched_row['due_time']) is datetime.time
        assert type(fetched_row['reminder_due']) is datetime.datetime
    '''.format(path=sqlitepath))

    result = testdir.runpytest(dboption)

    result.assert_outcomes(passed=1)


def test_add_row_persists_between_tests(testdir, dboption):
    """A table row added with TestData.add_row is not deleted after a test."""

    testdir.makepyfile('''
    def test_add_row_persists_part_one(testdb):
        # no rows in user table yet
        assert len(testdb.fetch_all('user')) == 0
        
        # add a row
        testdb.add_row('user', id=1)
        
        # yup, there is a row now
        assert len(testdb.fetch_all('user')) == 1
    
    def test_add_row_persists_part_two(testdb):
        # there still is the row from the previous test
        assert len(testdb.fetch_all('user')) == 1
    ''')

    result = testdir.runpytest(dboption)

    result.assert_outcomes(passed=2)


# TestDatabase.clean


def test_clean_invalid_table_name(testdir, dboption):
    """An error is raised if clean is called with an invalid table name."""

    testdir.makepyfile('''
    def test_invalid_table_name(testdb):
        testdb.clean('zxk67hi') 
    ''')

    result = testdir.runpytest(dboption)

    result.stdout.fnmatch_lines([
        'E*zxk67hi is not a valid table name*'
    ])
    result.assert_outcomes(failed=1)


def test_clean_removes_all_rows_in_a_table(testdir, dboption):
    """clean deletes all rows in a table if it is called with a table name."""

    testdir.makepyfile('''
    from hypothesis import given
    import hypothesis.strategies as s

    @given(user_count=s.integers(min_value=0, max_value=10), task_count=s.integers(min_value=0, max_value=10))
    def test_clean_deletes_all_rows_in_a_table(user_count, task_count, testdb):
        # testdb is not cleaned between successive tests, so we must do this ourselves
        testdb.clean()
        
        # set up initial database content
        for id in range(1, 1 + user_count):
            testdb.add_row('user', id=id)
        for id in range(1, 1 + task_count):
            testdb.add_row('Tasks', id=id, userId=id)
            
        # check the initial content
        assert len(testdb.fetch_all('user')) == user_count
        assert len(testdb.fetch_all('Tasks')) == task_count
        
        # delete all rows from the user table
        testdb.clean('user')
        
        # check the final content
        assert len(testdb.fetch_all('user')) == 0
        assert len(testdb.fetch_all('Tasks')) == task_count
    ''')

    result = testdir.runpytest(dboption)

    result.assert_outcomes(passed=1)


def test_clean_removes_all_rows_in_all_tables(testdir, dboption):
    """clean deletes all rows in all tables if it is called without a table name"""

    testdir.makepyfile('''
    from hypothesis import given
    import hypothesis.strategies as s

    @given(user_count=s.integers(min_value=0, max_value=10), task_count=s.integers(min_value=0, max_value=10))
    def test_clean_deletes_all_rows_in_a_table(user_count, task_count, testdb):
        # testdb is not cleaned between successive tests, so we must do this ourselves
        testdb.clean()
        
        # set up initial database content
        for id in range(1, 1 + user_count):
            testdb.add_row('user', id=id)
        for id in range(1, 1 + task_count):
            testdb.add_row('Tasks', id=id, userId=id)
            
        # check the initial content
        assert len(testdb.fetch_all('user')) == user_count
        assert len(testdb.fetch_all('Tasks')) == task_count
        
        # delete all rows from all tables
        testdb.clean()
        
        # check the final content
        assert len(testdb.fetch_all('user')) == 0
        assert len(testdb.fetch_all('Tasks')) == 0
    ''')

    result = testdir.runpytest(dboption)

    result.assert_outcomes(passed=1)


# tmprow


def test_tmprow_invalid_table_name(testdir, dboption):
    """An error is raised if tmprow is called with an invalid table name."""

    testdir.makepyfile('''
    def test_invalid_table_name(tmprow):
        tmprow('gh67ygt')
        
        assert True
    ''')

    result = testdir.runpytest(dboption)

    result.stdout.fnmatch_lines([
        'E*gh67ygt is not a valid table name*'
    ])
    result.assert_outcomes(failed=1)


def test_tmprow_invalid_column_name(testdir, dboption):
    """An error is raised if tmprow is called with an invalid table name."""

    testdir.makepyfile('''
    def test_invalid_table_name(tmprow):
        tmprow('user', occupation='accountant')
    ''')

    result = testdir.runpytest(dboption)

    result.stdout.fnmatch_lines([
        'E*no column occupation in the table user*'
    ])
    result.assert_outcomes(failed=1)


def test_tmprow_requires_primary_key_columns(testdir, dboption):
    """An error is raised if tmprow is called without all primary key columns."""

    # id missing for user table

    testdir.makepyfile('''
    def test_one_primary_key_missing(tmprow):
        tmprow('user')
    ''')

    result = testdir.runpytest(dboption)

    result.stdout.fnmatch_lines([
        'E*following primary key column is missing*: id'
    ])
    result.assert_outcomes(failed=1)

    # userId missing for Tasks table

    testdir.makepyfile('''
    def test_one_primary_key_missing(tmprow):
        tmprow('Tasks', id=1)
    ''')

    result = testdir.runpytest(dboption)

    result.stdout.fnmatch_lines([
        'E*following primary key column is missing*: userId'
    ])
    result.assert_outcomes(failed=1)

    # id and userId missing for Tasks table

    testdir.makepyfile('''
    def test_one_primary_key_missing(tmprow):
        tmprow('Tasks')
    ''')

    result = testdir.runpytest(dboption)

    result.stdout.fnmatch_lines([
        'E*following primary key columns are missing*: id, userId'
    ])
    result.assert_outcomes(failed=1)


def test_tmprow_adds_rows(testdir, dboption, sqlitepath):
    """tmprow adds a row to a table."""

    testdir.makepyfile("""
    from hypothesis import given
    import hypothesis.strategies as s
    import sqlite3
    
    @given(values=s.lists(s.tuples(s.from_regex(r'^[A-Za-z0-9]*$'), s.from_regex(r'^[A-Za-z0-9]*$'))))
    def test_user_content(values, testdb, tmprow):
        # add unique id to Hypothesis-generated values
        inserted_rows = [(index + 1, row[0], row[1]) for index, row in enumerate(values)]
     
        connection = sqlite3.connect('{path}')
        cursor = connection.cursor()
    
        # Rows added by tmprow are deleted only *after all Hypothesis-generated values have been tested*;
        # hence we have to manually delete any existing rows for each set of Hypothesis-generated parameters.
        cursor.execute('DELETE FROM user')
        cursor.execute('DELETE FROM Tasks')
        connection.commit()
    
        # add the Hypothesis generated data to the user table
        for row in inserted_rows:
            tmprow('user', id=row[0], first_name=row[1], LastName=row[2])
        
        # turn inserted user rows into dictionaries
        inserted_dicts = [{{'id': row[0], 'first_name': row[1], 'LastName': row[2]}} for row in inserted_rows]
     
        # use fetch_all to get the rows 
        fetched_rows = testdb.fetch_all('user')
       
        # compare inserted and fetched rows
        sorted_inserted_rows = sorted(inserted_dicts, key=lambda row: row['id'])
        sorted_fetched_rows = sorted(fetched_rows, key=lambda row: row['id'])
    
        assert sorted_fetched_rows == sorted_inserted_rows
        assert len(testdb.fetch_all('Tasks')) == 0
    """.format(path=sqlitepath))

    result = testdir.runpytest(dboption)

    result.assert_outcomes(passed=1)


def test_tmprow_adds_missing_columns(testdir, dboption, sqlitepath):
    """tmprow adds missing non-primary key columns to a new table row."""

    testdir.makepyfile('''
    import datetime
    import sqlite3
    
    def test_missing_columns(testdb, tmprow):
        connection = sqlite3.connect('{path}')
        cursor = connection.cursor()

        # delete any rows (just in case)
        cursor.execute('DELETE FROM Tasks')
        connection.commit()
    
        # add a new row
        tmprow('Tasks', id=1, userId=2)
        
        # fetch the added row
        fetched_row = testdb.fetch_all('Tasks')[0]
        
        assert type(fetched_row['priority']) is int
        assert type(fetched_row['duration']) is float
        assert type(fetched_row['done']) is bool
        assert type(fetched_row['due_date']) is datetime.date
        assert type(fetched_row['due_time']) is datetime.time
        assert type(fetched_row['reminder_due']) is datetime.datetime
    '''.format(path=sqlitepath))

    result = testdir.runpytest(dboption)

    result.assert_outcomes(passed=1)


def test_tmprow_does_not_persist_between_tests(testdir, dboption):
    """A table row added with tmprow is not deleted after a test."""

    testdir.makepyfile('''
    def test_tmprow_does_not_persist_part_one(testdb, tmprow):
        # no rows in user table yet
        assert len(testdb.fetch_all('user')) == 0
        
        # add a row which will persist between tests
        testdb.add_row('user', id=42)

        # add rows which will not be persisted
        tmprow('user', id=1)
        tmprow('user', id=2)
        tmprow('user', id=3)

        # yup, there are a four rows now
        assert len(testdb.fetch_all('user')) == 4

    def test_tmprow_does_not_part_two(testdb):
        # there is only one row left from the previous test, and it is the one added with add_row
        fetched_rows = testdb.fetch_all('user')
        assert len(fetched_rows) == 1
        assert fetched_rows[0]['id'] == 42
    ''')

    result = testdir.runpytest(dboption)

    result.assert_outcomes(passed=2)


def _row_count(db_path, table):
    """
    Get the number of rows in a table.

    Parameters
    ----------
    database_uri : str
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