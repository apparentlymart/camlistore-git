
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
            # TODO: Eventually when camlistore gets a garbage collector
            # it's gonna go looking for blobrefs inside permanodes to
            # see what it should keep. Therefore we need to store these
            # references as full blobrefs (with the sha1- prefix) and
            # then trim off the prefix for git's benefit.
            # That's still not really enough since we'd lose the
            # descendent objects too (trees referenced by commits, etc)
            # so basically this whole model is a bit flawed and needs to
            # be rethought if camlistore gets a GC.
            if len(attrs[ref_key]) > 0:
                self.refs[str(ref_name)] = str(attrs[ref_key][-1])

    def get_refs(self):
        return self.refs

    def get_peeled(self, name):
        # FIXME: This isn't correct for tags... we need to
        # keep looking these up until we find an actual commit.
        return self.refs[name]

    def fetch_objects(
        self,
        determine_wants,
        graph_walker,
        progress,
        get_tagged=None
    ):
        refs = self.refs  # FIXME: doesn't work for some reason
        wants = determine_wants(refs)

        shallows = getattr(graph_walker, 'shallow', set())
        unshallows = getattr(graph_walker, 'unshallow', set())

        if wants == []:
            if shallows or unshallows:
                # Do not send a pack in shallow short-circuit path
                return None
            return []

        haves = self.object_store.find_common_revisions(graph_walker)

        if shallows or unshallows:
            haves = []

        def get_parents(commit):
            if commit.id in shallows:
                return []
            return self.get_parents(commit.id, commit)

        return self.object_store.iter_shas(
            self.object_store.find_missing_objects(
                haves, wants, progress,
                get_tagged,
                get_parents=get_parents,
            )
        )

        progress("client wants %r\n" % wants)
        return [
        ]


class CamliBackend(Backend):

    def __init__(self, conn):
        self.conn = conn

    def open_repository(self, permanode_blobref):
        describe = self.conn.searcher.describe_blob(permanode_blobref)
        repo_meta = describe.raw_dict
        return CamliRepo(repo_meta, self.conn)
