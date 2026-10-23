#!/usr/bin/python
# -*- coding: utf-8 -*-

import os

from labhub import app


if __name__ == "__main__":
    # Never enable the Werkzeug debugger on a reachable host.
    app.run(debug=os.environ.get('LABHUB_DEBUG', '').lower() in {'1', 'true', 'yes'})
