"""
A minimal Sentry client.

Loosely based on sentry-sdk v1.5.8 (https://github.com/getsentry/sentry-python).
sentry-sdk is:
  Copyright (c) 2018 Sentry (https://sentry.io) and individual contributors.
  Licensed under the BSD-2-Clause License.
"""
import datetime
import gzip
import json
import os
import socket
import uuid
from typing import Optional
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

__version__ = "0.1"
USER_AGENT = f"smontry/{__version__}"


def _get_url_and_auth(
    sentry_dsn: str,
    url_type: str,
    *,
    client: Optional[str] = None,
    timestamp: Optional[datetime.datetime] = None,
    version: int = 7,
):
    """
    Parse a Sentry DSN into an API URL and an authentication header.
    """
    if not sentry_dsn:
        raise ValueError("sentry_dsn not set")
    parts = urlsplit(sentry_dsn)
    assert parts.username
    path = parts.path.rsplit("/", 1)
    project_id = str(int(path.pop()))
    path = "/".join(path) + "/"
    url = f"{parts.scheme}://{parts.hostname}{path}api/{project_id}/{url_type}/"
    rv = [("sentry_key", parts.username), ("sentry_version", version)]
    if timestamp is not None:
        rv.append(("sentry_timestamp", str(timestamp.timestamp())))
    if client is not None:
        rv.append(("sentry_client", client))
    if parts.password is not None:
        rv.append(("sentry_secret", parts.password))
    parts = ", ".join(f"{key}={value}" for key, value in rv)
    auth = f"Sentry {parts}"
    return (url, auth)


def _store_event(
    sentry_dsn: str,
    event: dict,
) -> bytes:
    """
    Send a Store API request. May raise.
    """
    url, auth = _get_url_and_auth(
        sentry_dsn,
        url_type="store",
        timestamp=datetime.datetime.utcnow(),
        client=USER_AGENT,
    )
    body = gzip.compress(json.dumps(event).encode("utf-8"))
    headers = {
        "Content-Encoding": "gzip",
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
        "X-Sentry-Auth": auth,
    }
    req = Request(
        url,
        body,
        headers,
        method="POST",
    )
    resp = urlopen(req)
    return resp.fp.read()


def _augment_event(event: dict) -> dict:
    event = event.copy()
    if "server_name" not in event and hasattr(socket, "gethostname"):
        event["server_name"] = socket.gethostname()
    if "environment" not in event:
        event["environment"] = os.environ.get("SENTRY_ENVIRONMENT") or "production"
    if "platform" not in event:
        event["platform"] = "python"
    if "timestamp" not in event:
        event["timestamp"] = datetime.datetime.utcnow().strftime(
            "%Y-%m-%dT%H:%M:%S.%fZ"
        )
    return event


def _get_default_sentry_dsn() -> str:
    return os.environ.get("SENTRY_DSN")


def capture_message(
    message: str,
    level: str = "info",
    *,
    sentry_dsn: Optional[str] = None,
):
    """
    Send a message event with the given level.
    """
    return _store_event(
        sentry_dsn or _get_default_sentry_dsn(),
        _augment_event({"message": message, "level": level}),
    )


if __name__ == "__main__":
    capture_message(
        f"This is Smontry, hello?! {uuid.uuid4()}",
    )
