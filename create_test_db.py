import argparse
import subprocess


def main():
    """

    :return:
    """

    # parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-db', required=True, action='store', help='source database')
    parser.add_argument('--source-host', required=True, action='store', help='source host')
    parser.add_argument('--source-port', required=False, default=3306, help='source port')
    parser.add_argument('--target-db', required=True, action='store', help='target database')
    parser.add_argument('--target-host', required=True, action='store', help='target host')
    parser.add_argument('--target-port', required=False, default=3306, help='target port')

    # dump the source database

    # remove all DEFINER clauses

    # create the test database

    # import the database content into the new database

    # remove all foreign keys
