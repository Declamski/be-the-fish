"""Talks to the sites service over HTTP.

This is the seam between the two services: dives never reads the sites database,
it asks the sites API instead. SITES_URL says where the sites service is, and every
call gives up after SITES_TIMEOUT_S seconds.
"""
import json
import urllib.error
import urllib.parse
import urllib.request

import flask


class SitesUnavailable(Exception):
    """The sites service could not be reached, was too slow, or answered with an error."""


def get_json(path):
    """GET SITES_URL + path and return the decoded JSON body.

    A 404 is passed on as it is (it is a real answer: "no such site"). Anything else
    that goes wrong becomes SitesUnavailable, so callers only have one error to handle.
    """
    url = flask.current_app.config["SITES_URL"] + path
    timeout = flask.current_app.config["SITES_TIMEOUT_S"]
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise
        print("Sites unavailable:", path, "answered", e.code, flush=True)
        raise SitesUnavailable("sites answered " + str(e.code)) from e
    except (OSError, ValueError) as e:
        # OSError: connection refused, unknown host, or the timeout ran out.
        # ValueError: the answer was not valid JSON.
        print("Sites unavailable:", path, e, flush=True)
        raise SitesUnavailable(str(e)) from e


def search_sites(query):
    """Sites whose name or location contains `query`. Each has id, name, location, description, label."""
    return get_json("/api/sites?" + urllib.parse.urlencode({"q": query}))


def get_site(site_id):
    """The site, or None if the sites service answers 404 (no such site).
    Raises SitesUnavailable if sites cannot answer."""
    try:
        return get_json("/api/sites/" + str(int(site_id)))
    except urllib.error.HTTPError:
        # get_json only lets a 404 through, so this means "no such site".
        return None


def site_exists(site_id):
    return get_site(site_id) is not None


def get_site_label(site_id):
    """e.g. "Blue Hole - Gozo, Malta", or None if the site does not exist."""
    site = get_site(site_id)
    if site is None:
        return None
    return site["label"]
