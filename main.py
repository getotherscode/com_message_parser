from config_parser import load_toml_file, parse_and_show_msg, frame_spliter
from com_app import load_the_com
import crcmod.predefined
from typing import Callable
import time

if __name__ == "__main__":

# mode
    MODE = "listen"
    FRAME_TIMEOUT = 0.015

# load the configure file    
    config_obj = load_toml_file()
    serial_config = config_obj.get("serial")
    message_config = config_obj.get("message")

# configure and open the com
    com_obj = load_the_com(serial_config.get("description"),serial_config.get("baudrate"))

# loop query the run time data and parse the data by toml

    # fixed head
    query_run_time_msg:bytes = bytes.fromhex("02 70 00")
    
    # get crc check
    crc_fun:Callable = crcmod.predefined.mkPredefinedCrcFun('modbus')
    crc_value:int = crc_fun(query_run_time_msg)

    # splice the message
    query_run_time_msg_with_crc:bytes = query_run_time_msg + crc_value.to_bytes(2,'little')

    ## join(Generator Expression)
    ## Generator Expression: (element operation for every element in iterable obj), returns generator obj
    ## iterable contains iterator contains generator
    ## generator obj: a lazy plan — knows how to produce results but does nothing until called
    ## f'{b:02x}': format b as lowercase hex, at least 2 digits (e.g. 1->'01', 255->'ff')
    print("send message : " + ' '.join(f'{b:02X}' for b in query_run_time_msg_with_crc))

    # get directory
    msg_dict = config_obj.get("message")

    try:
        framer = frame_spliter(com_obj, FRAME_TIMEOUT)
        while True:
            if MODE == "poll":
                # send query message
                com_obj.write(query_run_time_msg_with_crc)
                time.sleep(0.05)

            elif MODE == "listen":
                pass

            # receive reply
            reply_msg:bytes = next(framer)

            if(len(reply_msg) == 0):
                print("no reply")
                continue

            #check crc
            print("reply message : " + ' '.join(f'{b:02x}' for b in reply_msg))

            # parse the reply message and show in terminal
            parse_and_show_msg(reply_msg, msg_dict, len(reply_msg))
    except KeyboardInterrupt:
            print("Ctrl + C to Exit !")
    finally:
            #close the com
            com_obj.close()



        