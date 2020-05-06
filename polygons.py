import json
import numpy as np
from models import DistrictModel, RealtyModel, TempModel
from numba import jit

def parse_polygons():
    # read file
    with open('mo.json', 'r') as myfile:
        data=myfile.read()

    # parse file
    obj = json.loads(data)

    # show values
    for i in obj['features']:
        new_dist = DistrictModel(
            okato_ao=i['properties']['OKATO_AO'],
            name=i['properties']['NAME'],
            type=i['geometry']['type'],
            coordinates=i['geometry']['coordinates'][0]
        )

        new_dist.save_to_db()


@jit(nopython=True)
def ray_tracing(x,y,poly):
    n = len(poly)
    inside = False
    p2x = 0.0
    p2y = 0.0
    xints = 0.0
    p1x,p1y = poly[0]
    for i in range(n+1):
        p2x,p2y = poly[i % n]
        if y > min(p1y,p2y):
            if y <= max(p1y,p2y):
                if x <= max(p1x,p2x):
                    if p1y != p2y:
                        xints = (y-p1y)*(p2x-p1x)/(p2y-p1y)+p1x
                    if p1x == p2x or x <= xints:
                        inside = not inside
        p1x,p1y = p2x,p2y

    return inside

def check_point_is_in_polygon():
    districts = DistrictModel.query.all()
    flats = RealtyModel.query.all()
    res = 0

    for d in districts:
        for f in flats:
            if d.type == "Polygon":
                if ray_tracing(f.longitude, f.latitude, np.array(d.coordinates)):
                    res+=1
                    # f.dist = d.id
                    continue
            elif d.type == "MultiPolygon":
                for p in d.coordinates:
                    if ray_tracing(f.longitude, f.latitude, np.array(p)):
                        res += 1
                        # f.dist = d.id
                        continue
        print(res)

    RealtyModel.update_dist()

def count_avg_sq():
    districts = DistrictModel.query.all()
    flats = RealtyModel.query.all()

    for d in districts:
        sum = 0.0
        count = 0
        for f in flats:
            if f.type == 1:
                if d.id == f.dist:
                    sum += f.price/f.area
                    count += 1

        if count > 0:
            d.avg_sq = sum/count

    RealtyModel.update_dist()


def count_avg_coeff():
    districts = DistrictModel.query.all()
    flats = RealtyModel.query.all()
    flats_with_coeffs = TempModel.query.all()

    for fwc in flats_with_coeffs:
        for f in flats:
            if fwc.id == f.id:
                fwc.dist = f.dist

    RealtyModel.update_dist()

    for d in districts:
        coeff = 0
        count = 0
        for fwc in flats_with_coeffs:
            if d.id == fwc.dist:
                coeff += fwc.coeff
                count += 1

        if count > 0:
            d.avg_coeff = int(coeff/count)

    RealtyModel.update_dist()
