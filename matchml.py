from run import db
from models import RealtyModel
from sqlalchemy import and_
import requests

d = {'None': 0, 'block': 1, 'brick': 2, 'monolith': 3, 'monolithBrick': 4, 'old': 5, 'panel': 6, 'stalin': 7,
     'wood': 8}

flats = RealtyModel.query.filter(
    and_(RealtyModel.area_kitchen != None, RealtyModel.building_material_type != None)).limit(2)
URL = "http://realty.pythonanywhere.com/estimate"
count = 0

for i in flats:
    try:
        count += 1
        PARAMS = {'wallsMaterial': d[i.building_material_type], 'floorNumber': i.floor_number,
                  'floorsTotal': i.floors_count, 'totalArea': i.area, 'kitchenArea': i.area_kitchen,
                  'latitude': i.latitude, 'longitude': i.longitude}
        r = requests.get(url=URL, params=PARAMS)

        data = r.json()['Predicted price']
        i.predicted = data

        print (str(count) + '/13290')
    except:
        print('error')
        continue

    if count % 10 == 0:
        db.session.commit()
