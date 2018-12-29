
import parser as pr

if __name__ == '__main__':
    p = pr.ParserDenTop('/JRADB/accessD.html', 'pw01dli00/F3')
    kaisai_list = p.parse()

    print(kaisai_list)