
import camlistore
import sys
import json
from dulwich.repo import (
    Repo as GitRepo
)
from dulwich.objects import ShaFile
from StringIO import StringIO
from os import mkdir
import zlib

conn = camlistore.connect("http://localhost:3179/")
repo = GitRepo('export.git')

permanode_blobref = sys.argv[1]

repo_node = conn.searcher.describe_blob(permanode_blobref)
repo_attr = repo_node.raw_dict["permanode"]["attr"]

object_index_blobrefs = repo_attr.get("gitObjectIndices", [])

for index_blobref in object_index_blobrefs:
    index_blob = conn.blobs.get(index_blobref)
    index_dict = json.loads(index_blob.data)
    for obj_id, bytes_blobref in index_dict["objectBytes"].iteritems():
        object_dir = 'export.git/objects/' + obj_id[0:2]
        try:
            mkdir(object_dir)
        except OSError:
            pass
        object_file = open(object_dir + '/' + obj_id[2:], 'wb')
        bytes_blob = conn.blobs.get(bytes_blobref)
        bytes_dict = json.loads(bytes_blob.data)
        data = ''
        for part in bytes_dict["parts"]:
            part_blobref = part["blobRef"]
            part_blob = conn.blobs.get(part_blobref)
            #object_file.write(part_blob.data)
            data = data + part_blob.data
        object_file.write(zlib.compress(data))

for attr_key, attr_vals in repo_attr.iteritems():
    if not attr_key.startswith("gitRef:"):
        continue

    ref_name = attr_key[7:]
    ref_value = attr_vals[0]
    repo.refs[ref_name] = ref_value
