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


def calculate_fee(locker):
    penalty_fee = 0
    overtime = (locker['datetime_in'] + (3600 * locker['reserve_time']) - datetime.timestamp(datetime.now())) / 60
    if overtime < 0:
        penalty_fee += round(abs(overtime) / 10, 0) * 20
    reserve_fee = 0
    check_hour = locker['reserve_time'] - 2
    if check_hour > 0:
        reserve_fee += check_hour * 5
    return penalty_fee, reserve_fee


@app.put("/reserve/{locker_id}/{std_id}")
def reserve_locker(locker_id: int, std_id: int, items: list = Body(), reserve_time: int = Body()):
    if not (0 < locker_id < 7) or reserve_time <= 0  or len(items) == 0:
        raise HTTPException(400, detail="invalid values")
    if not is_available(locker_id):
        raise HTTPException(400, detail="locker unavailable")

    collection.update_one({"locker_id": locker_id},
                          {"$set": {"status": UNAVAILABLE,
                                    "datetime_in": datetime.timestamp(datetime.now()),
                                    "std_id": std_id,
                                    "items": items,
                                    "reserve_time": reserve_time}})
    return {"message": "success"}


@app.get("/check_out/{locker_id}/{std_id}")
def check_out_locker(locker_id: int, std_id: int):
    result = list(collection.find({"locker_id": locker_id, "std_id": std_id}))
    if len(result) == 0:
        raise HTTPException(404, detail="not matching lockers and student id")
    locker = result[0]

    penalty_fee, reserve_fee = calculate_fee(locker)

    return {"total_fee": reserve_fee + penalty_fee, "reserve_fee": reserve_fee, "penalty_fee": penalty_fee,
            "reserve_time": locker['reserve_time']}


@app.put("/check_out/{locker_id}/{std_id}/pay")
def pay_locker_fee(locker_id: int, std_id: int, paid: dict = Body()):
    result = list(collection.find({"locker_id": locker_id, "std_id": std_id}))
    if len(result) == 0:
        raise HTTPException(404, detail="not matching lockers and student id")
    locker = result[0]
    penalty_fee, reserve_fee = calculate_fee(locker)

    if penalty_fee + reserve_fee > paid['paid']:
        raise HTTPException(400)

    collection.update_one({"locker_id": locker_id},
                          {"$set": {"status": AVAILABLE,
                                    "datetime_in": 0,
                                    "std_id": 0,
                                    "items": [],
                                    "reserve_time": 0}})
    return {"change": paid['paid'] - penalty_fee + reserve_fee, "items": locker["items"]}


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
