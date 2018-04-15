# -*- coding: utf-8 -*-

import pytest


def pytest_addoption(parser):
    group = parser.getgroup('db-content')
    group.addoption(
        '--db-uri',
        action='store',
        dest='db_uri',
        help='URI of the test database, in a format SQLAlchemy understands'
    )


@pytest.fixture()
def testdb(pytestconfig):
    yield pytestconfig.getoption('db_uri')


@pytest.fixture()
def addrow():
    def _addrow():
        return '42'

    yield _addrow


@pytest.fixture()
def cleantable():
    def _cleantable():
        return '42'

    yield _cleantable