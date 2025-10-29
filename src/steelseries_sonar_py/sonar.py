import requests
import json
import os

try:
    from . import exceptions as ex
except ImportError:
    import exceptions as ex


class Sonar:
    # chatCapture = mic
    channel_names = ["master", "game", "chatRender", "media", "aux", "chatCapture"]
    streamer_slider_names = ["streaming", "monitoring"]
    volume_path = "/volumeSettings/classic"
    app_data_path = os.path.join(
        os.environ["ProgramData"],
        "SteelSeries",
        "SteelSeries Engine 3",
        "coreProps.json",
    )

    def __init__(self, app_data_path=None, streamer_mode=None):
        requests.packages.urllib3.disable_warnings()

        if app_data_path is not None:
            self.app_data_path = app_data_path

        self.load_base_url()
        self.load_server_address()

        if streamer_mode is None:
            self.streamer_mode = self.is_streamer_mode()

        if self.streamer_mode:
            self.volume_path = "/volumeSettings/streamer"

    def is_streamer_mode(self):
        streamer_mode_data = requests.get(self.web_server_address + "/mode/", verify=False)
        if streamer_mode_data.status_code != 200:
            raise ex.ServerNotAccessibleError(streamer_mode_data.status_code)
        
        return json.loads(streamer_mode_data.text) == "stream"

    def set_streamer_mode(self, streamer_mode):
        if streamer_mode:
            mode = "stream"
        else:
            mode = "classic"

        url = f"{self.web_server_address}/mode/{mode}"
        streamer_mode_data = requests.put(url)
        if streamer_mode_data.status_code != 200:
            raise ex.ServerNotAccessibleError(streamer_mode_data.status_code)

        self.streamer_mode = json.loads(streamer_mode_data.text) == "stream"
        return self.streamer_mode

    def load_base_url(self):
        if not os.path.exists(self.app_data_path):
            raise ex.EnginePathNotFoundError()

        with open(self.app_data_path, "r") as rf:
            common_app_data = json.load(rf)
            self.base_url = f'https://{common_app_data["ggEncryptedAddress"]}'

    def load_server_address(self):
        app_data = requests.get(self.base_url + "/subApps", verify=False)
        if app_data.status_code != 200:
            raise ex.ServerNotAccessibleError(app_data.status_code)

        app_data_json = json.loads(app_data.text)

        if not app_data_json["subApps"]["sonar"]["isEnabled"]:
            raise ex.SonarNotEnabledError()

        if not app_data_json["subApps"]["sonar"]["isReady"]:
            raise ex.ServerNotReadyError()

        if not app_data_json["subApps"]["sonar"]["isRunning"]:
            raise ex.ServerNotRunningError()

        self.web_server_address = app_data_json["subApps"]["sonar"]["metadata"][
            "webServerAddress"
        ]
        if self.web_server_address in ["", None, "null"]:
            raise ex.WebServerAddressNotFoundError()

    def get_volume_data(self):
        volume_info_url = self.web_server_address + self.volume_path

        volume_data = requests.get(volume_info_url)
        if volume_data.status_code != 200:
            raise ex.ServerNotAccessibleError(volume_data.status_code)
        volume_data_json = json.loads(volume_data.text)

        return volume_data_json

    def set_volume(self, channel, volume, streamer_slider="streaming"):
        if channel not in self.channel_names:
            raise ex.ChannelNotFoundError(channel)

        if self.streamer_mode and streamer_slider not in self.streamer_slider_names:
            raise ex.SliderNotFoundError(streamer_slider)

        if volume < 0 or volume > 1:
            raise ex.InvalidVolumeError(volume)

        full_volume_path = self.volume_path
        if self.streamer_mode:
            full_volume_path += f"/{streamer_slider}"

        url = f"{self.web_server_address}{full_volume_path}/{channel}/Volume/{json.dumps(volume)}"
        volume_data = requests.put(url)
        if volume_data.status_code != 200:
            raise ex.ServerNotAccessibleError(volume_data.status_code)

        return json.loads(volume_data.text)

    def mute_channel(self, channel, muted, streamer_slider="streaming"):
        if channel not in self.channel_names:
            raise ex.ChannelNotFoundError(channel)

        if self.streamer_mode and streamer_slider not in self.streamer_slider_names:
            raise ex.SliderNotFoundError(streamer_slider)

        muted = muted in [True, "true", "True", 1, "1"]

        full_volume_path = self.volume_path
        if self.streamer_mode:
            full_volume_path += f"/{streamer_slider}"

        mute_keyword = "isMuted" if self.streamer_mode else "Mute"

        url = f"{self.web_server_address}{full_volume_path}/{channel}/{mute_keyword}/{json.dumps(muted)}"
        mute_data = requests.put(url)
        if mute_data.status_code != 200:
            raise ex.ServerNotAccessibleError(mute_data.status_code)

        return json.loads(mute_data.text)

    def get_chat_mix_data(self):
        chat_mix_url = self.web_server_address + "/chatMix"

        chat_mix_data = requests.get(chat_mix_url)
        if chat_mix_data.status_code != 200:
            raise ex.ServerNotAccessibleError(chat_mix_data.status_code)

        return json.loads(chat_mix_data.text)

    def set_chat_mix(self, mix_volume):
        if mix_volume < -1 or mix_volume > 1:
            raise ex.InvalidMixVolumeError(mix_volume)
        
        url = f"{self.web_server_address}/chatMix?balance={json.dumps(mix_volume)}"
        chat_mix_data = requests.put(url)
        if chat_mix_data.status_code != 200:
            raise ex.ServerNotAccessibleError(chat_mix_data.status_code)

        return json.loads(chat_mix_data.text)

    ## Note: Copyed functionality from get_chat_mix_data, needs to be implemented properly and documented
    def get_audio_devices(self):
        # Wireshark capture as reference:
        #20220	680.831222	127.0.0.1	127.0.0.1	HTTP	578	GET /audioDevices HTTP/1.1 

        url = self.web_server_address + "/audioDevices"
        
        audio_devices_data = requests.get(url)
        if audio_devices_data.status_code != 200:
            raise ex.ServerNotAccessibleError(audio_devices_data.status_code)

        return json.loads(audio_devices_data.text)

    # Use get_audio_devices to get the device IDs
    def set_audio_device(self, device_id, streamer_slider="streaming"):
        # Wireshark capture as reference:
        #69336	2825.369295	127.0.0.1	127.0.0.1	HTTP	687	PUT /streamRedirections/monitoring/deviceId/%7B0.0.0.00000000%7D.%7Be5fc5284-587d-453c-94ad-688914a8f610%7D HTTP/1.1 

        url = f"{self.web_server_address}/streamRedirections/{streamer_slider}/deviceId/{device_id}"
        personal_device_data = requests.put(url)

        if personal_device_data.status_code != 200:
            raise ex.ServerNotAccessibleError(personal_device_data.status_code)
        
        return json.loads(personal_device_data.text)
    
    def set_app_channel(self):
        # Wireshark capture as reference:
        # 159088	5850.097544	127.0.0.1	127.0.0.1	HTTP	680	PUT /AudioDeviceRouting/render/%7B0.0.0.00000000%7D.%7B34869e41-cf12-4bec-ba8c-20d7a3f8b2e3%7D/17936 HTTP/1.1 

        pass

    def get_audio_device_routing(self):
        
        url = f"{self.web_server_address}/AudioDeviceRouting"

        personal_device_data = requests.get(url)

        if personal_device_data.status_code != 200:
            raise ex.ServerNotAccessibleError(personal_device_data.status_code)
        
        return json.loads(personal_device_data.text)
        pass

if __name__ == "__main__":
    sonar = Sonar("C:\\ProgramData\\SteelSeries\\SteelSeries Engine 3\\coreProps.json")
    AudioDevices = sonar.get_audio_devices()
    print(sonar.get_socket())

    #for device in AudioDevices:
    #    #print(f'{device['friendlyName']} {device["id"]}')
    #
    #    if device['friendlyName'] == "Speakers (Stealth 700P Gen 3)":
    #        print(device["id"])
    #        #sonar.set_audio_device(device["id"], "streaming")