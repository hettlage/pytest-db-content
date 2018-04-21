.. toctree::
   :maxdepth: 2

pytest-db-content
=================

Introduction
------------

A key concept with unit tests is that tests should not pollute the environment; every test should start from a clean slate. When testing with a database this would mean that ideally the database is created before each test and dropped after every test.

This can be problematic, in particular if there are many tables in the database. So, as a compromise, it may make more sense to keep the database and its table structure, but to drop any table content before and after testing. However, even if the database isn't constantly re-created, its data should be. Each individual test function should be responsible for populating the database and cleaning up after it.

To do this manually would be a tedious and error-prone task. The pytest-db-content package aims to provide a solution which mames this task as straightforward as possible while still maintaining maximum flexibility.

*Disclaimer:* The command `create-test-db` mentioned below is solely provided for convenience, and while it is discussed in this specification, it does not form part of it.

Conceptual Solution
-------------------

pytest-db-content is a plugin for `pytest http://pytest.readthedocs.io/en/latest/`_, which offers two fixtures and a utility command.

testdb
++++++

The `testdb` fixture, which is session scoped, creates a database connection and deletes the rows of all database tables when it is called. All table entries are deleted again and the database connection is closed when the session is finished. The tables themselves are neither created nor dropped by the fixture

The database URI must be provided as a command line option, `--db-uri`, and it must have a format understood by SQLAlchemy.

The database URI must include the string `__TEST__`. This requirement is made in order to avoid connecting to a production database. A meaningful error must be raised if the databasename does not meet this condition.

The `testdb` returns a `TestDatabase` object.

TestDatabase object
+++++++++++++++++++

A `TestDatabase` object, which is returned by the `testdb` fixture, has the following fields and methods.

database_uri
~~~~~~~~~~~~

A string containing the database URI.

add_row(table, **kwargs)
~~~~~~~~~~~~~~~~~~~~~~~~

A function which adds a new row to a table. `table` is a string and must be a valid table name. The keyword arguments must be column names and values for the table. The spelling must match exactly that of the column names in the database.

If a non-primary key table column is missing from the keyword arguments, the method must try to add an appropriate value for the column, based on its type. If a primary key is missing a meaningful error must be raised.

A meaningful error must also be raised if an invalid tablename or column name is used, or if a column value is invalid.

fetch_all(table)
~~~~~~~~~~~~~~~~

A function which returns a list of all the table rows. Each row is a tuple of column values. The order of the rows within the returned list is arbitrary. In particular, there is no guarantee that the rows are ordered by their primary key.

clean(table=None)
~~~~~~~~~~~~~~~~~

A function which removes all rows from tables. If a table is given, only the rows for this table are deleted. Otherwise the rows of all tables are deleted.

tmprow
++++++

The `tmprow` fixture, which is function-scoped, lets the user add a row to a table in the test database. This row is deleted after the current test is completed. So in general you should prefer this fixture over the `add_row` method of the `testdb` fixture.

The fixture returns a function with the following signature.

::
   tmprow(table, **kwargs)

`table` is a string and must be a valid table name. The keyword arguments must be valid column names and values for that table.

If a non-primary key table column is missing from the keyword arguments, the method must try to add an appropriate value for the column, based on its type. If a primary key is missing a meaningful error must be raised.

A meaningful error must also be raised if an invalid tablename or column name is used, or if a column value is invalid.

`tmprow` uses the `testdb` fixture, so there is no need to explicitly include the latter if you only need to add temporary rows.

create-test-db
++++++++++++++

The `create-test-db` command creates a new MySQL database and adds the table structure of another MySQL database to it. It then removes all foreign key constraints for the newly created tables.       

The command has the following command line options.

===================  ===============================================  =========
Option               Description                                      Default  
===================  ===============================================  =========
--force              Remove the test database if it exists already    False    
--source-host        Host server for the source database            
--source-port        Port for the source database                     3306     
--source-db          Source database                                
--source-username    Username for accessing the source database     
--source-password    Password for accessing the source database     
--target-host        Host server for the created database           
--target-port        Port for the created database                    3306     
--target-db          Created test database                          
--target-username    Username for accessing the test database       
--target-password    Password for accessing the test database       
===================  ===============================================  =========

The name of the target database must contain the string `__TEST__`. It is assumed that UTF-8 is used as the encoding.

Tests
-----

The plugin must

* Expose a `testdb` and `tmprow` fixture.
* Add a command line option group with an option `--db-uri`.
* Raise an error if the `--database-uri` option value does not contain the string `__TEST__`.

The `testdb` fixture must

* Raise an error if the `--db-uri` option has not been used.
* Raise an error if the `--db-uri` option value does not contain the string `__TEST__`.
* Raise an error if it cannot connect to the database.
  
The `TestDatabase.database_uri` field must

* Be a string containing the database URI.
  
The `TestDatabase.add_row` method must

* Create a new table row with the given values if called with a valid table name and valid column names and values.
* Create a new table row even if not all required columns are passed.
* Not delete the added table row after a test is finished.
* Raise a meaningful error if an invalid table name is passed.
* Raise a meaningful error if an invalid column name is passed.
* Raise a meaningful error if an invalid column value is passed.
  
The `TestDatabase.fetch_all` method must

* Return a list of all the table rows for a given table name.
* Raise a meaningful error if an invalid table name is passed.

The `TestDatabase.clean` method must

* Delete all table rows for a table if it is called with a valid table name.
* Not delete rows from other tables if it is called with a valid table name.
* Delete all rows from all tables if it is called without a table name.
* Raise a meaningful error if an invalid table name is passed.

The `tmprow` fixture must

* Create a new table row with the given values if called with a valid table name and valid column names and values.
* Create a new table row even if not all required columns are passed.
* Delete the added table row after a test is finished.
* Raise a meaningful error if an invalid table name is passed.
* Raise a meaningful error if an invalid column name is passed.
* Raise a meaningful error if an invalid column value is passed.

Implementation
--------------

This plugin is realised as a pip-installable pytest plugin. The database access is handled by SQLAlchemy.

testdb
++++++

The testdb fixture opens the database connection and then uses automapping to create SQLAlchemy classes. These classes are then used to drop any existing table rows. All table rows are dropped again at the end of the fixture.

TestDatabase.add_row
++++++++++++++++++++

Reflection is used to get the SQLAlchemy ORM class for the given table name. It inspects the columns of that class and adds missing column names and values to those passed as keyword arguments. It then calls the class constructor to create a table row. The change is committed straight away.

TestDatabsase.fetch_all
+++++++++++++++++++++++

Reflection is used to get the SQLAlchemy ORM class for the given table name. That class is then used to query for all the table rows.

TestDatabsase.clean
+++++++++++++++++++

Reflection is used to get the SQLAlchemy ORM class for the given table name (or all ORM classes if no table name is given). It then deletes all rows from the table(s). The change is committed straight away.

tmprow
++++++

The `tmprow` fixture uses reflection to get the SQLAlchemy ORM class for the given table name. It inspects the columns of that class and adds missing column names and values to those passed as keyword arguments. It then calls the class constructor to create a table row. The change is committed straight away.

The SQLAlchemy object for the new row is stored in an internal list.

After a test is concluded, all entries of this internal list are deleted from the database, starting from the row last added.

create-test-db
++++++++++++++

`mysqldump` is used to export the table structure without data, and `sed` is used to remove all DEFINER clauses. `mysql` is used to create the new database and then to import the table structure. Finally, all foreign keys are removed from the tables.
