#!/usr/bin/env python3
# pylint: disable=invalid-name,line-too-long

import argparse
import glob
import hashlib
import json
import os
import shutil
import sys

objects = {}
extensions = [
    '.jpg',
    '.mp4',
    '.avi',
    '.lrv',
    '.thm',
]

parser = argparse.ArgumentParser()
parser.add_argument('--pattern', default='**', dest='pattern')
parser.add_argument('--export', nargs='?', type=argparse.FileType('w'), dest='export_')
parser.add_argument('--cleanup', default=False, action='store_true', dest='cleanup_')
parser.add_argument('--backup', dest='backup_')

action = parser.add_mutually_exclusive_group(required=True)
action.add_argument('--scan', action='store_true', dest='scan')
action.add_argument('--import', type=argparse.FileType('r'), dest='import_')

args = parser.parse_args()


def calculate_md5(filename_):
    hash_ = None

    with open(filename_, mode='rb') as handle:
        # Only read the first 32 kbytes of a file to generate
        # the md5 hash, since if we're reading a 1 or 2GB
        # movie it's going to take some time, plus a large
        # memory buffer.
        data = handle.read(32768)

        hash_ = hashlib.md5(data).hexdigest()

    return hash_


if __name__ == '__main__':
    if args.scan:
        for filename in glob.iglob(args.pattern, recursive=True):
            if not os.path.isfile(filename):
                # Skip anything that is not a file
                continue

            _, extension = os.path.splitext(filename)

            extension = extension.lower()

            if not any([not extensions, extension in extensions]):
                continue

            md5 = calculate_md5(filename)
            objects[md5] = objects.get(md5, {
                'filenames': [],
                'count': 0,
                'size': 0,
                'total_size': 0
            })
            objects[md5]['filenames'] = objects[md5].get('filenames') + [filename]
            objects[md5]['count'] += 1
            objects[md5]['size'] = os.path.getsize(filename)
            objects[md5]['total_size'] = objects[md5]['size'] * objects[md5]['count']

        if args.export_:
            print(
                f"Exporting results [unique hashes={len(objects)}, destination={args.export_.name}]")
            # Make a backup of the existing sys.stdout file handle
            # remap sys.stdout to our export file and dump the
            # contents of our data to sys.stdout which will either
            # be to the console or filename
            backup_fh, sys.stdout = sys.stdout, args.export_

            print(json.dumps(objects, indent=4))
            sys.stdout = backup_fh

    elif args.import_:
        objects = json.load(args.import_)
        print(objects)

if args.cleanup_:
    total_bytes_freed = 0

    if args.backup_:
        # Attempt to create backup folder
        try:
            os.mkdir(args.backup_)
        except FileExistsError:
            print(f"Directory [{args.backup_}] already exists, using as backup folder")
            pass

    for key, value in filter(lambda v: v[1].get('count') > 1, objects.items()):
        filenames = value.get('filenames', [])

        # Our array of saved/ filenames
        filenames_ = filenames.copy()

        # Our filename we'll make a backup of, plus pop the first element from the
        # list, so we can delete any remaining elements
        filename = filenames.pop()

        # Just another sanity check to make sure we have more than 1 filename
        # before performing any move operations, including that we make sure
        # all of our files exist before proceeding.

        if len(filenames) >= 1 and all([os.path.isfile(key) for key in filenames_]):
            if args.backup_:
                print(f"Copying [{filename}] to [{args.backup_}] before deleting")

                try:
                    shutil.copy2(filename, args.backup_)
                except shutil.SameFileError as e:
                    print(f"Copy error [{e}]")

            for filename_ in filenames:
                print(f"Deleting a copy of [{filename_}]")
                total_bytes_freed += value.get('size', 0)

                os.remove(filename_)
        else:
            print(f"File [{filename}] is not being moved as one or more of its copies no longer exist!")

    print(f"Total bytes freed by cleanup [{total_bytes_freed}]")

