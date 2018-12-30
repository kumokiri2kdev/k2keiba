import logging.config
from logging import getLogger, INFO

import parser as pr


if __name__ == '__main__':
    logger = getLogger(__name__)
    logger.setLevel(INFO)

    p = pr.ParserDenTop('/JRADB/accessD.html', 'pw01dli00/F3')
    kaisai_list = p.parse()

    logger.info(kaisai_list)