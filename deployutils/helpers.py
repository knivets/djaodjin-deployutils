# Copyright (c) 2017, DjaoDjin inc.
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

import datetime

from dateutil.tz import tzlocal
from pytz import utc
import six


def datetime_or_now(dtime_at=None):
    if not dtime_at:
        return datetime.datetime.utcnow().replace(tzinfo=utc)
    if isinstance(dtime_at, six.string_types):
        dtime_at = datetime.datetime.strptime(dtime_at, "%Y-%m-%dT%H:%M:%S.%fZ")
    if isinstance(dtime_at, datetime.date):
        dtime_at = datetime.datetime(
            dtime_at.year, dtime_at.month, dtime_at.day)
    if dtime_at.tzinfo is None:
        dtime_at = dtime_at.replace(tzinfo=utc)
    return dtime_at


def start_of_day(dtime_at=None):
    """
    Returns the local (user timezone) start of day, that's,
    time 00:00:00 for a given datetime
    """
    dtime_at = datetime_or_now(dtime_at)
    return datetime.datetime(dtime_at.year, dtime_at.month,
        dtime_at.day, tzinfo=tzlocal())
