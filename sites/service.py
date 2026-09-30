from . import repository

# Sites are only added by the app's admin, by editing this list.
# They are added at startup if they are not in the database yet.
# Well-known public dive sites only - never a private/real personal spot.
SEED_SITES = [
    {
        "name": "Bloody Bay Wall",
        "location": "Little Cayman, Cayman Islands",
        "description": "A vertical wall that starts in shallow water and drops far "
                       "beyond recreational depth. Known for turtles, groupers and sponges.",
    },
    {
        "name": "USS Kittiwake",
        "location": "Grand Cayman, Cayman Islands",
        "description": "A former US Navy submarine rescue ship, sunk on purpose in 2011 "
                       "as an artificial reef. Shallow enough for snorkellers to see the top.",
    },
    {
        "name": "Stingray City",
        "location": "Grand Cayman, Cayman Islands",
        "description": "A shallow sandbar in North Sound where southern stingrays gather.",
    },
    {
        "name": "Blue Hole",
        "location": "Dahab, Egypt",
        "description": "A deep sinkhole next to the shore, famous with freedivers. "
                       "The Arch at around 55 m is a well-known and dangerous landmark.",
    },
    {
        "name": "Blue Hole",
        "location": "Gozo, Malta",
        "description": "A rock pool that leads down through an arch into the open sea.",
    },
    {
        "name": "SS Thistlegorm",
        "location": "Red Sea, Egypt",
        "description": "A British cargo ship sunk in 1941, still carrying its wartime "
                       "cargo of trucks, motorbikes and locomotives.",
    },
    {
        "name": "Silfra",
        "location": "Thingvellir, Iceland",
        "description": "A fissure between the North American and Eurasian plates, "
                       "filled with very clear and very cold glacial water.",
    },
    {
        "name": "Dean's Blue Hole",
        "location": "Long Island, Bahamas",
        "description": "One of the deepest known blue holes, and a venue for "
                       "international freediving competitions.",
    },
]


def clean_text(text):
    """Trim the ends and turn any run of spaces inside into a single space."""
    return " ".join(text.split())


def create_site(conn, name, location, description=None):
    if name is None or not name.strip():
        raise ValueError("Site name is required")
    if location is None or not location.strip():
        raise ValueError("Site location is required")

    name = clean_text(name)
    location = clean_text(location)

    # Two sites may share a name, but the same name in the same location is one site.
    if repository.find_site(conn, name, location) is not None:
        raise ValueError("This site already exists")

    return repository.insert_site(conn, name, location, description)


def seed_sites(conn):
    """Add every site in SEED_SITES that is not in the database yet. Returns how many were added."""
    added = 0
    for site in SEED_SITES:
        if repository.find_site(conn, site["name"], site["location"]) is None:
            create_site(conn, site["name"], site["location"], site["description"])
            added = added + 1
    return added


def search_sites(conn, query):
    """Return the sites whose name or location contains `query`, ignoring case.

    An empty query returns every site.
    """
    all_sites = repository.list_sites(conn)
    if query is None or not query.strip():
        return all_sites

    query = query.strip().lower()
    matches = []
    for site in all_sites:
        if query in site["name"].lower() or query in site["location"].lower():
            matches.append(site)
    return matches


def get_site(conn, site_id):
    site = repository.get_site(conn, site_id)
    if site is None:
        raise ValueError("Site not found")
    return site


# --- Public functions for other domains (the seam for Assignment 2) ---

def site_exists(conn, site_id):
    return repository.get_site(conn, site_id) is not None


def get_site_label(conn, site_id):
    """Return e.g. "Blue Hole - Gozo, Malta", or None if the site does not exist."""
    site = repository.get_site(conn, site_id)
    if site is None:
        return None
    return site["name"] + " - " + site["location"]
