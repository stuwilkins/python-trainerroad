import requests
import lxml.html
from lxml import etree
from io import StringIO, BytesIO

import logging
logger = logging.getLogger(__name__)


class TrainerRoad:
    _ftp = 'Ftp'
    _weight = 'Weight'
    _input_data_names = (_ftp, _weight, 'Marketing')
    _select_data_names = ('TimeZoneId', 'IsMale', 'IsPrivate',
                          'Units', 'IsVirtualPowerEnabled', 'TimeZoneId')
    _login_url = "https://www.trainerroad.com/login"
    _logout_url = 'https://www.trainerroad.com/logout'
    _rider_url = 'https://www.trainerroad.com/profile/rider-information'
    _rvt = '__RequestVerificationToken'

    def __init__(self, username, password):
        self._username = username
        self._password = password
        self._session = None

    def connect(self):
        self._session = requests.Session()
        self._session.auth = (self._username, self._password)

        data = {'Username': self._username,
                'Password': self._password}

        r = self._session.post(self._login_url, data=data,
                               allow_redirects=False)

        if (r.status_code != 200) and (r.status_code != 302):
            # There was an error
            raise RuntimeError("Error loging in to TrainerRoad (Code {})"
                               .format(r.status_code))

        logger.info('Logged into TrainerRoad as "{}"'.format(self._username))

    def disconnect(self):
        r = self._session.get(self._logout_url, allow_redirects=False)
        if (r.status_code != 200) and (r.status_code != 302):
            raise RuntimeError("Error loging out of TrainerRoad (Code {})"
                               .format(r.status_code))

        self._session = None
        logger.info('Logged out of TrainerRoad as "{}"'.format(self._username))

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.disconnect()

    def _parse_value(self, tree, name):
        rtn = tree.xpath('//form//input[@name="{}"]/@value'.format(name))
        if not rtn:
            raise RuntimeError('Input {} not found in form'.format(name))

        return rtn[0]

    def _parse_name(self, tree, name):
        rtn = tree.xpath('//form//select[@name="{}"]//option'
                         '[@selected="selected"]/@value'.format(name))
        if not rtn:
            raise RuntimeError('Input {} not found in form'.format(name))

        return rtn[0]

    def _get(self, url):
        if self._session is None:
            raise RuntimeError('Not Connected')

        r = self._session.get(url)

        if r.status_code != 200:
            raise RuntimeError("Error getting info from TrainerRoad (Code {})"
                               .format(r.status_code))

        return r

    def _post(self, url, data):
        if self._session is None:
            raise RuntimeError('Not Connected')

        r = self._session.post(url, data)

        if r.status_code != 200:
            raise RuntimeError("Error posting info to TrainerRoad (Code {})"
                               .format(r.status_code))

        return r

    def _read_profile(self):
        r = self._get(self._rider_url)
        parser = etree.HTMLParser()
        tree = etree.parse(StringIO(r.text), parser)

        token = self._parse_value(tree, self._rvt)

        input_data = {}
        for key in self._input_data_names:
            input_data[key] = self._parse_value(tree, key)

        select_data = {}
        for key in self._select_data_names:
            select_data[key] = self._parse_name(tree, key)

        return (dict(**input_data, **select_data), token)

    def _write_profile(self, new_values):
        # Read values
        data, token = self._read_profile()

        logger.info("Read profile values {}".format(data))
        logger.debug("Token = {}".format(token))

        # Update values with new_values
        for key, value in new_values.items():
            if key not in data:
                raise ValueError("Key \"{}\" is not in profile form"
                                 .format(key))
            data[key] = str(value)

        logger.info("New profile values {}".format(data))

        # Now post the form
        token = {self._rvt: token}
        self._post(self._rider_url, data=dict(**data, **token))

        # Now re-read to check
        _data, token = self._read_profile()

        logger.info("Read profile values (verification) {}".format(data))

        if data == _data:
            return
        else:
            raise RuntimeError('Failed to verify profile')

        return

    @property
    def ftp(self):
        values, token = self._read_profile()
        return values[self._ftp]

    @ftp.setter
    def ftp(self, value):
        self._write_profile({self._ftp: value})

    @property
    def weight(self):
        values, token = self._read_profile()
        return values[self._weight]

    @weight.setter
    def weight(self, value):
        self._write_profile({self._weight: value})
