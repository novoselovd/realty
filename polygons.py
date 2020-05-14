import json
import numpy as np
from models import DistrictModel, RealtyModel, TempModel, AoModel
from numba import jit
import numpy as np

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
    flats = RealtyModel.query.filter(RealtyModel.dist == None)
    res = 0

    for d in districts:
        for f in flats:
            if d.type == "Polygon":
                if ray_tracing(f.longitude, f.latitude, np.array(d.coordinates)):
                    print('here')
                    res+=1
                    f.dist = d.id
                    continue
            elif d.type == "MultiPolygon":
                for p in d.coordinates:
                    if ray_tracing(f.longitude, f.latitude, np.array(p)):
                        print('here')
                        res += 1
                        f.dist = d.id
                        continue


    RealtyModel.update_dist()
    print(RealtyModel.query.filter(RealtyModel.dist == None).count())

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


def parse_ao():
    # with open('ao.json', 'r') as myfile:
    #     data=myfile.read()
    #
    # obj = json.loads(data)
    #
    # for i in obj['features']:
    #     new_ao = AoModel(
    #         id=i['properties']['OKATO'],
    #         name=i['properties']['NAME'],
    #         type=i['geometry']['type']
    #     )
    #
    #     new_ao.save_to_db()
    #
    districts = DistrictModel.query.all()
    ao = AoModel.query.all()

    for a in ao:
        sumsq = 0.0
        sumcoeff = 0
        countsq = 0
        countcoeff = 0
        for d in districts:
            if a.id == d.okato_ao:
                if d.avg_sq:
                    sumsq += d.avg_sq
                    countsq += 1
                if d.avg_coeff:
                    sumcoeff += d.avg_coeff
                    countcoeff += 1

        if countsq != 0:
            a.avg_sq = sumsq/countsq

        if countcoeff != 0:
            a.avg_coeff = int(sumcoeff/countcoeff)


    RealtyModel.update_dist()

# def fix_kuncevo():
#     districts = DistrictModel.query.all()
#
#     for i in districts:
#         if i.id == 146:
#             i.type = 'Polygon'
#             i.coordinates = [[37.3772208,55.7290976],[37.3757376,55.7318886],[37.3747854,55.7318705],[37.3741846,55.7321483],[37.3739806,55.7325229],[37.3739593,55.7327464],[37.3739806,55.7329337],[37.3743348,55.7337313],[37.3744902,55.734311],[37.3741308,55.7351085],[37.3739484,55.7356339],[37.3733799,55.7368298],[37.3713199,55.7408223],[37.3703866,55.7425678],[37.3699681,55.7434919],[37.3692171,55.7453458],[37.3689382,55.7459858],[37.3685841,55.747846],[37.3683159,55.7501042],[37.3682944,55.7516257],[37.3683964,55.7538054],[37.3685439,55.7587108],[37.3684956,55.7595226],[37.3685492,55.760081],[37.3685868,55.7604917],[37.3684527,55.7612823],[37.3684901,55.762559],[37.3681522,55.7627311],[37.367868,55.7630359],[37.367927,55.7632169],[37.3680235,55.7633709],[37.3681308,55.7636334],[37.3681576,55.7638146],[37.3680986,55.7639173],[37.3680074,55.764062],[37.3679108,55.7641405],[37.3676158,55.7642129],[37.3673422,55.7642614],[37.3667306,55.7643247],[37.3665322,55.7642914],[37.3663068,55.7642914],[37.3660118,55.7642523],[37.3657328,55.7642069],[37.3656203,55.7644122],[37.365824,55.7644392],[37.3663068,55.7646143],[37.366516,55.7648708],[37.366543,55.7649463],[37.3664034,55.7649312],[37.3664892,55.7651002],[37.3665912,55.7653869],[37.3667254,55.7656223],[37.3669024,55.7658004],[37.3671062,55.7659361],[37.3673852,55.7661445],[37.3681094,55.7666152],[37.3683454,55.766748],[37.3686082,55.7669381],[37.3686565,55.7684922],[37.3686297,55.7687037],[37.3685278,55.7688636],[37.3678948,55.7692919],[37.3671706,55.7697477],[37.3668756,55.7697989],[37.3666878,55.7698924],[37.366516,55.7700073],[37.3664518,55.7701127],[37.366398,55.7702456],[37.3664142,55.7703692],[37.366618,55.770677],[37.3667574,55.7708369],[37.3667574,55.7709123],[37.366677,55.7709728],[37.3665698,55.771021],[37.3663177,55.7711598],[37.3658349,55.7713863],[37.3651885,55.7718299],[37.3527002,55.7776712],[37.3523139,55.7774539],[37.3524427,55.7738092],[37.350426,55.7727835],[37.3486232,55.7707194],[37.3484086,55.7700918],[37.3476791,55.7700918],[37.3472073,55.7694765],[37.3458337,55.7695365],[37.3445463,55.7698021],[37.3445894,55.7685833],[37.3402551,55.7689213],[37.3383239,55.7692591],[37.3404696,55.7703697],[37.3391821,55.7706111],[37.3394825,55.7707317],[37.3383235,55.771335],[37.3366069,55.7712867],[37.3323154,55.7719626],[37.3321441,55.7713595],[37.3321441,55.7679315],[37.3304273,55.7677864],[37.3296119,55.767376],[37.3207496,55.7668445],[37.3188613,55.7695002],[37.3160718,55.769138],[37.3126814,55.7690656],[37.3099349,55.769983],[37.3076604,55.7709485],[37.3062012,55.7711899],[37.3049997,55.7712624],[37.304828,55.7720107],[37.3019097,55.7737247],[37.3012231,55.7745213],[37.3022101,55.7748107],[37.3040985,55.7747383],[37.3090337,55.7756558],[37.3153641,55.774618],[37.3223375,55.7769108],[37.323024,55.7767418],[37.3242794,55.7777313],[37.3246227,55.7782261],[37.3251377,55.7785883],[37.3254166,55.7790829],[37.3268059,55.7793363],[37.3277715,55.7800002],[37.3284153,55.78108],[37.3278359,55.7812369],[37.3223052,55.7833063],[37.3182392,55.7846096],[37.3171234,55.7849474],[37.3130893,55.7862505],[37.3129177,55.7799761],[37.3123168,55.7799278],[37.3114585,55.7802657],[37.3112869,55.7839822],[37.3106002,55.7844648],[37.3120431,55.786558],[37.3130035,55.7876018],[37.3154926,55.7882774],[37.3136901,55.790256],[37.3114585,55.7913176],[37.3105144,55.7921862],[37.3118019,55.7925239],[37.312746,55.7923792],[37.3153209,55.7927652],[37.3141193,55.7935372],[37.3212432,55.796191],[37.3226165,55.7968665],[37.3230457,55.7971077],[37.3217582,55.7977349],[37.3202991,55.7974937],[37.3156642,55.796384],[37.312746,55.795419],[37.3118877,55.796963],[37.3022478,55.7981811],[37.2928815,55.7960099],[37.2931176,55.7970172],[37.2930586,55.7980002],[37.2904569,55.8020165],[37.2943783,55.8029212],[37.2970014,55.8033552],[37.2984712,55.803512],[37.2998338,55.8036085],[37.3037337,55.8037653],[37.3030471,55.8028005],[37.3027038,55.7984586],[37.3090553,55.7973972],[37.3142051,55.7982174],[37.3145484,55.7991341],[37.3156642,55.7992788],[37.3190116,55.8004367],[37.3207283,55.8005332],[37.3217582,55.8009673],[37.3227613,55.8015462],[37.3240702,55.8013533],[37.3300569,55.8005029],[37.3344986,55.79996],[37.3349814,55.8010758],[37.3361079,55.8020587],[37.3401313,55.803904],[37.3427384,55.8051158],[37.3483014,55.8065872],[37.3579574,55.8036929],[37.3579359,55.8023423],[37.357614,55.8016669],[37.3578071,55.801486],[37.358923,55.8014378],[37.35888,55.8012447],[37.3582363,55.8011483],[37.3577642,55.8009433],[37.3575926,55.8005091],[37.3572493,55.8003282],[37.3567128,55.8004608],[37.3556399,55.8003523],[37.3547387,55.7997251],[37.3541594,55.7988688],[37.3539233,55.798905],[37.3529147,55.7982536],[37.3516702,55.7972766],[37.349031,55.7974093],[37.3486232,55.7964323],[37.3521423,55.7947435],[37.3566913,55.7931512],[37.360897,55.7916554],[37.3656177,55.7909315],[37.3734283,55.8026076],[37.3718833,55.802897],[37.3727416,55.8074796],[37.3729133,55.8086372],[37.3717464,55.809237],[37.3730795,55.8112716],[37.3738654,55.8125921],[37.3750562,55.8123899],[37.376494,55.8120644],[37.3774703,55.8126735],[37.3786639,55.8119649],[37.3792084,55.8116454],[37.3797393,55.8114826],[37.3801793,55.8113201],[37.3802169,55.8112686],[37.3796643,55.8106689],[37.3810751,55.8106416],[37.3807211,55.8096559],[37.3849725,55.8093004],[37.3848009,55.8090351],[37.3807239,55.8093969],[37.3803806,55.8090231],[37.3792648,55.8091195],[37.378149,55.8078655],[37.3778057,55.8069972],[37.3790073,55.8065149],[37.378664,55.8058396],[37.3780632,55.8057913],[37.3772907,55.8043442],[37.3753166,55.8033312],[37.3743724,55.8038136],[37.3736,55.8037171],[37.3734283,55.8025593],[37.3657035,55.7909315],[37.3672644,55.7903645],[37.3682622,55.7900084],[37.3686269,55.7898094],[37.3700218,55.788802],[37.3705581,55.7883076],[37.3705903,55.7881807],[37.3671572,55.7869864],[37.3665348,55.7867088],[37.3647325,55.7860695],[37.3616533,55.7850741],[37.3593895,55.7840905],[37.3606877,55.7832762],[37.360677,55.7831072],[37.359529,55.7824256],[37.3596148,55.7823229],[37.3582414,55.7814843],[37.3581664,55.7815868],[37.3582952,55.7817738],[37.35822,55.7818342],[37.3571794,55.7812007],[37.3522441,55.7780271],[37.3524371,55.7778037],[37.3521797,55.777683],[37.3527002,55.777816],[37.3530864,55.777647],[37.354803,55.7769229],[37.365446,55.7719264],[37.3686432,55.7703058],[37.3754452,55.7671523],[37.3765396,55.766724],[37.3817323,55.7642913],[37.3969779,55.7568302],[37.4221183,55.7448354],[37.427649,55.7482081],[37.4284698,55.7477281],[37.4292959,55.747556],[37.4315651,55.7456869],[37.4311091,55.7452795],[37.4321391,55.7446995],[37.4325735,55.7437967],[37.4330778,55.7427156],[37.4358002,55.7415229],[37.4391343,55.7399314],[37.4396922,55.7396778],[37.4399817,55.7392218],[37.4398746,55.7385031],[37.4379756,55.7371741],[37.4417413,55.7352928],[37.4423315,55.7349573],[37.4434151,55.7342567],[37.4441715,55.7336043],[37.4447856,55.7329095],[37.445196,55.732387],[37.4454536,55.7319371],[37.4457378,55.7313056],[37.4476583,55.7267866],[37.4471058,55.7267536],[37.4413765,55.7267956],[37.4386245,55.726826],[37.4380131,55.7268772],[37.4148845,55.7270011],[37.4120574,55.7271823],[37.4059043,55.728004],[37.3939686,55.7295567],[37.3928312,55.7297439],[37.3914044,55.7298589],[37.3895268,55.729871],[37.3885611,55.7297983],[37.3861901,55.7294782],[37.3848168,55.7292125],[37.382714,55.7287894],[37.3819255,55.728717],[37.3797527,55.7287048],[37.3784547,55.7288559]]
#
#
#
#     RealtyModel.update_dist()
