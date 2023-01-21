""" JRA Uma Page Parser """
import os
import json
import shutil
import logging.config
from time import sleep
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common import exceptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.chrome.options import Options

SHORT_SLEEP_TIME = 0.5
LONG_SLEEP_TIME = 2.0

logger = logging.getLogger(__name__)


class RpaJRAVideoPlayTimeout(Exception):
    pass


class RpaJRAVideoPlayContentError(Exception):
    pass


class RpaJRAVideoPlayRetryTimeOut(Exception):
    pass


class RpaJRAVideoPlayObserveTimeout(Exception):
    pass


class RpaJRAVideoPlayFail(Exception):
    pass


class RpaJRAVideo(object):
    def __init__(self):
        self.browser = self.get_driver()

    def get_driver(self):
        pass

    def safty_wait(self):
        sleep(SHORT_SLEEP_TIME)

    def safty_long_wait(self):
        sleep(LONG_SLEEP_TIME)

    def invoke_jra_result(self):
        try:
            element_btn = self.browser.find_element_by_id('btn')
            element_btn.click()
        except exceptions.NoSuchElementException:
            raise RpaJRAVideoPlayContentError
        except Exception as e:
            logger.error(e)

    def invoke_jra_video(self):
        try:
            WebDriverWait(self.browser, 5).until(EC.presence_of_element_located((By.CLASS_NAME, 'movie_line')))
            element_movie_div = self.browser.find_element(By.CLASS_NAME, 'movie_line')
            element_btn = element_movie_div.find_element(By.CLASS_NAME, 'btn_block')
            element_btn.click()
        except exceptions.TimeoutException:
            raise RpaJRAVideoPlayTimeout
        except exceptions.NoSuchElementException:
            raise RpaJRAVideoPlayContentError

    def set_high_quality(self):
        try:
            WebDriverWait(self.browser, 30).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'eqp-icon-resolution')))
            resolution_btn = self.browser.find_element(By.CLASS_NAME, 'eqp-icon-resolution')
        except exceptions.TimeoutException:
            raise RpaJRAVideoPlayTimeout

        if resolution_btn.is_displayed():
            for i in range(10):
                try:
                    resolution_btn.click()
                    WebDriverWait(self.browser, 10).until(
                        EC.visibility_of_element_located((By.CLASS_NAME, 'eqp-resolution-balloon-list')))
                    WebDriverWait(self.browser, 10).until(
                        EC.element_to_be_clickable((By.CLASS_NAME, 'eqp-resolution-balloon-item')))
                    eq_buttons = self.browser.find_elements(By.CLASS_NAME, 'eqp-resolution-balloon-item')
                    if len(eq_buttons) > 1:
                        eq_buttons[1].click()
                        break
                except exceptions.TimeoutException:
                    logger.info('TimeoutException')
                except exceptions.ElementClickInterceptedException:
                    logger.info('ElementClickInterceptedException')
                except exceptions.ElementNotInteractableException:
                    logger.info('ElementNotInteractableException')
                sleep(0.5)

            else:
                raise RpaJRAVideoPlayTimeout
        else:
            raise RpaJRAVideoPlayContentError

    def wait_until_video_plays(self):

        try:
            WebDriverWait(self.browser, 10).until(EC.element_to_be_clickable(
                (By.CLASS_NAME, 'eqp-big-play-button')))
            eq_buttons = self.browser.find_elements(By.CLASS_NAME, 'eqp-big-play-button')
            if eq_buttons:
                eq_buttons[0].click()
            else:
                logger.info('ElementNotInteractableException')
                raise RpaJRAVideoPlayContentError

        except exceptions.TimeoutException:
            raise RpaJRAVideoPlayTimeout

    def play_jra_video(self):
        self.invoke_jra_video()

        self.safty_wait()

        handles = self.browser.window_handles

        self.browser.switch_to.window(handles[1])

        for i in range(3):
            try:
                WebDriverWait(self.browser, 5).until(EC.presence_of_element_located((By.TAG_NAME, 'iframe')))
                logger.debug('iframe comes up')
                iframe = self.browser.find_elements(By.TAG_NAME, 'iframe')
                if len(iframe) >= 1:
                    logger.debug('switch')
                    self.browser.switch_to.frame(iframe[0])
                    break
                else:
                    logger.info("No iframe")
                    sleep(1)
            except exceptions.TimeoutException:
                logger.info('exceptions.TimeoutException happens, retry')
        else:
            self.browser.close()
            self.browser.switch_to.window(handles[0])
            raise RpaJRAVideoPlayTimeout

        self.safty_long_wait()
        self.set_high_quality()

        try:
            self.wait_until_video_plays()
        except RpaJRAVideoPlayTimeout:
            self.browser.close()
            self.browser.switch_to.window(handles[0])
            raise RpaJRAVideoPlayTimeout

    def retrieve_url(self, race_id):
        for i in range(5):
            self.browser.get('https://www.jra.go.jp/JRADB/accessS.html?CNAME={}'.format(race_id))
            self.safty_wait()
            break
        else:
            logger.error('Failed to play video')
            self.browser.close()
            self.browser.switch_to.window(self.browser.window_handles[0])
            self.browser.quit()
            raise RpaJRAVideoPlayFail

        self.safty_wait()

        for i in range(5):
            try:
                self.play_jra_video()
                break
            except RpaJRAVideoPlayTimeout:
                logger.info('Retry Play Video [{}]'.format(i))
            except RpaJRAVideoPlayContentError:
                logger.info('Retry Play Video [{}]'.format(i))
        else:
            logger.error('Failed to play video')
            self.browser.close()
            self.browser.switch_to.window(self.browser.window_handles[0])
            self.browser.quit()
            raise RpaJRAVideoPlayFail

        url = None
        for entry_json in self.browser.get_log('performance'):
            entry = json.loads(entry_json['message'])
            if entry is not None:
                if entry['message']['method'] != 'Network.requestWillBeSent':
                    continue
                if entry['message']['params']['request']['url'].endswith('.m3u8'):
                    url = entry['message']['params']['request']['url']

        return url


class RpaJRAVideoChrome(RpaJRAVideo):
    def __init__(self):
        super().__init__()

    def get_driver(self):
        caps = DesiredCapabilities.CHROME
        caps["goog:loggingPrefs"] = {"performance": "ALL"}
        options = Options()
        options.add_argument('--headless')

        return webdriver.Chrome(desired_capabilities=caps, options=options)


if __name__ == '__main__':
    # "choromedriver" must be placed in somewhere visible from the running environment.
    video_rpa = RpaJRAVideoChrome()

    races = [
        'pw01sde1006202301061120230115/48',
        'pw01sde1009202203021120220619/10',
        'pw01sde1006202205091120221228/82'
    ]

    for race in races:
        for i in range(2):
            try:
                print('Race ID : {}'.format(race))
                url = video_rpa.retrieve_url(race)
                print('Video URL  : {}'.format(url))
                break
            except rpa.RpaJRAVideoPlayFail:
                logger.warning('RpaJRAVideoPlayFail')