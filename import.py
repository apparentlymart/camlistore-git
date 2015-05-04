
import camlistore
import sys
import json
from dulwich.repo import Repo as GitRepo

conn = camlistore.connect("http://localhost:3179/")
repo = GitRepo('.')

permanode_blobref = sys.argv[1]

repo_node = conn.searcher.describe_blob(permanode_blobref)
repo_attr = repo_node.raw_dict["permanode"]["attr"]

object_index_blobrefs = repo_attr.get("gitObjectIndices", [])
known_obj_ids = set()

for index_blobref in object_index_blobrefs:
    index_blob = conn.blobs.get(index_blobref)
    index_dict = json.loads(index_blob.data)
    for obj_id in index_dict["objectBytes"]:
        known_obj_ids.add(obj_id)

obj_bytes_blobrefs = {}

for obj_id in repo.object_store:
    if obj_id in known_obj_ids:
        continue

    obj = repo.object_store[obj_id]

    obj_header_blob = camlistore.Blob(obj._header(), hash_func_name='sha1')
    # FIXME: Should split the body blob like it's a file
    obj_body_blob = camlistore.Blob(obj.as_raw_string(), hash_func_name='sha1')

    bytes_dict = {}
    bytes_dict["camliType"] = "bytes"
    bytes_dict["parts"] = [
        {
            "blobRef": obj_header_blob.blobref,
            "size": obj_header_blob.size,
        },
        {
            "blobRef": obj_body_blob.blobref,
            "size": obj_body_blob.size,
        },
    ]
    bytes_payload = json.dumps(bytes_dict, indent=1)
    bytes_payload = bytes_payload.replace("{", '{"camliVersion": 1,', 1)
    bytes_blob = camlistore.Blob(bytes_payload, hash_func_name='sha1')
    obj_bytes_blobrefs[obj_id] = bytes_blob.blobref

    conn.blobs.put_multi(obj_header_blob, obj_body_blob, bytes_blob)


obj_index_dict = {}
obj_index_dict["camliType"] = "gitObjectIndex"
obj_index_dict["objectBytes"] = obj_bytes_blobrefs
obj_index_payload = json.dumps(obj_index_dict, indent=1)
obj_index_payload = obj_index_payload.replace("{", '{"camliVersion": 1,', 1)
obj_index_blob = camlistore.Blob(obj_index_payload, hash_func_name='sha1')
conn.blobs.put(obj_index_blob)

print obj_index_blob.blobref
