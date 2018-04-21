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

The book archive library just consists of a class which exposes methods for adding a book, removing a book and getting the books for an author. Copy the following Python code and save it as a file `book_archive.py`.

.. code-block:: python

   import sqlite3
   
   class BookArchive:
       """
       A simple class for archiving books.
   
       Parameters
       ----------
       db_path : file path
           The file path to the database for this archive.
   
       """
   
       def __init__(self, db_path):
           self.connection = sqlite3.connect(db_path)
   
       def __del__(self):
           self.connection.close()
   
       def add_book(self, genre, author, title, pages, publication_date):
           """
           Add a book to the archive.
   
           Parameters
           ----------
           genre : str
               The name of the book genre.
           author : str
               The author.
           title : str
               The book title.
           pages : int
               The number of pages in the book.
           publication_date : datetime.date
               The date when the book was published.
   
           """
   
           cursor = self.connection.cursor()
   
           cursor.execute('SELECT id FROM genre WHERE genre=?', genre)
           genre_id = cursor.fetchone()[0]
   
           cursor.execute('''
   INSERT INTO book (genre_id, author, title, pages, publication_date)
               VALUES (?, ?, ?, ?, ?)
               ''', (genre_id, author, title, pages, publication_date))
           self.connection.commit()
   
       def books(self, genre):
           """
           Return all the books for a genre.
   
           Parameters
           ----------
           genre : str
               The name of the genre.
   
           Returns
           -------
           books : list of tuple
               A list of tuples with the column values.
   
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

We can shorten this test, though. `testdb` has a method `fetch_all`, which returns a list of tuples. Each of these tuples contains the column values of one of the table rows. `fetch_all` requires the table name as its only parameter. Here is the rewritten test.

.. code-block:: python
   
   def test_genres_were_added(testdb):
       """There are three rows in the genre table."""
   
       genre_count = len(testdb.fetch_all('genre'))
   
       assert genre_count == 3

The order in which `fetch_all` returns the rows is undefined and must not be relied on. This is one of the reasons why you probably won't use it too often for checking table content, although as the test shows it can be helpful if you only need to check the number of rows (or maybe just have one row in the table).

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

