from django.db import models
from pymongo import MongoClient
from dotenv import load_dotenv
import os
load_dotenv()

client = MongoClient(os.environ.get('MongoDB'))

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