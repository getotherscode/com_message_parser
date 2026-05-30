import tomllib
import serial
import time
from pathlib import Path

SENSOR_FAULT = 0x7FFF

# load the config file
def load_toml_file(config_file_path = "./config.toml"):
    config_file = Path(config_file_path)
    if not config_file.exists():
        #raise terminate the program
        raise FileNotFoundError(f"config.toml path:{config_file_path} dose not exist !")
    #rb: binary mode, tomllib need binary
    #with : context manager, bind the return  with "as" 
    #open return file obj, encapsulate fd with method
    with open(config_file_path, "rb") as f:
        try:
            config = tomllib.load(f)
            print("load config toml file success !")
        except Exception as e:
            print("load config toml file failed, Error Msg:{e}")
            exit()
        return config

# frame spliter    
def frame_spliter(com_obj: serial.Serial, frame_interval_require = 0.01):
    buffer = b''
    last_recv_time = 0.0

    original_timeout = com_obj.timeout
    com_obj.timeout = 0.001
    #try, except match, finally must be executed
    try:
        while True:
            bytes_to_read = com_obj.in_waiting
            if bytes_to_read > 0:
                data = com_obj.read(bytes_to_read)
                if data:
                    buffer += data
                    last_recv_time = time.time()
            current_time = time.time()

            if len(buffer) > 0 and (current_time - last_recv_time) > frame_interval_require:
                #yield is a generator, remember the state and repeted returns 
                yield buffer
                buffer = b''
                last_recv_time = 0.0
            time.sleep(0.001)
    except GeneratorExit:
        pass
    finally:
        com_obj.timeout = original_timeout        

#parse message: run time
def parse_run_time(recv_dict: dict, msg: bytes):
    # msg level: struct
    msg_st = recv_dict.get("msg_struct",[])

    # create the table to format showed data in terminal
    data_obj = []

    for st in msg_st: 
        offset: int = st.get('byte_offset')
        byte_desc = st.get('description',f"Offset_{offset}")
        data_type:str = st.get('data_type')

        # u8 u16 u32 match
        data = 0
        scale: float = st.get('scale', 1.0)
        byte_seq: str = st.get('byte_seq')
        bit_array = st.get('bits')

        match data_type:
            case "u8":        
                data = msg[offset]
                data_obj.append(
                    {
                        "id":str(offset),
                        "type":"[bold blue]u8[/bold blue]",
                        "desc":f"{byte_desc}", 
                        "value":f"{data}", 
                        "raw":f"{msg[offset]:02x}",
                        "is_section":True
                    }
                )

            case "u16":
                if byte_seq != "big":
                    data = (msg[offset + 1] << 8) + msg[offset]            
                else:
                    data = (msg[offset] << 8) + msg[offset + 1]
                # handle sensor fault
                if data == SENSOR_FAULT:
                    data = 0
                else:    
                    # scale
                    if scale != None and data != 0:
                        data = data * scale
                value_str = f"{data:.1f}" if float(scale) != 1.0 else f"{int(data)}"

                if bit_array:
                    data_obj.append(
                        {
                            "id": str(offset),
                            "type":"[bold blue]u16[/bold blue]",
                            "desc":f"{byte_desc}", 
                            "value":" ",
                            "raw":f"h:{msg[offset]:02x}, l:{msg[offset + 1]:02x}",
                            "is_section":True
                        }
                    )

                    for bit in bit_array:
                        bit_offset = bit.get('bit_offset')
                        bit_desc = bit.get('description')
                        bit_value = ((1 << bit_offset) & data) >> bit_offset
                        data_obj.append(
                        {
                            "id": f"{offset}_{bit_offset}",
                            "type":"[bold blue]bit[/bold blue]",
                            "desc":f"{bit_desc}", 
                            "value":f"{bit_value}",
                            "raw":" ",
                            "is_section":False
                        })
                    data_obj[-1]["is_section"] = True

                else:
                    data_obj.append(
                        {
                            "id": str(offset),
                            "type":"[bold blue]u16[/bold blue]",
                            "desc":f"{byte_desc}", 
                            "value":value_str,
                            "raw":f"h:{msg[offset]:02x}, l:{msg[offset + 1]:02x}",
                            "is_section":True
                        })
                    
            case "u32":
                if byte_seq != "big":
                    data = (msg[offset + 3] << 24) + (msg[offset + 2] << 16) + (msg[offset + 1] << 8) + msg[offset]            
                else:
                    data = (msg[offset] << 24) + (msg[offset + 1] << 16) + (msg[offset + 2] << 8) + msg[offset + 3]
                
                if scale != None and data != 0:
                        data = data * scale
                value_str = f"{data:.1f}" if float(scale) != 1.0 else f"{int(data)}"
                
                data_obj.append(
                        {
                            "id": str(offset),
                            "type":"[bold blue]u32[/bold blue]",
                            "desc":f"{byte_desc}", 
                            "value":f"{data}",
                            "raw":f"h:{msg[offset]:02x}, l:{msg[offset + 1]:02x}, h1:{msg[offset + 2]:02x}, h0:{msg[offset + 3]:02x}",
                            "is_section":True
                        })

    return data_obj
    # show the data

# parse and show message in terminal interface
def parse_msg(reply:bytes, msg_dict: dict, expect_length: int):
    msg_list:list = msg_dict.get("recv",[])

    # match the message type
    match_msg = None
    # list level: recv
    for msg_recv in msg_list:
        msg_type_desc = msg_recv.get("msg_type_desc")
        msg_len = msg_recv.get("msg_length")
        msg_type_code = msg_recv.get("msg_type_code",{})
        value = msg_type_code.get("value");   
        type_code_offset = msg_type_code.get("byte_offset")
        #print(f"current message type code : {value:#x}")
        if type_code_offset is not None and reply[type_code_offset] == value:
            match_msg = msg_recv
            if match_msg == None or msg_len != expect_length:
                #print("no matched message")
                continue
            else:
                #print(f"matched message type : {msg_type_desc}")
                break

    match value:
        case 0x70:
            return parse_run_time(match_msg, reply)
    


