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

pytest-db-content is a plugin for `pytest http://pytest.readthedocs.io/en/latest/`_, which offers three fixtures and a utility command.

testdb
++++++

The `testdb` fixture, which is session scoped, creates a database connection and deletes the rows of all database tables when it is called. All table entries are deleted again and the database connection is closed when the session is finished. The tables themselves are neither created nor dropped by the fixture

The database URI must be provided as a command line option, `--db-uri`, and it must have a format understood by SQLAlchemy.

The database name must include the string `__TEST__`. This requirement is made in order to avoid connecting to a production database. A meaningful error must be raised if the databasename does not meet this condition.

Both the `addrow` and `cleantable` fixture use the `testdb` fixture, so there usually should be no need to explicitly include it in the tests of a project.

addrow
++++++

The `addrow` fixture, which is function scoped, returns a function which lets the user add a new row to a table. The row is automatically deleted once the test is done. A dictionary of column names and values is returned.

The signature of the function is as follows::

    addrow(table_name, **kwargs)

`table_name` is a string and must be a valid table name. The key word arguments must be column names and values for the table. The spelling must match exactly that of the column names in the dabase.

A meaningful error must be raised if an invalid tablename or column name is used, or if a column value is invalid.

cleantable
++++++++++

The `cleantable` fixture expects a valid table name as its single argument, and it deletes all rows from this table.

create-test-db
++++++++++++++

The `create-test-db` command creates a new MySQL database and adds the table structure of another MySQL database to it. It then removes all foreign key constraints for the newly created tables.

The command has the following command line options.

===================  ============================================  =========
Option               Description                                   Default  
===================  ============================================  =========
--remove-existing    Remove the target db if it exists already     False    
--source-host        Host server for the source database         
--source-port        Port for the source database                  3306     
--source-db          Source database                             
--source-username    Username for accessing the source database  
--source-password    Password for accessing the source database  
--target-host        Host server for the created database        
--target-port        Port for the created database                 3306     
--target-db          Created database                            
--target-username    Username for accessing the target database  
--target-password    Password for accessing the target database  
===================  ============================================  =========

The name of the target database must contain the string `__TEST__`. It is assumed that UTF-8 is used as the encoding.

Tests
-----

The plugin must

* Expose a `testdb` and an `addrow` fixture.
* Add a command line option group with an option `--db-uri`.
* Raise an error if the `--db-uri` option value does not contain the string `__TEST__`.

The `testdb` fixture must

* Raise an error if the `--db-uri` option has not been used.
* Raise an error if the `--db-uri` option value does not contain the string `__TEST__`.
* Raise an error if it cannot connect to the database.

The `addrow` fixture must

* Create a new table row with the given values if called with a valid table name and valid column names and values.
* Return a dictionary of column names and values for the row it creates.
* Create a new table row even if not all required columns are passed.
* Raise a meaningful error if an invalid table name is passed.
* Raise a meaningful error if an invalid column name is passed.
* Raise a meaningful error if an invalid column value is passed.

The `cleantable` fixture must

* Delete all table rows if it is called with a valid table name.
* Raise a meaningful error if an invalid table name is passed.

Implementation
--------------

This plugin is realised as a pip-installable pytest plugin. The database access is handled by SQLAlchemy.

testdb
++++++

The testdb fixture opens the database connection and then uses automapping to create SQLAlchemy classes. These classes are then used to drop any existing table rows. All table rows are dropped again at the ebnd of the fixture.

addrow
++++++

The addrow fixture uses reflection to get the SQLAlchemy ORM class for the given table name. It inspects the columns of that class and adds missing column names and values to those passed as keyword arguments. It then calls the class constructor to create a table row. The change is committed straight away.

The SQLAlchemy object for the new row is stored in an internal list.

After a test is concluded, all entries of this internal list are deleted from the database, starting from the row last added.

cleantable
++++++++++

The cleantable fixture uses reflection to get the SQLAlchemy ORM class for the given table name. It then deletes all rows from the table. The change is committed straight away.

create-test-db
++++++++++++++

`mysqldump` is used to export the table structure without data, and `sed` is used to remove all DEFINER clauses. `mysql` is used to create the new database and then to import the table structure. Finally, all foreign keys are removed from the tables.