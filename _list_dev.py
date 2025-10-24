from device_manager import DeviceManager
with DeviceManager() as dm:
    devs = dm.list_all_devices(refresh_cache=True)
    for d in devs:
        print(d.index, d.name, d.max_input_channels, d.max_output_channels, d.host_api, d.is_loopback)
