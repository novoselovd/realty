import urllib.request, json
from models import SellModel, RentModel

def update_db():
	with urllib.request.urlopen("https://rest-app.net/api-cian/ads?login=tbago@yandex.ru&token=3110c1024b85d2dcfc808b6d4aebc3ce&category_id=1&deal_id=1&region_id=1") as url:
		data = json.loads(url.read().decode())
		for i in data['data']:
			if SellModel.find_by_id(i['Id']):
				continue
			new_realty = SellModel(
				id = i['Id'],
				price = float(i['price']),
				address = i['address'],
				area = float(i['area']),
				latitude = float(i['coords']['lat']),
				longitude = float(i['coords']['lng'])
			)

			new_realty.save_to_db()
