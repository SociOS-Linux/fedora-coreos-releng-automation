#!/usr/bin/python3

"""
    This script is meant to be run from the Fedora CoreOS build
    pipeline (see https://github.com/coreos/fedora-coreos-pipeline.git)
    It makes an OSTree import request to the coreos-ostree-importer
    running in Fedora's Infra OpenShift cluster.
"""

import argparse
import os
import sys

# Pick up libraries we use that are delivered along with COSA
sys.path.insert(0, '/usr/lib/coreos-assembler')
from cosalib.meta import GenericBuildMeta
from cosalib.fedora_messaging_request import send_request_and_wait_for_response
from cosalib.cmdlib import get_basearch

# Example datagrepper URLs to inspect sent messages:
# https://apps.fedoraproject.org/datagrepper/raw?topic=org.fedoraproject.prod.coreos.build.request.ostree-import&delta=100000
# https://apps.stg.fedoraproject.org/datagrepper/raw?topic=org.fedoraproject.stg.coreos.build.request.ostree-import&delta=100000
# https://apps.fedoraproject.org/datagrepper/raw?topic=org.fedoraproject.prod.coreos.build.request.ostree-import.finished&delta=100000
# https://apps.stg.fedoraproject.org/datagrepper/raw?topic=org.fedoraproject.stg.coreos.build.request.ostree-import.finished&delta=100000

# Give the importer some time to do the import
OSTREE_IMPORTER_REQUEST_TIMEOUT_SEC = 15 * 60

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", help="Build ID", required=True)
    parser.add_argument(
        "--arch", help="target architecture", default=get_basearch()
    )
    parser.add_argument(
        "--fedmsg-conf",
        metavar="CONFIG.TOML",
        required=True,
        help="fedora-messaging config file for publishing",
    )
    parser.add_argument(
        "--stg", action="store_true", help="target the stg infra rather than prod"
    )
    parser.add_argument(
        "--s3",
        metavar="<BUCKET>[/PREFIX]",
        required=True,
        help="bucket and prefix to S3 builds/ dir",
    )
    parser.add_argument(
        "--repo",
        choices=["prod", "compose"],
        required=True,
        help="the name of the OSTree repo within Fedora to import into",
    )
    return parser.parse_args()


def send_ostree_import_request(args):
    if args.build == 'latest':
        raise Exception("Refusing to ostree import generic 'latest' build ID")
    build = GenericBuildMeta(build=args.build, basearch=args.arch)

    bucket, prefix = get_bucket_and_prefix(args.s3)
    environment = "prod"
    if args.stg:
        environment = "stg"

    # Example: https://fcos-builds.s3.amazonaws.com/prod/streams/stable/builds/31.20200127.3.0/x86_64/fedora-coreos-31.20200127.3.0-ostree.x86_64.tar
    commit_url = f"https://{bucket}.s3.amazonaws.com/{prefix}/builds/{args.build}/{args.arch}/{build['images']['ostree']['path']}"

    response = send_request_and_wait_for_response(
        request_type="ostree-import",
        config=args.fedmsg_conf,
        environment=environment,
        request_timeout=OSTREE_IMPORTER_REQUEST_TIMEOUT_SEC,
        body={
            "build_id": args.build,
            "basearch": args.arch,
            "commit_url": commit_url,
            "checksum": "sha256:" + build["images"]["ostree"]["sha256"],
            "ostree_ref": build["ref"],
            "ostree_checksum": build["ostree-commit"],
            "target_repo": args.repo,
        },
    )
    validate_response(response)


def get_bucket_and_prefix(path):
    split = path.split("/", 1)
    if len(split) == 1:
        return (split[0], "")
    return split


def validate_response(response):
    if response["status"].lower() == "failure":
        # https://pagure.io/robosignatory/pull-request/38
        if "failure-message" not in response:
            raise Exception("Importing failed")
        raise Exception(f"Importing failed: {response['failure-message']}")
    assert response["status"].lower() == "success", str(response)


def main():
    args = parse_args()
    send_ostree_import_request(args)


if __name__ == "__main__":
    sys.exit(main())
