from fastapi import FastAPI, HTTPException, Body
from datetime import datetime
from pymongo import MongoClient
from pydantic import BaseModel
from dotenv import load_dotenv
import urllib
import os

load_dotenv(".env")

DATABASE_NAME = "exceed09"
COLLECTION_NAME = "Locker"
USERNAME = os.getenv('user')
PASSWORD = os.getenv('password')
MONGO_KU_SERVER_URL = f"mongodb://{USERNAME}:{PASSWORD}@mongo.exceed19.online:8443/?authMechanism=DEFAULT"

client = MongoClient(MONGO_KU_SERVER_URL)

db = client[DATABASE_NAME]
collection = db[COLLECTION_NAME]

app = FastAPI()

AVAILABLE = "Available"
UNAVAILABLE = "Unavailable"


def is_available(locker_id: int):
    return list(collection.find({"locker_id": locker_id}))[0]['status'] == AVAILABLE


@app.post("/reserve/{locker_id}/{std_id}")
def reserve_locker(locker_id: int, std_id: int, items: list = Body(), reserve_time: int = Body()):
    if not is_available(locker_id):
        raise HTTPException(400)
    collection.update_one({"locker_id": locker_id},
                          {"$set": {"status": UNAVAILABLE,
                                    "datetime_in": datetime.timestamp(datetime.now()),
                                    "std_id": std_id,
                                    "items": items,
                                    "reserve_time": reserve_time}})


@app.put("/check_out/{locker_id}/{std_id}")
def check_out_locker(locker_id: int, std_id: int):
    pass


@app.post("/check_out/{locker_id}/pay")
def pay_locker_fee(locker_id: int):
    pass


@app.get("/lockers")
def available_lockers():
    result = collection.find({})
    filtered_list = []
    for locker in result:
        if is_available(locker['locker_id']):
            filtered_list.append({"locker_id": locker['locker_id'],
                                  "status": locker['status'],
                                  "left_time": None})
        else:
            filtered_list.append({"locker_id": locker['locker_id'],
                                  "status": locker['status'],
                                  "left_time": (locker['datetime_in'] + (3600 * locker['reserve_time']) -
                                                datetime.timestamp(datetime.now())) / 60})

    return {"result": filtered_list}
