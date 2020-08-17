import cv2
import pytesseract
from model.config import Config
import numpy as np
from hashlib import md5
import time
import os
import re

try:
    import Image
except ImportError:
    from PIL import Image
from subprocess import check_output


# The CaptchaResolver class simulates a captcha converter
class CaptchaResolver:
    def __init__(self, path=None):
        self.path = path
        self.config = Config()

    def set_path(self, path):
        self.path = path

    def get_path(self):
        return self.path

    def resolve(self, is_check_output=None):
        # Denoising
        if is_check_output is None:
            image = cv2.imread(self.path, 0)
        # dst = cv2.fastNlMeansDenoisingColored(image, None, 10, 10, 7, 21)
        # b, g, r = cv2.split(dst)  # get b,g,r
        # rgb_dst = cv2.merge([r, g, b])  # switch it to rgb
        # gray = cv2.cvtColor(rgb_dst, cv2.COLOR_BGR2GRAY)
        # filename = "{}.png".format(os.getpid())
        # gray = cv2.medianBlur(gray, 3)
        # gray = cv2.threshold(gray, 231, 255,
        # #                      cv2.THRESH_BINARY)[1]
        # kernel = np.ones((5, 5), np.uint8)
        # lower_red = np.array([30, 150, 50])
        # upper_red = np.array([255, 255, 180])
        # mask = cv2.inRange(rgb_dst, lower_red, upper_red)
        # erosion = cv2.erode(mask, kernel, iterations=1)
        # dilation = cv2.dilate(mask, kernel, iterations=1)
        # cv2.imwrite(self.path, gray)
        # cmd = 'convert ' + self.path + ' -scale 400% ' + self.path
        # os.system(cmd)
        # image = Image.open(self.path)
        # pixdata = image.load()
        # for y in range(image.size[1]):
        #     for x in range(image.size[0]):
        #         if pixdata[x, y][0] < 90:
        #             pixdata[x, y] = (0, 0, 0, 255)
        #
        # for y in range(image.size[1]):
        #     for x in range(image.size[0]):
        #         if pixdata[x, y][1] < 136:
        #             pixdata[x, y] = (0, 0, 0, 255)
        #
        # for y in range(image.size[1]):
        #     for x in range(image.size[0]):
        #         if pixdata[x, y][2] > 0:
        #             pixdata[x, y] = (255, 255, 255, 255)
        # converted_captcha = self.config.get_base_dir('tmp') + self.get_tmp_file_name('captcha.gif')
        # image.save(converted_captcha, "GIF")
        # image_orig = Image.open(converted_captcha)
        # width, height = image_orig.size
        # big = image_orig.resize((int(width * 5), int(height * 5)), Image.BICUBIC)
        # big_captcha = self.config.get_base_dir('tmp') + self.get_tmp_file_name('big-captcha.gif')
        # big.save(big_captcha)
        else:
            check_output(['convert', self.path, '-resample', '600', self.path])
            image = Image.open(self.path)
        captcha_str = pytesseract.image_to_string(image, lang="eng")
        os.remove(self.path)
        captcha_str = re.sub('[^A-Za-z0-9]+', '', captcha_str)
        # os.remove(converted_file)
        # print('Captcha: ' + captcha_str)
        return captcha_str

    def save_from_source(self, source, suffix='jpeg'):
        tmp_file = self.config.get_base_dir('tmp') + self.get_tmp_file_name('captcha.' + suffix)
        with open(tmp_file, 'wb') as handler:
            handler.write(source)
        self.set_path(tmp_file)
        if suffix is not 'jpeg':
            image = Image.open(tmp_file)
            rgb_im = image.convert('RGB')
            new_file = self.config.get_base_dir('tmp') + self.get_tmp_file_name('captcha.jpeg')
            rgb_im.save(new_file, "jpeg")
            self.set_path(new_file)
            os.remove(tmp_file)

    def get_tmp_file_name(self, filename):
        return "%s_%s" % (md5(str(time.time()).encode('utf-8')).hexdigest(), filename)
