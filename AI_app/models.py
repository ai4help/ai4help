from django.db import models
from pymongo import MongoClient
client = MongoClient("mongodb+srv://ai4help:PEXiXEq%23Am3HxHk@cluster0.t086sbe.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")

new_database = 'ai4help'

db = client[new_database]

collection_names = db.list_collection_names()

def get_collection():
    if not collection_names:
        new_collection = db['conv']
        return new_collection
    else:
        return  db['conv']

def get_doc_collection():
    if not collection_names:
        new_collection = db['doc_data']
        return new_collection
    else:
        return  db['doc_data']