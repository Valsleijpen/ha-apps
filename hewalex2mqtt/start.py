import json, os, re

opts = json.load(open('/data/options.json'))
src = open('/app/hewalex2mqtt.py').read()

def patch(old, new, text, name, regex=False):
    result = re.sub(old, new, text, flags=re.M) if regex else text.replace(old, new)
    if result == text:
        print('WAARSCHUWING: aanpassing niet toegepast: ' + name, flush=True)
    return result

dev = str(opts['pcwu_dev_id'])
src = patch(r'^devHardId = \d+', 'devHardId = ' + dev, src, 'devHardId', True)
src = patch(r'^devSoftId = \d+', 'devSoftId = ' + dev, src, 'devSoftId', True)
src = patch('client.publish(key, val)', 'client.publish(key, val, retain=True)', src, 'retain')
src = patch('if isinstance(item[1], dict): # skipping dictionaries (time program)',
            'if False: # time program published as list', src, 'tijdprogramma')
src = patch('val = str(item[1])',
            'val = json.dumps(sorted(h for h, on in item[1].items() if on)) if isinstance(item[1], dict) else str(item[1])',
            src, 'tijdprogramma json')
src = 'import json\n' + src
open('/app/run_hewalex.py', 'w').write(src)

ini = f"""[MQTT]
MQTT_ip = {opts['mqtt_host']}
MQTT_port = {opts['mqtt_port']}
MQTT_authentication = True
MQTT_user = {opts['mqtt_user']}
MQTT_pass = {opts['mqtt_pass']}
MQTT_GatewayDevice_Topic = HewaGate

[ZPS]
Device_Zps_Enabled = False
Device_Zps_Address = 127.0.0.1
Device_Zps_Port = 8899
Device_Zps_MqttTopic = SolarBoiler

[Pcwu]
Device_Pcwu_Enabled = True
Device_Pcwu_Address = {opts['pcwu_host']}
Device_Pcwu_Port = {opts['pcwu_port']}
Device_Pcwu_MqttTopic = Heatpump
"""
open('/app/hewalex2mqttconfig.ini', 'w').write(ini)

os.chdir('/app')
os.execvp('python', ['python', '-u', 'run_hewalex.py'])
