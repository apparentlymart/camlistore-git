#!/usr/bin/env python

import camlistore
from camligit import CamliBackend

from dulwich.server import (
    serve_command,
    ReceivePackHandler,
)


conn = camlistore.connect("http://localhost:3179/")

backend = CamliBackend(conn)
serve_command(ReceivePackHandler, backend=backend)
