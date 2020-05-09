import urllib.request, json
from models import RealtyModel

def update_db(price1, deal_id):
	count = 0
	with urllib.request.urlopen("https://rest-app.net/api-cian/ads?login=tbago@yandex.ru&token=3110c1024b85d2dcfc808b6d4aebc3ce&category_id=1&deal_id=" + str(deal_id) + "&region_id=1&price1=" + str(price1)) as url:
		data = json.loads(url.read().decode())
		for i in data['data']:
			if RealtyModel.find_by_id(i['Id']):
				continue
			try:
				new_realty = RealtyModel(
					id = i['Id'],
					url = i['url'],
					type = deal_id,
					price = float(i['price']),
					phone = i['phone'],
					metro = i['metro'],
					rooms_count = i['rooms_count'],
					floor_number = i['floor_number'],
					floors_count = i['floors_count'],
					images = i['images'],
					city = i['city'],
					address = i['address'],
					description = i['description'],
					area = float(i['area']),
					latitude = float(i['coords']['lat']),
					longitude = float(i['coords']['lng']),
					area_kitchen = i['area_kitchen'],
					time_publish = i['time_publish'],
					building_material_type = i['building_material_type'],
					status = 1
				)

				new_realty.save_to_db()
			except KeyError as e:
				new_realty = RealtyModel(
					id=i['Id'],
					url=i['url'],
					type=deal_id,
					price=float(i['price']),
					phone=i['phone'],
					metro=i['metro'],
					rooms_count=i['rooms_count'],
					floor_number=i['floor_number'],
					floors_count=i['floors_count'],
					images=i['images'],
					city=i['city'],
					address=i['address'],
					description=i['description'],
					area=float(i['area']),
					latitude=float(i['coords']['lat']),
					longitude=float(i['coords']['lng']),
					area_kitchen=i['area_kitchen'],
					time_publish=i['time_publish'],
					building_material_type=None,
					status=1
				)

				new_realty.save_to_db()

			except Exception as er:
				print(e.__doc__)
				print(e.message)
				continue



