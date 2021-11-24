#!/usr/bin/python
# -*- coding: utf-8 -*-

import psycopg2.extras


class Site(object):
    def __init__(self, db):
        self.conn = db.connection
        self.c = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        self.ignored_filters = ["all", "", None]
        self.order_cols = []
        self.filter_cols = []
