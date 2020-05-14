import requests

# # api-endpoint
# URL = "http://realty.pythonanywhere.com/update"
#
# # defining a params dict for the parameters to be sent to the API
# PARAMS1 = {'deal_id': 1, 'price': 0}
# PARAMS2 = {'deal_id': 2, 'price': 0}
#
# # sending get request and saving the response as response object
# r1 = requests.get(url=URL, params=PARAMS1)
# r2 = requests.get(url=URL, params=PARAMS2)


# api-endpoint
URL1 = "http://realty.pythonanywhere.com/count"
URL2 = "http://realty.pythonanywhere.com/polygons"

r1 = requests.get(url=URL1)

r2 = requests.get(url=URL2)


