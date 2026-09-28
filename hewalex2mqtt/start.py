import json, os, re

opts = json.load(open('/data/options.json'))
src = open('/app/hewalex2mqtt.py').read()

def patch(old, new, text, name, regex=False):
    result = re.sub(old, new, text, flags=re.M) if regex else text.replace(old, new)
    if result == text:
        print('WAARSCHUWING: aanpassing niet toegepast: ' + name, flush=True)
    return result

# PCWU device-ID (warmtepomp)
dev = str(opts['pcwu_dev_id'])
src = patch(r'^devHardId = \d+', 'devHardId = ' + dev, src, 'devHardId', True)
src = patch(r'^devSoftId = \d+', 'devSoftId = ' + dev, src, 'devSoftId', True)

# ZPS krijgt een eigen device-ID (zonneboilerregelaar)
zps_dev = str(opts.get('zps_dev_id', 2))
src = patch(r'^devSoftId = (\d+)$', r'devSoftId = \1\nzpsDevId = ' + zps_dev, src, 'zpsDevId', True)
src = patch('ZPS(conHardId, conSoftId, devHardId, devSoftId,',
            'ZPS(conHardId, conSoftId, zpsDevId, zpsDevId,', src, 'ZPS eigen id')

# Storing bij de ene module mag de andere niet blokkeren
src = patch(r'^(\s+)readZPS\(\)$',
            r'\1try:\n\1    readZPS()\n\1except Exception as e:\n\1    logger.info("ZPS uitlezen mislukt: " + str(e))',
            src, 'ZPS try', True)
src = patch(r'^(\s+)readPCWU\(\)$',
            r'\1try:\n\1    readPCWU()\n\1except Exception as e:\n\1    logger.info("PCWU uitlezen mislukt: " + str(e))',
            src, 'PCWU try', True)

# ZPS: instellingen van de regelaar uitlezen (origineel las hier per ongeluk de status)
src = patch(r'(def readZPSConfig\(\):[\s\S]*?)dev\.readStatusRegisters', r'\1dev.readConfigRegisters',
            src, 'ZPS config lezen', True)
src = patch(r'^(\s+)#readZPSConfig\(\).*$',
            r'\1try:\n\1    readZPSConfig()\n\1except Exception as e:\n\1    logger.info("ZPS config uitlezen mislukt: " + str(e))',
            src, 'ZPS config aanroepen', True)

# ZPS: schrijfopdrachten via SolarBoiler/Command/<naam>, alleen veilige instellingen
src = patch(r"^(\s+)client\.subscribe\(_Device_Pcwu_MqttTopic \+ '/Command/#', qos=1\)$",
            r"\g<0>\n\1if _Device_Zps_Enabled:\n\1    client.subscribe(_Device_Zps_MqttTopic + '/Command/#', qos=1)\n\1    logger.info('subscribed to : ' + _Device_Zps_MqttTopic + '/Command/#')",
            src, 'ZPS subscribe', True)
src = patch(r"^(\s+)else:\n(\s+)logger\.info\('cannot process message on topic ' \+ topic\)",
            r"\1elif len(arr) == 3 and arr[0] == _Device_Zps_MqttTopic and arr[1] == 'Command':\n\2logger.info('Recieved ZPS command ' + topic)\n\2writeZpsConfig(arr[2], payload)\n\1else:\n\2logger.info('cannot process message on topic ' + topic)",
            src, 'ZPS command', True)
src = patch('def printZPSMqttTopics():',
            """ZPS_WRITE_ALLOWED = ['LegionellaProtEnabled', 'HolidayEnabled', 'CirculationPumpEnabled']

def writeZpsConfig(registerName, payload):
    if registerName not in ZPS_WRITE_ALLOWED:
        logger.info('ZPS schrijven geweigerd (niet toegestaan): ' + registerName)
        return
    ser = serial.serial_for_url("socket://%s:%s" % (_Device_Zps_Address, _Device_Zps_Port))
    dev = ZPS(conHardId, conSoftId, zpsDevId, zpsDevId, on_message_serial)
    dev.write(ser, registerName, payload)
    ser.close()

def printZPSMqttTopics():""", src, 'ZPS write functie')

src = patch('client.publish(key, val)', 'client.publish(key, val, retain=True)', src, 'retain')
src = patch('if isinstance(item[1], dict): # skipping dictionaries (time program)',
            'if False: # time program published as list', src, 'tijdprogramma')
src = patch('val = str(item[1])',
            'val = json.dumps(sorted(h for h, on in item[1].items() if on)) if isinstance(item[1], dict) else str(item[1])',
            src, 'tijdprogramma json')
src = 'import json\n' + src
open('/app/run_hewalex.py', 'w').write(src)

zps_enabled = 'True' if opts.get('zps_enabled', False) else 'False'
ini = f"""[MQTT]
MQTT_ip = {opts['mqtt_host']}
MQTT_port = {opts['mqtt_port']}
MQTT_authentication = True
MQTT_user = {opts['mqtt_user']}
MQTT_pass = {opts['mqtt_pass']}
MQTT_GatewayDevice_Topic = HewaGate

[ZPS]
Device_Zps_Enabled = {zps_enabled}
Device_Zps_Address = {opts.get('zps_host', '127.0.0.1')}
Device_Zps_Port = {opts.get('zps_port', 8899)}
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
