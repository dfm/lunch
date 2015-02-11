#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division, print_function

__all__ = ["setup", "fetch", "build"]

import os
import json
import requests
import numpy as np
import pandas as pd

from geo import propose_position, compute_distance

SETTINGS_FILE = "lunch.json"
VENUES_FILE = "venues.json"
URL = "https://api.foursquare.com/v2/venues/explore"


def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            settings = json.load(f)
    else:
        settings = {}
    return settings


def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)


def get_request_pars():
    settings = load_settings()
    return dict(
        client_id=settings["client_id"],
        client_secret=settings["client_secret"],
        oauth_token=settings["token"],
        v="20150202",
        m="foursquare",
        ll=settings["ll"],
    )


def setup(clobber=False):
    settings = load_settings()

    # Get the app information.
    if (clobber or "client_id" not in settings or
            "client_secret" not in settings):
        print("Enter some info about your app")
        settings["client_id"] = raw_input("Client id: ")
        settings["client_secret"] = raw_input("Client secret: ")

    if clobber or "token" not in settings:
        print("Go to the following URL and authorize the app:")
        print("https://foursquare.com/oauth2/authenticate"
              "?client_id={0}&response_type=code&redirect_uri=http://dfm.io"
              .format(settings["client_id"]))
        code = raw_input("Enter the code from the resulting URL: ")

        # Get the token.
        pars = dict(
            client_id=settings["client_id"],
            client_secret=settings["client_secret"],
            grant_type="authorization_code",
            redirect_uri="http://dfm.io",
            code=code,
        )
        r = requests.get("https://foursquare.com/oauth2/access_token",
                         params=pars)
        settings["token"] = r.json()["access_token"]

    if clobber or "ll" not in settings:
        print("You need to give your coordinates...")
        settings["ll"] = raw_input("Where are you located (lat,lng): ")

    save_settings(settings)


def fetch(clobber=False, ntot=1000, max_page=5, page=50, sig=0.5):
    # Set up the API access.
    setup()

    # Set up the request parameters.
    pars = get_request_pars()
    pars["section"] = "food"
    pars["day"] = "any"
    pars["time"] = "12"
    pars["limit"] = page
    lat, lng = map(float, pars["ll"].split(","))

    # Get the existing list if it's available.
    if clobber or not os.path.exists(VENUES_FILE):
        venues = dict(ids=[], venues=[])
    else:
        with open(VENUES_FILE, "r") as f:
            venues = json.load(f)

    # Paginate!
    while len(venues["venues"]) < ntot:
        pars["ll"] = "{0},{1}".format(*(propose_position(lat, lng, sig)))
        for i in range(0, max_page):
            if i:
                pars["offset"] = i * page
            else:
                pars.pop("offset", None)
            r = requests.get(URL, params=pars)
            if r.status_code != requests.codes.ok:
                r.raise_for_status()

            # Loop through the results and save them to the list of venues.
            data = r.json()
            for group in data["response"]["groups"]:
                for v in group["items"]:
                    id_ = v["venue"]["id"]
                    if id_ not in venues["ids"]:
                        loc = v["venue"]["location"]
                        lat2 = loc["lat"]
                        lng2 = loc["lng"]
                        v["distance"] = compute_distance(lat, lng, lat2, lng2)
                        venues["venues"].append(v)
                        venues["ids"].append(id_)

            # Save the current state of the list.
            with open(VENUES_FILE, "w") as f:
                json.dump(venues, f, indent=2)

            print(pars["ll"], i, len(venues["venues"]))

    return venues


def build(clobber=False):
    with open(VENUES_FILE, "r") as f:
        venues = json.load(f)

    # Define the elements that we will extract.
    elements = [
        ("id", ["venue", "id"]),
        ("name", ["venue", "name"]),
        ("address", ["venue", "location", "formattedAddress", 0]),
        ("photos", ["venue", "photos", "count"]),
        ("price", ["venue", "price", "tier"]),
        ("distance", ["distance"]),
        ("rating", ["venue", "rating"]),
        ("rating_signal", ["venue", "ratingSignals"]),
        ("checkins", ["venue", "stats", "checkinsCount"]),
        ("tips", ["venue", "stats", "tipCount"]),
        ("users", ["venue", "stats", "usersCount"]),
        ("category", ["venue", "categories", 0, "shortName"]),
    ]

    # Initialize the container for the data.
    data = dict((el, []) for el, _ in elements)
    data["good"] = []

    for v in venues["venues"]:
        for el, path in elements:
            val = v
            for p in path:
                try:
                    val = val[p]
                except KeyError:
                    val = None
                    break
            data[el].append(val)
        good = v.get("good", None)
        if good is None:
            good = 0
        else:
            good = 1 if good else -1
        data["good"].append(good)

    # Sort the data.
    df = pd.DataFrame(data)
    df.rating = df["rating"].fillna(0.0)
    df.price = df["price"].fillna(5.0)
    df["score"] = -0.5 * ((df.distance/0.6) ** 2 +
                          ((df.rating - 10)/0.5) ** 2 +
                          (df.price) ** 2)

    # We don't want dessert for lunch.
    bads = ["Desserts", "Donuts", "Ice Cream", "Bakery", "Cupcakes", u"Café",
            "Snacks", "Bubble Tea"]
    m = df.category != bads[0]
    for b in bads[1:]:
        m &= df.category != b
    df.score = df["score"].where(m, -np.inf)
    cols = ["completed", "name", "address", "category", "distance", "rating",
            "price", "id"]
    final = df.sort("score")[-100:]
    final["random"] = np.random.rand(len(final))
    final["completed"] = np.zeros(len(final), dtype=bool)
    final.sort("random")[cols].to_csv("lunch.csv", encoding="utf-8",
                                      index=False)


if __name__ == "__main__":
    import sys

    if "setup" in sys.argv:
        setup(clobber="clobber" in sys.argv)
        sys.exit(0)

    elif "fetch" in sys.argv:
        fetch(clobber="clobber" in sys.argv)
        sys.exit(0)

    elif "build" in sys.argv:
        build(clobber="clobber" in sys.argv)
        sys.exit(0)
