# Copyright (c) 2017, Djaodjin Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import getpass, mimetypes, os

import boto
from django.core.management.base import BaseCommand

from ..... import configs, crypt
from ... import settings

#pylint:disable=import-error
from six.moves.urllib.parse import urlparse


class Command(BaseCommand):
    help = "Encrypt the configuration files and upload them to a S3 bucket."

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument('--app_name',
            action='store', dest='app_name', default=settings.APP_NAME,
            help='Name of the config file(s) project')
        parser.add_argument('--location', action='store', dest='location',
            default=None, help='Print but do not execute')
        parser.add_argument('filenames', metavar='filenames', nargs='+',
            help="config files to upload")

    def handle(self, *args, **options):
        #pylint: disable=too-many-locals
        default_acl = 'private'
        app_name = options['app_name']
        location = options['location']
        if not location:
            location = os.getenv("SETTINGS_LOCATION", None)
        if not location:
            self.stderr.write("a location argument must be passed on the "\
            "command line or SETTINGS_LOCATION defined in the environment.\n")
            return -1
        upload_local = not location.startswith('s3://')
        _, bucket_name, prefix = urlparse(location)[:3]
        if upload_local:
            self.stdout.write('upload configs to local directory %s' % location)
        else:
            self.stdout.write("upload configs to %s/%s" % (location, app_name))
        passphrase = getpass.getpass('Passphrase:')
        conn = boto.connect_s3()
        bucket = conn.get_bucket(bucket_name)
        for confname in options['filenames']:
            if os.path.exists(confname):
                conf_path = confname
                confname = os.path.basename(confname)
            else:
                conf_path = configs.locate_config(confname, app_name)
            content_type = mimetypes.guess_type(conf_path)[0]
            if content_type:
                headers = {'Content-Type': content_type}
            else:
                headers = {}
            content = None
            with open(conf_path) as conf_file:
                content = conf_file.read()
            encrypted = crypt.encrypt(content, passphrase)
            if upload_local:
                with open(
                    os.path.join(location, confname), "wb") as upload_file:
                    upload_file.write(encrypted)
            else:
                key = boto.s3.key.Key(bucket)
                key.name = '%s/%s/%s' % (prefix, app_name, confname)
                key.set_contents_from_string(encrypted, headers,
                    replace=True, policy=default_acl)
