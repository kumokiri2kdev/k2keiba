import k2kparser.result_params as prp
import k2kparser.result as pr
from k2kparser import util as ut

if __name__ == '__main__':
    target_mont = 202202
    param = prp.ParserRaceParams.get_cname(target_mont)
    print("Month : {}, Param : {}".format(target_mont, param))

    prkl = pr.ParserResultKaisaiList('/JRADB/accessS.html', param)
    days = prkl.parse()

    print(days)
    for day in days:
        print(day.get('date'))
        print(ut.Util.parse_date_mmdd(day.get('date')))