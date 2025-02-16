#!/usr/bin/python3

'''
    This script is used by the pipeline to send informational messages. It is a
    thin wrapper around cosa's broadcast_fedmsg().
'''

import argparse
import os
import sys

# Pick up libraries we use that are delivered along with COSA
sys.path.insert(0, '/usr/lib/coreos-assembler')
from cosalib.meta import GenericBuildMeta
from cosalib.fedora_messaging_request import broadcast_fedmsg


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fedmsg-conf",
        metavar="CONFIG.TOML",
        required=True,
        help="fedora-messaging config file for publishing",
    )
    parser.add_argument(
        "--stg",
        action="store_true",
        help="target the stg infra rather than prod",
    )
    parser.add_argument(
        "--extra-fedmsg-keys",
        action='append',
        metavar='KEY=VAL',
        default=[],
        help="extra keys to inject into messages",
    )

    subparsers = parser.add_subparsers(dest='cmd', title='subcommands')
    subparsers.required = True

    build_state_change = subparsers.add_parser('build.state.change')
    build_state_change.add_argument("--build", required=True)
    build_state_change.add_argument("--basearch", required=True)
    build_state_change.add_argument("--stream", required=True)
    build_state_change.add_argument("--state", required=True)
    build_state_change.add_argument("--build-dir")
    build_state_change.add_argument("--result")
    build_state_change.set_defaults(func=msg_build_state_change)

    stream_release = subparsers.add_parser('stream.release')
    stream_release.add_argument("--build", required=True)
    stream_release.add_argument("--basearch", required=True)
    stream_release.add_argument("--stream", required=True)
    stream_release.set_defaults(func=msg_stream_release)

    stream_metadata_update = subparsers.add_parser('stream.metadata.update')
    stream_metadata_update.add_argument("--stream", required=True)
    stream_metadata_update.set_defaults(func=msg_stream_metadata_update)

    return parser.parse_args()


def msg_build_state_change(args):
    body = {
        "build_id": args.build,
        "basearch": args.basearch,
        "stream": args.stream,
        "state": args.state,
        "build_dir": args.build_dir,
    }
    if args.result:
        body['result'] = args.result
    broadcast_fedmsg(
        broadcast_type='build.state.change',
        config=args.fedmsg_conf,
        environment=args.environment,
        body=body,
    )


def msg_stream_release(args):
    broadcast_fedmsg(
        broadcast_type='stream.release',
        config=args.fedmsg_conf,
        environment=args.environment,
        body={
            "build_id": args.build,
            "basearch": args.basearch,
            "stream": args.stream,
        },
    )


def msg_stream_metadata_update(args):
    broadcast_fedmsg(
        broadcast_type='stream.metadata.update',
        config=args.fedmsg_conf,
        environment=args.environment,
        body={
            "stream": args.stream,
        },
    )


def main():
    args = parse_args()
    args.environment = "stg" if args.stg else "prod"
    args.func(args)


if __name__ == "__main__":
    sys.exit(main())
