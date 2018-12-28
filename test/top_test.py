""" Test Code for ParserTop class. """

import parser as pr

if __name__ == '__main__':
    p = pr.ParserTop()
    params = p.parse()

    list_to_be_checked = (
        'kaisai',
        'shutuba',
        'odds',
        'haraimodoshi',
        'tokubetu'
    )

    for check_item in list_to_be_checked:
        if check_item in params:
            print(check_item,'exists :', params[check_item])
        else:
            print("Error :", check_item , "doesn't exist.")

