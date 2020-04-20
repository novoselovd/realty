import urllib.request, json
from models import RealtyModel

def update_db(price1, deal_id):
	with urllib.request.urlopen("https://rest-app.net/api-cian/ads?login=tbago@yandex.ru&token=3110c1024b85d2dcfc808b6d4aebc3ce&category_id=1&deal_id=" + str(deal_id) + "&region_id=1&price1=" + str(price1)) as url:
		data = json.loads(url.read().decode())
		for i in data['data']:
			if RealtyModel.find_by_id(i['Id']):
				continue
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
				area = float(i['area']),
				latitude = float(i['coords']['lat']),
				longitude = float(i['coords']['lng'])
			)

			new_realty.save_to_db()

