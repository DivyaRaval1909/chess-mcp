from pymongo import ASCENDING, MongoClient

from config import MONGODB_DATABASE, MONGODB_URI


client = MongoClient(
    MONGODB_URI,
    serverSelectionTimeoutMS=3000,
    tz_aware=True,
)
database = client[MONGODB_DATABASE]
users = database.users
games = database.games
rooms = database.rooms


def initialise_database():
    client.admin.command("ping")
    users.create_index([("username", ASCENDING)], unique=True)
    games.create_index([("players.white_user_id", ASCENDING)])
    games.create_index([("players.black_user_id", ASCENDING)])
    rooms.create_index([("share_code", ASCENDING)], unique=True)
