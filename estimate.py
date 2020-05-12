import xgboost as xgb
import pandas as pd
import dill as pickle
import numpy as np
from geopy.distance import geodesic
import math
from sklearn.metrics import mean_absolute_error, r2_score, median_absolute_error
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder

filename1 = 'rf_model.pk'
filename2 = 'xgb_model.pk'


def get_azimuth(latitude, longitude):
    rad = 6372795

    llat1 = city_center_coordinates[0]
    llong1 = city_center_coordinates[1]
    llat2 = latitude
    llong2 = longitude

    lat1 = llat1 * math.pi / 180.
    lat2 = llat2 * math.pi / 180.
    long1 = llong1 * math.pi / 180.
    long2 = llong2 * math.pi / 180.

    cl1 = math.cos(lat1)
    cl2 = math.cos(lat2)
    sl1 = math.sin(lat1)
    sl2 = math.sin(lat2)
    delta = long2 - long1
    cdelta = math.cos(delta)
    sdelta = math.sin(delta)

    y = math.sqrt(math.pow(cl2 * sdelta, 2) + math.pow(cl1 * sl2 - sl1 * cl2 * cdelta, 2))
    x = sl1 * sl2 + cl1 * cl2 * cdelta
    ad = math.atan2(y, x)

    x = (cl1 * sl2) - (sl1 * cl2 * cdelta)
    y = sdelta * cl2
    z = math.degrees(math.atan(-y / x))

    if (x < 0):
        z = z + 180.

    z2 = (z + 180.) % 360. - 180.
    z2 = - math.radians(z2)
    anglerad2 = z2 - ((2 * math.pi) * math.floor((z2 / (2 * math.pi))))
    angledeg = (anglerad2 * 180.) / math.pi

    return round(angledeg, 2)


def mean_absolute_percentage_error(y_true, y_pred):
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    return np.mean(np.abs((y_true - y_pred) / y_true)) * 100


def median_absolute_percentage_error(y_true, y_pred):
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    return np.median(np.abs((y_true - y_pred) / y_true)) * 100


def print_metrics(prediction, val_y):
    val_mae = mean_absolute_error(val_y, prediction)
    median_AE = median_absolute_error(val_y, prediction)
    r2 = r2_score(val_y, prediction)

    print('')
    print('R\u00b2: {:.2}'.format(r2))
    print('')
    print('Средняя абсолютная ошибка: {:.3} %'.format(mean_absolute_percentage_error(val_y, prediction)))
    print('Медианная абсолютная ошибка: {:.3} %'.format(median_absolute_percentage_error(val_y, prediction)))


file_path = 'https://raw.githubusercontent.com/maxbobkov/ml_moscow_flats/master/moscow_dataset_2020.csv'
df = pd.read_csv(file_path)

df['priceMetr'] = df['price']/df['totalArea']

city_center_coordinates = [55.7522, 37.6156]
df['distance'] = list(map(lambda x, y: geodesic(city_center_coordinates, [x, y]).meters, df['latitude'], df['longitude']))
df['azimuth'] = list(map(lambda x, y: get_azimuth(x, y), df['latitude'], df['longitude']))

df = df.loc[(df['distance'] < 40000)]

df['priceMetr'] = df['priceMetr'].round(0)
df['distance'] = df['distance'].round(0)
df['azimuth'] = df['azimuth'].round(0)


first_quartile = df.quantile(q=0.25)
third_quartile = df.quantile(q=0.75)
IQR = third_quartile - first_quartile
outliers = df[(df > (third_quartile + 1.5 * IQR)) | (df < (first_quartile - 1.5 * IQR))].count(axis=1)
outliers.sort_values(axis=0, ascending=False, inplace=True)


outliers = outliers.head(3000)
df.drop(outliers.index, inplace=True)


categorical_columns = df.columns[df.dtypes == 'object']
labelencoder = LabelEncoder()
for column in categorical_columns:
    df[column] = labelencoder.fit_transform(df[column])


y = df['priceMetr']

features = [
            'wallsMaterial',
            'floorNumber',
            'floorsTotal',
            'totalArea',
            'kitchenArea',
            'distance',
            'azimuth'
           ]


X = df[features]

train_X, val_X, train_y, val_y = train_test_split(X, y, random_state=1)


rf_model = RandomForestRegressor(n_estimators=2000,
                                 n_jobs=-1,
                                 bootstrap=False,
                                 criterion='mse',
                                 max_features=3,
                                 random_state=1,
                                 max_depth=55,
                                 min_samples_split=5
                                 )

rf_model.fit(train_X, train_y)

rf_prediction = rf_model.predict(val_X).round(0)

print_metrics(rf_prediction, val_y)


xgb_model = xgb.XGBRegressor(objective ='reg:gamma',
                             learning_rate = 0.01,
                             max_depth = 45,
                             n_estimators = 2000,
                             nthread = -1,
                             eval_metric = 'gamma-nloglik',
                             )

xgb_model.fit(train_X, train_y)

xgb_prediction = xgb_model.predict(val_X).round(0)

print_metrics(xgb_prediction, val_y)


prediction = rf_prediction * 0.5 + xgb_prediction * 0.5

print_metrics(prediction, val_y)


importances = rf_model.feature_importances_
std = np.std([tree.feature_importances_ for tree in rf_model.estimators_],
             axis=0)
indices = np.argsort(importances)[::-1]

print('here')

with open('test1.pk', 'wb') as file:
    pickle.dump(xgb_model, file)

