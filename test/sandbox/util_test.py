
from k2kparser import util as ut


print(ut.Util.parse_date_mmdd_to_int('1月22日', 2022))
print(ut.Util.parse_date_mmdd_to_int('1月22日'))

print(ut.Util.parse_date_mmdd_to_int('11月29日'))
print(ut.Util.parse_date_mmdd_to_int('11月29日', 2021))