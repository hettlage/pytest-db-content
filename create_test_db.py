import argparse
import re
import subprocess
import sys
import tempfile
import MySQLdb

TEST_DB_IDENTIFIER = '__TEST__'


def _show_subprocess_error(completed_process):
    print('', file=sys.stderr)
    print(completed_process.stderr.decode('UTF-8'), file=sys.stderr)


def main():
    """
    A script for creating a test database.

    The created test database is a copy of another database, with two limitations:

    * All foreign keys are removed.
    * All `DEFINER` clauses are removed.

    The source database must specified by means of the command line options `--source-db` (for the database name),
    `--source-host` for the host address, (optionally) `--source-port` for the database port, `--source-username` for
    the username and `--source-password` for the password. Analogously, the target database (i.e. the  created target
    database) must be specified with the command line options `--target-db`, `--target-host`, (optionally)
    `--target-port`, `--target-username` and `--target-password`.

    The script fails if the name of the target (i.e. created test) database does not contain the string specified in the
    `TEST_DB_IDENTIFIER` constant.

    Returns
    -------
    return_code : int
        Zero if the script execution is successful; a non-zero value if the script execution fails.

    """

    # parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--remove-existing', required=False, action='store_true',
                        help='remove the target database if it exists already')
    parser.add_argument('--source-db', required=True, action='store', help='source database')
    parser.add_argument('--source-host', required=True, action='store', help='source host')
    parser.add_argument('--source-password', required=True, help='password for accessing the source database')
    parser.add_argument('--source-port', required=False, default=3306, help='source port')
    parser.add_argument('--source-username', required=True, help='username for accessing the source database')
    parser.add_argument('--target-db', required=True, action='store', help='target database')
    parser.add_argument('--target-host', required=True, action='store', help='target host')
    parser.add_argument('--target-password', required=True, help='password for accessing the target database')
    parser.add_argument('--target-port', required=False, default=3306, help='target port')
    parser.add_argument('--target-username', required=True, help='username for accessing the target database')
    args = parser.parse_args()

    # make sure the test database *really* is a test database
    if TEST_DB_IDENTIFIER not in args.target_db:
        print('The target database name must contain the string \'{}\'.'.format(TEST_DB_IDENTIFIER),
              file=sys.stderr)
        return 1

    # dump the source database
    print('Export source database...')
    mysqldump_process = subprocess.run(['mysqldump',
                                        '--routines',
                                        '--no-data',
                                        '-h', args.source_host,
                                        '-P', str(args.source_port),
                                        '-u', args.source_username,
                                        '-p{}'.format(args.source_password),
                                        args.source_db],
                                       stderr=subprocess.PIPE,
                                       stdout=subprocess.PIPE)
    if mysqldump_process.returncode:
        _show_subprocess_error(mysqldump_process)
        return mysqldump_process.returncode

    # See https://stackoverflow.com/questions/9446783/remove-definer-clause-from-mysql-dumps/24613430 for the
    # following code.

    # remove DEFINER clauses
    print('Clean exported SQL...')
    sed_process1 = subprocess.run(['sed',
                                   '-e', 's/DEFINER[ ]*=[ ]*[^*]*\*/\*/'],
                                  input=mysqldump_process.stdout,
                                  stderr=subprocess.PIPE,
                                  stdout=subprocess.PIPE)
    if sed_process1.returncode:
        _show_subprocess_error(sed_process1)
        return sed_process1.returncode

    # remove DEFINER clauses for procedures
    sed_process2 = subprocess.run(['sed',
                                  '-e', 's/DEFINER[ ]*=[ ]*[^*]*PROCEDURE/PROCEDURE/'],
                                  input=sed_process1.stdout,
                                  stderr=subprocess.PIPE,
                                  stdout=subprocess.PIPE)
    if sed_process2.returncode:
        _show_subprocess_error(sed_process2)
        return sed_process2.returncode

    # remove DEFINER clauses for functions
    sed_process3 = subprocess.run(['sed',
                                   '-e', 's/DEFINER[ ]*=[ ]*[^*]*FUNCTION/FUNCTION/'],
                                  input=sed_process2.stdout,
                                  stderr=subprocess.PIPE,
                                  stdout=subprocess.PIPE)
    if sed_process3.returncode:
        _show_subprocess_error(sed_process3.stderr)
        return sed_process3.returncode

    # remove references to the source database
    cleaned_sql = re.sub(r'`{}`\.'.format(args.source_db), '', sed_process3.stdout.decode("UTF-8"))

    # remove the test database (if requested and necessary)
    mysql_command = ['mysql',
                     '-h', args.target_host,
                     '-P', str(args.target_port),
                     '-u', args.target_username,
                     '-p{}'.format(args.target_password)]
    if args.remove_existing:
        print('Remove existing test database...')
        remove_db_process = subprocess.run(mysql_command,
                                           stderr=subprocess.PIPE,
                                           input=bytes('DROP DATABASE IF EXISTS `{}`'.format(args.target_db),
                                                       encoding='UTF-8'))
        if remove_db_process.returncode:
            _show_subprocess_error(remove_db_process)
            return remove_db_process.returncode

    # create the test database
    print('Create test database...')
    create_db_process = subprocess.run(mysql_command,
                                       stderr=subprocess.PIPE,
                                       input=bytes('CREATE DATABASE `{}`'.format(args.target_db), encoding='UTF-8'))
    if create_db_process.returncode:
        _show_subprocess_error(create_db_process)
        return create_db_process.returncode

    # import the database content into the new database
    mysql_command_with_db = mysql_command + [args.target_db]
    import_process = subprocess.run(mysql_command_with_db,
                                    stderr=subprocess.PIPE,
                                    input=bytes(cleaned_sql, encoding='UTF-8'))
    if import_process.returncode:
        _show_subprocess_error(import_process)
        return import_process.returncode

    # See https://gist.github.com/amcclosky/994260 for the following code.

    # remove all foreign keys
    print('Remove foreign keys from test database...')
    db = MySQLdb.connect(host=args.target_host,
                         port=args.target_port,
                         db=args.target_db,
                         user=args.target_username,
                         passwd=args.target_password)
    cursor = db.cursor()
    cursor.execute("""SELECT `table_schema`, `table_name`, `constraint_name`
                             FROM information_schema.table_constraints
                             WHERE constraint_type = 'FOREIGN KEY' AND table_schema = %s""",
                   (args.target_db,))
    for table_schema, table_name, constraint_name in cursor.fetchall():
        cursor = db.cursor()
        alter_statement = 'ALTER TABLE `{}`.`{}` DROP FOREIGN KEY `{}`'\
            .format(table_schema, table_name, constraint_name)
        cursor.execute(alter_statement)

    # done
    print()
    print('The test database {} has been created.'.format(args.target_db))
    print('All foreign keys have been removed.')

main()