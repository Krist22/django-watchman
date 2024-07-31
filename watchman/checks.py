# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import uuid
from os.path import join

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.mail import EmailMessage
from django.db import connections
from django.core.exceptions import SuspiciousFileOperation

from watchman import settings as watchman_settings
from watchman import utils
from watchman.decorators import check



def _check_caches(caches):
    return [_check_cache(cache) for cache in sorted(caches)]


@check
def _check_cache(cache_name):
    key = "django-watchman-{}".format(uuid.uuid4())
    value = "django-watchman-{}".format(uuid.uuid4())

    cache = utils.get_cache(cache_name)

    cache.set(key, value)
    cache.get(key)
    cache.delete(key)
    return {cache_name: {"ok": True}}


def _check_databases(databases):
    return [_check_database(database) for database in sorted(databases)]


@check
def _check_database(database):
    connection = connections[database]
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    return {database: {"ok": True}}


@check
def _check_email():
    headers = {"X-DJANGO-WATCHMAN": True}
    headers.update(watchman_settings.WATCHMAN_EMAIL_HEADERS)
    email = EmailMessage(
        "django-watchman email check",
        "This is an automated test of the email system.",
        watchman_settings.WATCHMAN_EMAIL_SENDER,
        watchman_settings.WATCHMAN_EMAIL_RECIPIENTS,
        headers=headers,
    )
    email.send()
    return {"ok": True}


@check
def _check_storage():
    try:
        filename = "django-watchman-{}.txt".format(uuid.uuid4())
        base_dir = watchman_settings.WATCHMAN_STORAGE_PATH
        path = safe_join(base_dir, filename)

        # Check that the path is secure and in the authorized directory
        if not path.startswith(base_dir):
            raise SuspiciousFileOperation("Attempted road crossing detected.")

        content = b"django-watchman test file"
        saved_path = default_storage.save(path, ContentFile(content))
       
        file_size = default_storage.size(saved_path)
        file_content = default_storage.open(saved_path).read()
        default_storage.delete(saved_path)
        
        return {"ok": True}
    except SuspiciousFileOperation:
        raise SuspiciousFileOperation("Attempted road crossing detected.")
    except Exception as e:
        return {"error": str(e)}


def caches():
    return {"caches": _check_caches(watchman_settings.WATCHMAN_CACHES)}


def databases():
    return {"databases": _check_databases(watchman_settings.WATCHMAN_DATABASES)}


def email():
    return {"email": _check_email()}


def storage():
    return {"storage": _check_storage()}
