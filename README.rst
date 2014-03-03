camlistore-git
==============

This thing is a toy implementation of the git protocol backed by Camlistore.

If the repo contains only objects that are smaller than 32MB in size and
doesn't contain any tags (two limitations that ought to be fixed, but aren't)
then you can push objects from your git repo into your Camlistore server,
although at present you won't be able to get them back out again without
some manual work.

Requirements
------------

    pip install dulwich camlistore

Setup
-----

First create a permanode that'll be your repository root:

    camput permanode

Make a note of the blobref you got and put it into a special remote in your
``.git/config``:

    [remote "camli"]
        url = permanode-blobref
        fetch = +refs/heads/*:refs/remotes/camli/*
        receivepack = /path/to/camlistore-git/receive-pack.py
        uploadpack = /path/to/camlistore-git/upload-pack.py

Usage
-----

Push to Camlistore just like any other repository:

    git push camli master

If you're watching the logs for your Camlistore server you'll see it accept
some new blobs the first time you call this. Subsequent pushes with no
new commits will not show anything, since the server already has those blobs.

At present we don't update the stored ref on push, because the ``camlistore``
library hasn't learned to make mutation claims yet. However if you're not
already bored of this you can try manually setting a ref:

    camput attr permanode-blobref ref:refs/heads/master commit-sha1

(Of course remember to substitute appropriate values for ``permanode-blobref``
and ``commit-sha``.)

Once you've done that you should find that pushing will tell you that the
remote is already up-to-date.

You can also now list refs on the remote, which should echo back the
commit hash you just wrote:

    git ls-remote camli

However, fetching won't work unless your local repository happens to have
all of the necessary objects, since retrieving objects from the store is
not yet implemented.

Limitations
-----------

This thing is basically one giant limitation, but if you're curious about
building it into something more real here are some notes about what's missing:

* Will fail if your git repo contains any objects bigger than the Camlistore
  maximum blob size, since it doesn't attempt to split up objects in this
  case.

* Although it supports reading the refs out of a permanode's attributes,
  it doesn't support creating new mutation claims when a ref is updated.

* Objects can be stored into Camlistore but retrieving them back again
  with ``git pull`` or ``git fetch`` is not supported.

* It doesn't know how to peel tag objects, so it'll probably blow up in your
  face if your repo contains these.

* If Camlistore ever gets a garbage collector it'll probably delete all of
  your git objects, because Camlistore doesn't understand the git data model
  and so it can't tell that all of these objects belong to your repository
  permanode. We'd need to create explicit "keep" claims to avoid this.

The idea of storing git repos inside Camlistore is not particularly useful
anyway since you can already push your objects to a multitude of hosted
git server solutions that'll store stuff much more sensibly. However, if you
want to try finishing this thing up and making something useful then go
right ahead!

License
-------

This thing is too dumb to deserve a license so it's just placed into the
public domain. If "public domain" is not a concept in your region then I
apologise.
