from django.test import TestCase

from pymongo import MongoClient

uri = "mongodb://titans:TitansCareer@ac-72om8zm-shard-00-00.tu1atbz.mongodb.net:27017,ac-72om8zm-shard-00-01.tu1atbz.mongodb.net:27017,ac-72om8zm-shard-00-02.tu1atbz.mongodb.net:27017/?replicaSet=atlas-iov063-shard-0&ssl=true&authSource=admin"
client = MongoClient(uri, ssl=True, ssl_cert_reqs='CERT_NONE')
db = client['titans']

try:
    collections = db.list_collection_names()
    print("Connected to MongoDB. Collections:", collections)
except Exception as e:
    print("Failed to connect to MongoDB:", e)

