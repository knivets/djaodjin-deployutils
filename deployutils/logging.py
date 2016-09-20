# Copyright (c) 2016, Djaodjin Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
# TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from __future__ import absolute_import

import logging, json

from django.views.debug import ExceptionReporter
from pip.utils import get_installed_distributions

from deployutils import crypt
from deployutils.thread_local import get_request


class RequestFilter(logging.Filter):

    def filter(self, record):
        """
        Adds user and remote_addr to the record.
        """
        request = get_request()
        user = getattr(request, 'user', None)
        if user and not user.is_anonymous():
            record.username = user.username
        else:
            record.username = '-'
        meta = getattr(request, 'META', {})
        record.remote_addr = meta.get('REMOTE_ADDR', '-')
        return True


class JSONFormatter(logging.Formatter):
    """
    JSON log formatter.
    """

    _whitelists = {
        'record': [
            'asctime',
            'event',
            'http_user_agent',
            'levelname',
            'message',
            'path_info',
            'remote_addr',
            'request_method',
            'server_protocol',
            'username'
        ],
        'traceback': [
            'server_time',
            'sys_version_info',
            'exception_type',
            'frames',
            'template_info',
            'sys_executable',
            'django_version_info',
            'exception_value',
            'sys_path',
            'filtered_POST',
            'settings',
            'postmortem',
            'template_does_not_exist'
        ],
        'meta': [
            'CONTENT_LENGTH',
            'CONTENT_TYPE',
            'CSRF_COOKIE',
            'GATEWAY_INTERFACE',
            'HTTP_ACCEPT',
            'HTTP_ACCEPT_ENCODING',
            'HTTP_ACCEPT_LANGUAGE',
            'HTTP_CACHE_CONTROL',
            'HTTP_CONNECTION',
            'HTTP_COOKIE',
            'HTTP_DNT',
            'HTTP_HOST',
            'HTTP_UPGRADE_INSECURE_REQUESTS',
            'HTTP_USER_AGENT',
            'LOGNAME',
            'PWD',
            'QUERY_STRING',
            'REMOTE_ADDR',
            'REMOTE_HOST',
            'REQUEST_METHOD',
            'SECURITYSESSIONID',
            'SERVER_NAME',
            'SERVER_PORT',
            'SERVER_PROTOCOL',
            'SERVER_SOFTWARE',
            'TMPDIR',
            'USER',
            'VIRTUAL_ENV',
            'wsgi.version',
            'wsgi.url_scheme',
        ],
        'settings': [
            'ABSOLUTE_URL_OVERRIDES',
            'ADMINS',
            'ALLOWED_HOSTS',
            'ALLOWED_INCLUDE_ROOTS',
            'APPEND_SLASH',
            'APP_NAME',
            'ASSETS_DEBUG',
            'AUTHENTICATION_BACKENDS',
            'BASE_DIR',
            'CSRF_COOKIE_AGE',
            'CSRF_COOKIE_DOMAIN',
            'CSRF_COOKIE_HTTPONLY',
            'CSRF_COOKIE_NAME',
            'CSRF_COOKIE_PATH',
            'CSRF_COOKIE_SECURE',
            'CSRF_FAILURE_VIEW',
            'CSRF_HEADER_NAME',
            'CSRF_TRUSTED_ORIGINS',
            'DEBUG',
            'DEBUG_PROPAGATE_EXCEPTIONS',
            'DEFAULT_FILE_STORAGE',
            'DEFAULT_FROM_EMAIL',
            'EMAILER_BACKEND',
            'EMAIL_BACKEND',
            'EMAIL_HOST',
            'EMAIL_HOST_PASSWORD',
            'EMAIL_HOST_USER'
            'EMAIL_PORT',
            'EMAIL_SSL_CERTFILE',
            'EMAIL_SSL_KEYFILE',
            'EMAIL_SUBJECT_PREFIX',
            'EMAIL_TIMEOUT',
            'EMAIL_USE_SSL',
            'EMAIL_USE_TLS',
            'FILE_UPLOAD_DIRECTORY_PERMISSIONS',
            'FILE_UPLOAD_HANDLERS',
            'FILE_UPLOAD_MAX_MEMORY_SIZE',
            'FILE_UPLOAD_PERMISSIONS',
            'FILE_UPLOAD_TEMP_DIR',
            'INSTALLED_APPS',
            'MAIL_TOADDRS',
            'MANAGERS',
            'MAX_UPLOAD_SIZE',
            'MIDDLEWARE_CLASSES',
            'PASSWORD_HASHERS',
            'SECURE_BROWSER_XSS_FILTER',
            'SECURE_CONTENT_TYPE_NOSNIFF',
            'SECURE_HSTS_INCLUDE_SUBDOMAINS',
            'SECURE_HSTS_SECONDS',
            'SECURE_PROXY_SSL_HEADER',
            'SECURE_REDIRECT_EXEMPT',
            'SECURE_SSL_HOST',
            'SECURE_SSL_REDIRECT',
            'SERVER_EMAIL',
            'SESSION_CACHE_ALIAS',
            'SESSION_COOKIE_AGE',
            'SESSION_COOKIE_DOMAIN',
            'SESSION_COOKIE_HTTPONLY',
            'SESSION_COOKIE_NAME',
            'SESSION_COOKIE_PATH',
            'SESSION_COOKIE_SECURE',
            'SESSION_ENGINE',
            'SESSION_EXPIRE_AT_BROWSER_CLOSE',
            'SESSION_FILE_PATH',
            'SESSION_SAVE_EVERY_REQUEST',
            'SESSION_SERIALIZER',
            'USE_X_FORWARDED_HOST',
            'USE_X_FORWARDED_PORT',
            'WSGI_APPLICATION',
            'X_FRAME_OPTIONS',
        ]
    }

    def __init__(self, fmt=None, datefmt=None, whitelists=None, replace=False):
        super(JSONFormatter, self).__init__(fmt=fmt, datefmt=datefmt)
        if whitelists and replace:
            self.whitelists = whitelists
        elif whitelists:
            self.whitelists = self._whitelists
            for key, values in whitelists.iteritems():
                if not key in self.whitelists:
                    self.whitelists[key] = []
                self.whitelists[key] += values
        else:
            self.whitelists = self._whitelists

    def format(self, record):
        record.message = record.getMessage()
        if self.usesTime():
            record.asctime = self.formatTime(record, self.datefmt)

        record_dict = {
            attr_name: record.__dict__[attr_name]
            for attr_name in record.__dict__
            if attr_name in self.whitelists.get('record')
        }
        if record.exc_info:
            if hasattr(record, 'request'):
                request = record.request
            else:
                request = None
            exc_info_dict = self.formatException(
                record.exc_info, request=request)
            if exc_info_dict:
                record_dict.update(exc_info_dict)
        return json.dumps(record_dict, cls=crypt.JSONEncoder)

    def formatException(self, exc_info, request=None):
        #pylint:disable=too-many-locals,arguments-differ
        reporter = ExceptionReporter(request, is_email=True, *exc_info)
        traceback_data = reporter.get_traceback_data()
        filtered_traceback_data = {}

        if request:
            user = getattr(request, 'user', None)
            if user and not user.is_anonymous():
                username = user.username
            else:
                username = '-'
            filtered_traceback_data.update({
                'method': request.method,
                'path_info': request.path_info,
                'username': username,
                'remote_addr': request.META.get('REMOTE_ADDR', '-'),
                'server_protocol': request.META.get('SERVER_PROTOCOL', '-'),
                'http_user_agent': request.META.get('HTTP_USER_AGENT', '-')
            })
            request_dict = {
                'method': request.method,
                'path_info': request.path_info}
            params = {}
            for key, val in request.GET.iteritems():
                params.update({key: val})
            if params:
                request_dict.update({'GET': params})
            params = {}
            for key, val in request.POST.iteritems():
                params.update({key: val})
            if params:
                request_dict.update({'POST': params})
            params = {}
            for key, val in request.FILES.iteritems():
                params.update({key: val})
            if params:
                request_dict.update({'FILES': params})
            params = {}
            for key, val in request.COOKIES.iteritems():
                params.update({key: val})
            if params:
                request_dict.update({'COOKIES': params})
            params = {}
            for key in self.whitelists.get('meta', []):
                value = request.META.get(key, None)
                if value is not None:
                    params.update({key: value})
            if params:
                request_dict.update({'META': params})
            filtered_traceback_data.update({'request': request_dict})

        for frame in traceback_data.get('frames', []):
            frame.pop('tb', None)

        for key in self.whitelists.get('traceback', []):
            value = traceback_data.get(key, None)
            if value is not None:
                if key == 'settings':
                    value = {}
                    for settings_key in self.whitelists.get(key, []):
                        settings_value = traceback_data[key].get(
                            settings_key, None)
                        if settings_value is not None:
                            value.update({settings_key: settings_value})
                filtered_traceback_data.update({key: value})

        # Pip packages
        installed_packages = get_installed_distributions(local_only=False)
        filtered_traceback_data.update({
            'installed_packages':
            [{'name': package.project_name,
              'version': package.version,
              'location': package.location}
             for package in installed_packages]
        })

        return filtered_traceback_data