.. toctree::
   :maxdepth: 2


pytest-db-content
=================

[TBD]

create-test-db
--------------

As its name suggests, `create-test-db` is a script for creating a test database. It can only handle MySQL databases. While (depending on your use case) it may be of help, it is not necessary to use it with the `pytest-db-content` plugin. You may generate your test database any way you like.

.. warning::

   The script does not try to cover all possible edge cases. So if your database contains names that include non-ASCII characters, spaces or the like, it may or may not work as expected. Do not use this script for generating a database you might want to use in production.

If you have installed `pytest-db-content`, the script should be available as a shell command. It accepts the following command line options.

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

Apart from the two port options and the `--force` option all the options must be included. An example usage might look as follows.

.. code-block:: bash

   create-test-db --source-host my.db.server.org \
                  --source-db observations \
                  --source-username observer \
                  --source-password topsecret
                  --target-host my.test.server.org \
                  --target-db observations__TEST__ \
                  --target-username admin \
                  --target-password alsotopsecret \
                  --force

There is no need to choose an administrator as the user for the test database; but you should bear in mind that the user needs far-reaching permissions, such as dropping and creating whole databases.

`create-test-db` is opinionated when it comes to the name of the test database and requires that it contains the string `__TEST__`. This is to ensure that you don't accidentally replace a live database.

The script first exports the specified source database and then cleans the exported SQL by removing all `DEFINER` clauses and dropping all the foreign keys. The former is done as the definers may not exist as database users in the target database. The latter simplifies adding entries to the database and ensures that SQLAlchemy automapping will work.
