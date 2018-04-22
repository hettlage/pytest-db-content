Quickstart
==========

This quickstart uses a simple library for archiving books to illustrate how pytest-db-content can be used to facilitate tests that need a database. It assumes that you have already installed the pytest-db-content package.

Setting up the database
-----------------------

Create a new empty folder, go that folder, and create a SQLite database in a file `books.__TEST__.sqlite`.

.. code-block:: bash
   
   sqlite3 books.__TEST__.sqlite
   SQLite version 3.22.0 2018-01-22 18:45:57
   Enter ".help" for usage hints.
   sqlite> CREATE TABLE book (
      ...> id INT PRIMARY KEY,
      ...> genre_id INT NOT NULL,
      ...> author VARCHAR(50) NOT NULL,
      ...> title VARCHAR(50) NOT NULL,
      ...> pages INT NOT NULL,
      ...> publication_date DATE NOT NULL,
      ...> read BOOLEAN NOT NULL
      ...> );
   sqlite> CREATE TABLE genre (
      ...> id INT PRIMARY KEY,
      ...> name VARCHAR(50) NOT NULL
      ...> );
   sqlite> .exit

Don't add any content to the tables - it would be removed once we start testing.

Creating the book archive library
---------------------------------

The book archive library just consists of a class which just exposes a method for getting all the books for a genre. Copy the following Python code and save it as a file `book_archive.py`.

.. code-block:: python

   import sqlite3
   
   class BookArchive:
       """
       A simple book archive.
   
       Parameters
       ----------
       db_path : file path
           The file path to the database for this archive.
   
       """
   
       def __init__(self, db_path):
           self.connection = sqlite3.connect(db_path)
   
       def __del__(self):
           self.connection.close()
  
       def books(self, genre):
           """
           Return all the books for a genre.
   
           Parameters
           ----------
           genre : str
               The name of the genre.
   
           Returns
           -------
           books : list of dict
               A list of dictionaries with the column names and values.
   
           """
   
           cursor = self.connection.cursor()
   
           cursor.execute('''
   SELECT * FROM book
            WHERE genre_id=(SELECT id FROM genre WHERE name=?)
            ''', (genre,))
   
           return [row for row in cursor.fetchall()]

Also add a file `setup.py` with the following content.

.. code-block:: python
   
   from setuptools import setup
   
   setup(
       name='book_archive',
       py_modules=['book_archive']
   )

You can now install your shiny new book archive library with pip.

.. code-block:: bash
   
   pip install -e .

The `-e` option tells pip to save references to the code files rather than the code itself. This way the installed package is automatically kept up to date if you make changes to the source code.

Configuring the tests
---------------------

The table `genre` is a lookup table, which can change the same throughout all the tests. So we only have to create it once, before all the tests start. It thus makes sense to create it in a pytest fixture. This fixture gives us a first taste of the pytest-db-content plugin.

Create a new folder `tests` and a configuration file `tests/conftest.py` with the following code.

.. code-block:: python
   
   import pytest
   
   
   @pytest.fixture(scope='session', autouse=True)
   def genres(testdb):
       testdb.add_row('genre', id=1, name='novel')
       testdb.add_row('genre', id=2, name='biography')
       testdb.add_row('genre', id=3, name='science')

`testdb` is a session-scoped pytest fixture provided by pytest-db-content. It connects to the test database and offers various methods for accessing it. One of these is the `add_row` method shown in the above code, which (you've guessed it) adds a new row to a table. The table column names and values must be passed as keyword arguments. The (Python) type of the argument values should be the one corresponding ton the column type in the database.

Writing our first test
----------------------

.. info::
   
   This guide is *not* about testing. To keep things simple it will not test as extensively as you normally should. Maybe worse, it will also include tests that change the environment for subsequent tests, which is something you should avoid in real life.

Let's see whether pytest is happy with ourt code so far. Create a file `tests/test_book_archive.py` with the following test.

.. code-block:: python

   def test_sanity():
       """pytest is happy."""

       assert True

Run pytest with this file.

.. code-block:: bash

   pytest -v tests/

   ...

   E           ValueError: The db-content plugin requires the --database-uri command line option.

Oops. pytest fails with an error. That might make sense; we have to tell the tests what database to use, after all. The `--database-uri' command line option expects an URI which SQLAlchemy can understand. In our case, this will be something like `sqlite:///relative/path/to/db.` Let's give it a try.

.. code-block:: bash
   
   pytest -v --database-uri=sqlite:///books.sqlite tests/

   ...

   E           ValueError: The database URI passed with the --database-uri command line option must include the string '__TEST__'

Another error... The command line option requires the URI to contain the string `__TEST__`. This is a safety feature. pytest-db-content's `testdb` fixture removes all table rows before and after the test session, which is probably something you don't want to happen to your production database.

Luckily we included `__TEST__` in the filename of our database file earlier on; so let's see whether that does the trick.

.. code-block:: bash
   
   pytest -v --database-uri=sqlite:///books.__TEST__.sqlite
   
   ...
   
   tests/test_book_archive.py::test_sanity PASSED

Phew. That worked. Onward!

testdb's other methods
----------------------

For the fun of it, let us convince ourselves that the `genres` fixture really creates three rows in the genre table. We obviously can use Python's sqlite3 package to do this, which requires us to know the filename of the database. We can get this from the testdb fixture, as it exposes a database_uri property, whose value is whatever has been passed as the value for the `--database-uri` command line option.

Add the following code to `tests/test_book_archive.py`.

.. code-block:: python
   
   import sqlite3
   
   
   def test_genres_were_added(testdb):
       """There are three rows in the genre table."""
   
       db_path = testdb.database_uri.split('sqlite:///')[1]
       connection = sqlite3.connect(db_path)
   
       cursor = connection.cursor()
   
       cursor.execute('''
   SELECT COUNT(*) FROM genre
   ''')
       genre_count = cursor.fetchone()[0]
   
       assert genre_count == 3

We can shorten this test, though. `testdb` has a method `fetch_all`, which returns a list of dictionaries of columnh names and values. `fetch_all` requires the table name as its only parameter. Here is the rewritten test.

.. code-block:: python
   
   def test_genres_were_added(testdb):
       """There are three rows in the genre table."""
   
       genre_count = len(testdb.fetch_all('genre'))
   
       assert genre_count == 3

The order in which `fetch_all` returns the rows is undefined and must not be relied on. This is one of the reasons why you probably won't use it too often for checking table content, although (as the above test shows) it can be helpful if you only need to check the number of rows (or maybe just have one row in the table).

`testdb` also has a `clean` method, which removes all rows from one table or all tables, depending on whether you pass a table name it. Let's write a test to see it in action. This must come *after* the test functions we've previously written.

.. code-block:: python
   
   from datetime import date


   def test_cleaning_tables(testdb):
       """testdb's clean method removes table rows."""

       # add two books
       testdb.add_row('book', id=1, genre_id=1, author='Douglas Adams', title='Dirk Gently\'s Holistic Detective Agency', pages=288, publication_date=date(2012, 12, 6), read=True)
       testdb.add_row('book', id=2, genre_id=1, author='Terry Pratchett', title='The Colour of Magic', pages=288, publication_date=date(1990, 4, 1), read=False)

       # we have two books now, and there three genres
       assert len(testdb.fetch_all('book')) == 2
       assert len(testdb.fetch_all('genre')) == 3

       # gone with the genres
       testdb.clean('genre')

       # the books are still there, but the genres aren't
       assert len(testdb.fetch_all('book')) == 2
       assert len(testdb.fetch_all('genre')) == 0

       # add back a genre
       testdb.add_row('genre', id=1, name='novel')

       # yup, there is a genre now (and there are still two books)
       assert len(testdb.fetch_all('book')) == 2
       assert len(testdb.fetch_all('genre')) == 1

       # gone with everything
       testdb.clean()

       # nothing is left
       assert len(testdb.fetch_all('book')) == 0
       assert len(testdb.fetch_all('genre')) == 0

Looking at the two add_row calls for adding books you might think that we had to supply plenty of keyword arguments we weren't interested in really. At first sight that might seem necessary as all the columns in the book table are NOT NULL. But wouldn't it be nice if we nonetheless didn't have to do all this typing?

The good news is that indeed we don't have, apart from the primary keys. Any column you don't include in the keyword arguments will automatically be added by `add_row` with some default value. The method does its best to guess the correct data type to use. Missing columns are added irrespective of whether they can be NULL. So if you want to have NULL as a column value, you have to explicitly pass `None` with the keyword argument for the column; just omitting the keyword argument doesn't mean that NULL will be used as the column value.

For example, we can replace the first two `add_row` calls in the above ewith the following shorter version.

.. code-block:: python
   
   testdb.add_row('book', id=1)
   testdb.add_row('book', id=2)

The tmprow fixture
------------------

As the `testdb` fixture is session-scoped, so is its `add_row` method. Any rows you add with it will remain in the database until the end of all tests (unless you remove yourself before). While this may be of use for lookup tables, it usually is more convenient to remove added rows after a specific test function has finished. Test functions should start from well-defined (read: empty) table content.

This potential short-coming is addressed by the `tmprow` fixture. This works exactly as `add_row`, but it is function-scoped and any rows it adds are removed once a test function is done. You can see it in action by adding the following tests at the end `tests/test_book_archive.py`.

.. code-block:: python
   
   def test_persistent_or_temporary_part_1(testdb, tmprow):
    """add_row and tmprow add rows to a table."""
   
       # start from a clean slate
       testdb.clean('book')
   
       # add some books
       testdb.add_row('book', id=1)
       tmprow('book', id=2)
       tmprow('book', id=3)
       tmprow('book', id=4)
   
       # check the books are there now
       assert len(testdb.fetch_all('book')) == 4
   
   
   def test_persistent_or_temporary_part_2(testdb):
       """Rows added by test_row persist between test functions, rows added by tmprow do not."""
   
       # there is only one book left...
       assert len(testdb.fetch_all('book')) == 1
   
       # ... and it is the one added with the add_row method
       assert testdb.fetch_all('book')[0]['id'] == 1

As expected, the rows added with `tmprow` are deleted between these two tests, but the one added with `add_row` is not.

A cautionary tale regarding function-scope
------------------------------------------

So far we haven't written any test for our `BookArchive` class... Let's remedy the situation by adding the following test after akll the other tests.

.. code-block:: python
   
   import book_archive
   
   
   def test_books(testdb, tmprow):
       """The books method returns the correct books."""
   
       tmprow('book', id=1, genre_id=1, author='Richard Harris')
       tmprow('book', id=2, genre_id=2, author='Stephen Hawking')
       tmprow('book', id=3, genre_id=1, author='Zakes Mda')
   
       db_path = testdb.database_uri.split('sqlite:///')[1]
       archive = book_archive.BookArchive(db_path)
   
       novels = archive.books('novel')
       sorted_novels = sorted(novels, key=lambda book: book['id'])
   
       assert len(sorted_novels) == 2
       assert sorted_novels[0]['author'] == 'Richard Harris'
       assert sorted_novels[1]['author'] == 'Zakes Mda'

While this works fine and seeing the test is confidence-inspiring, it would be nice to test for more than one set of authors. We can do this by turning our test into a parametrised one.

.. info::
   
   Again, this guide is nbot about testing. In real life, you would also vary the number of books, genres etc.

.. code-block:: python
   
   import book_archive
   import pytest
   
   
   @pytest.mark.parametrize('authors',
                            [
                                ('Richard Harris', 'Stephen Hawking', 'Zakes Mda'),
                                ('Ayobami Adebayo', 'Marcus Chown', 'Chimamanda Ngozi Adichie')
                            ])
   def test_books(authors, testdb, tmprow):
       """The books method returns the correct books."""
   
       tmprow('book', id=1, genre_id=1, author=authors[0])
       tmprow('book', id=2, genre_id=2, author=authors[1])
       tmprow('book', id=3, genre_id=1, author=authors[2])
   
       db_path = testdb.database_uri.split('sqlite:///')[1]
       archive = book_archive.BookArchive(db_path)
   
       novels = archive.books('novel')
       sorted_novels = sorted(novels, key=lambda book: book['id'])
   
       assert len(sorted_novels) == 2
       assert sorted_novels[0]['author'] == authors[0]
       assert sorted_novels[1]['author'] == authors[2]

If you run pytest, the test passes without problems. But let's go one step further. Surely we should not limit ourselves to two sets of authors, we should cover edge cases like empty strings, and wec should include non-ASCII characters. Doing all this manually would be tedious and error prone. Instead we rewrite our test using `Hypothesis`, which was automatically installed when you installed `pytest-db-content`.

.. code-block:: python
   
   import book_archive
   from hypothesis import given
   from hypothesis.strategies import tuples, text
   
   
   @given(authors=tuples(text(max_size=50), text(max_size=50), text(max_size=50)))
   def test_books(authors, testdb, tmprow):
       """The books method returns the correct books."""
   
       tmprow('book', id=1, genre_id=1, author=authors[0])
       tmprow('book', id=2, genre_id=2, author=authors[1])
       tmprow('book', id=3, genre_id=1, author=authors[2])
   
       db_path = testdb.database_uri.split('sqlite:///')[1]
       archive = book_archive.BookArchive(db_path)
   
       novels = archive.books('novel')
       sorted_novels = sorted(novels, key=lambda book: book['id'])
   
       assert len(sorted_novels) == 2
       assert sorted_novels[0]['author'] == authors[0]
       assert sorted_novels[1]['author'] == authors[2]

Running pytest this time leads to a rude awakening - the test fails. A little digging in the copious error output lets you find the error message: `UNIQUE constraint failed: book.id` The problem is that we are trying to create books with idsa that exist ijn the database already. In other words, the rows we add with `tmprow` are *not* deleted between iterations done by Hypothesis. The `tmprow` fixture is set up before the first set of authors, but is only torn down after the last set of authors.

So when using Hypothesis, bear in mind that the same instance of a fixture is yused for all iterations. In our case that implies we have to do some manual cleaning up. Luckily, this is straightforward. Just replace the code

.. code-block:: python

       """The books method returns the correct books."""
   
       tmprow('book', id=1, genre_id=1, author=authors[0])

with

.. code-block:: python

       """The books method returns the correct books."""
   
       testdb.clean('book')
       tmprow('book', id=1, genre_id=1, author=authors[0])

After this change the test passes again.

What about real databases?
--------------------------

This quickstart guiode used a very simple SQLite database. Real databases can of course be much more complex. In particular, they might have foreign keys. These are of course crucial for ensuring database integrity, but they asre bad news for testing. Having to satisfy foreign key constraints can become onerous, and foreign keys may very well mean that SQLAlchemy's automapping functionality breaks down, so that pytest-db-content won't work.

For these reasons pytest-db-content ships with a script `create-test-database` which lets you create a test database free of foreign keys from a production database. Explaining this script is beyond the scope ofr this guide, but you may find more details in the Advanced section.