import logging
import requests

import voluptuous as vol

# Import the device class from the component that you want to support
from homeassistant.components.light import SUPPORT_BRIGHTNESS, ATTR_BRIGHTNESS, Light, PLATFORM_SCHEMA
from homeassistant.const import CONF_HOST, CONF_PASSWORD
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

# Validation of the user's configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_PASSWORD): cv.string,
})

def setup_platform(hass, config, add_devices, discovery_info=None):

    # Assign configuration variables. The configuration check takes care they are
    # present. 
    host = config.get(CONF_HOST)
    base_url="http://"+host+"/api.php"
    password = config.get(CONF_PASSWORD)

    # Verify that passed in configuration works
    response = requests.get(base_url)
    if not response.ok:
        _LOGGER.error("Could not connect to Domus.Link")
        return False

    # Add devices
    response=requests.get(base_url+"/aliases/all",auth=("", password));
    if not response.ok:
        _LOGGER.error("Could not connect to Domus.Link")
        return False

    light_array = []

    for alias in response.json()['aliases']:
        if (alias['aliasMapElement']['elementType'].upper() == 'LIGHT'
             and
             alias['enabled']):
           if ( alias['moduleType'].startswith("AM") ):
               light_array.append(DomusLight(alias,base_url,password,0))
           else:
               light_array.append(DomusLight(alias,base_url,password,SUPPORT_BRIGHTNESS))
    add_devices(light_array)

class DomusLight(Light):

    def __init__(self, alias, base_url, password, capabilities):
        self._name = alias['label'].replace("_"," ")
        self._alias=alias['label']
        self._state = False
        self._brightness = 100
        self._base_url = base_url
        self._password = password
        self._capabilities = capabilities

    def check_for_error(self, response):
        if not response.ok:
            _LOGGER.error("Could not connect to Domus.Link")
            return False
        else:
            return True

    @property
    def name(self):
        # Return the display name of this light.
        return self._name

    @property
    def brightness(self):
        # Return the brightness of the light.
        return int(float(self._brightness)*2.55)

    @property
    def supported_features(self):
        # Flag supported features.
        return self._capabilities

    @property
    def is_on(self):
        # Return true if light is on.
        return self._state

    def turn_on(self, **kwargs):
        # Instruct the light to turn on.
        if(not self._state):
            request_string=self._base_url+"/on/"+self._alias
            response=requests.post(request_string,auth=("", self._password));
            if(self.check_for_error(response)):
                self._state=True
                self._brightness=100
        if(self._capabilities == SUPPORT_BRIGHTNESS):
            new_brightness=int(float(kwargs.get(ATTR_BRIGHTNESS, 255))/2.55)
            if(new_brightness < 1):
                new_brightness=1
            request_string=self._base_url+"/dimbright/"+self._alias+("/0","/1")[self._state]+"/"+str(self._brightness)+"/"+str(new_brightness)
            response=requests.post(request_string,auth=("", self._password));
            if(self.check_for_error(response)):
                self.update()

    def turn_off(self, **kwargs):
        # Instruct the light to turn off.
        response=requests.post(self._base_url+"/off/"+self._alias,auth=("", self._password));
        if(self.check_for_error(response)):
            self.update()

    def update(self):
        # Fetch new state data for this light.
        response=requests.get(self._base_url+"/aliasstate/"+self._alias,auth=("", self._password));
        if(self.check_for_error(response)):
            status=response.json()
            self._state = status['state']==1
            self._brightness = int(status['level'])

