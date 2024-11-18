# import paho.mqtt.client as mqtt
import logging
import json
import os
import time

from socket import socket, AF_INET, SOCK_DGRAM


config = None
with open("config.json", 'r') as f:
    config = json.load(f)

columns = None

assert config['host'] is not None
assert config['path_to_save'] is not None


def flush_to_file(data):
    global config, columns

    data = data.decode()
    if type(data) is not str:
        logging.error(
            "Provided data is not string type. type = {}".format(type(data)))
        return

    try:
        data = dict(json.loads(data))
    except Exception as e:
        logging.error(
            "Error while loading string to json: {}\ndata={}".format(e, data))
        return

    write_cols = False
    # First run
    if columns is None and os.path.isfile(config['path_to_save']):
        f = open(config['path_to_save'], 'r')
        line = f.readline()
        # CSV file with columns descriptor
        columns = line.split(',')
        logging.warn(
            "File already exists. Using columns found in the file: {}",
            columns)
        write_cols = True
    elif columns is None:
        columns = [c for c in data]
        write_cols = True

    if write_cols:
        with open(config['path_to_save'], 'a') as f:
            f.write(','.join(['timestamp'] + columns) + '\n')

    # Make sure each key is in columns
    for key in data:
        if key not in columns:
            logging.warn("{} column doesn't exist".format(key))

    temp = []
    for c in columns:
        val = data.get(c, '')
        if val == '':
            logging.warn("{} not found in sent data".format(c))
        temp.append(val)
    temp = [time.time()] + temp
    temp = [str(x) for x in temp]

    with open(config['path_to_save'], 'a') as f:
        f.write(','.join(temp) + '\n')

    logging.info("Succesfully wrote to file!")


try:
    sock = socket(AF_INET, SOCK_DGRAM)
    sock.bind(('0.0.0.0', config['port']))
    sock.sendto(b"Hello!", (config['host'], config['port']))

    while True:
        data, addr = sock.recvfrom(1024 * 4)
        flush_to_file(data)


except KeyboardInterrupt:
    sock.close()
    print("Closing down...")

except Exception as e:
    logging.error("Error while running server. Error = {}".format(e))
