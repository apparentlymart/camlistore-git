camlistore-git
==============

This is a prototype of archiving git repositories in Camlistore.

This is not production-ready or complete. It's just a proof-of-concept for
a Camlistore schema proposal for git repositories.

Requirements
------------

    pip install dulwich camlistore

Importing
---------

First create a permanode that'll be your repository root::

    camput permanode

Make a note of the blobref you got and use it to upload::

    python import.py <blobref>

At present this only creates the object data and associated index. It does
not set the attributes on the permanode to add the index and update the
refs, because the underlying camlistore library has no support for creating
claims.

Exporting
---------

Make a bare repo to import into. This must be called ``export.git`` and be
in the current working directory::

    git init --bare export.git

Then start the export::

    python export.py <blobref>

The ``export.git`` repository will then be updated to match the imported
repository.
