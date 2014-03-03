
import sys

import camlistore
from StringIO import StringIO
from dulwich.server import (
    Backend,
    BackendRepo,
)
from dulwich.object_store import (
    BaseObjectStore,
    MemoryObjectStore,
)
from dulwich.pack import (
    Pack,
    PackData,
    PackInflater,
    iter_sha1,
    write_pack_header,
    write_pack_index_v2,
    write_pack_object,
    write_pack_objects,
    compute_file_sha,
    PackIndexer,
    PackStreamCopier,
)
from dulwich.errors import NotGitRepository


class CamliObjectStore(BaseObjectStore):

    def __init__(self, conn):
        self.conn = conn

    def add_object(self, obj):
        self.add_objects([obj])

    def add_objects(self, objs):
        sys.stderr.write("Adding objects %r\n" % list(objs))

        blobs = [
            camlistore.Blob(
                x._header() + x.as_raw_string(),
                hash_func_name='sha1',
            )
            for x in objs
        ]
        for x in blobs:
            sys.stderr.write("it's %r\n" % x.blobref)
        # FIXME: This only works as long as the git repo doesn't contain
        # any objects over camlistore's blob size limit of 32MB. For larger
        # objects we should implement an indirection where the repo
        # metadata includes attributes for objects we've split that
        # point to camlistore static set blobs listing all of the chunks.
        self.conn.blobs.put_multi(*blobs)

    def add_pack(self):
        f = StringIO()
        def commit():
            p = PackData.from_file(StringIO(f.getvalue()), f.tell())
            f.close()
            self.add_objects(
                [obj for obj in PackInflater.for_pack_data(p)]
            )
        def abort():
            pass
        return f, commit, abort

    def add_thin_pack(self, read_all, read_some):
        f, commit, abort = self.add_pack()
        try:
            indexer = PackIndexer(f, resolve_ext_ref=self.get_raw)
            copier = PackStreamCopier(read_all, read_some, f, delta_iter=indexer)
            copier.verify()
            #self._complete_thin_pack(f, indexer)
        except:
            abort()
            raise
        else:
            commit()


class CamliRepo(BackendRepo):

    def __init__(self, repo_meta, conn):
        self.conn = conn
        self.repo_meta = repo_meta
        self.object_store = CamliObjectStore(conn)
        self.refs = {}
        attrs = repo_meta["permanode"]["attr"]
        ref_keys = (
            x for x in attrs
            if x.startswith("ref:")
        )
        for ref_key in ref_keys:
            ref_name = ref_key[4:]
            if len(attrs[ref_key]) > 0:
                self.refs[ref_name] = attrs[ref_key][-1]

    def get_refs(self):
        return self.refs

    def get_peeled(self, name):
        return None

    def fetch_objects(
        self,
        determine_wants,
        graph_walker,
        progress,
        get_tagged=None
    ):
        if False:
            yield None


class CamliBackend(Backend):

    def __init__(self, conn):
        self.conn = conn

    def open_repository(self, permanode_blobref):
        describe = self.conn.searcher.describe_blob(permanode_blobref)
        repo_meta = describe.raw_dict
        return CamliRepo(repo_meta, self.conn)
