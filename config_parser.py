import tomllib
from pathlib import Path
from rich.table import Table
from rich.console import Console

SENSOR_FAULT = 0x7FFF

#display in console
def init_display_format():

    table = Table(title="Run-Time Data")
    table.add_column("Field", style="cyan", width=30)
    table.add_column("Value", style="green", width=15)
    table.add_column("Raw", style="dim", width=15)
    return table

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

#parse message: run time
def parse_run_time(recv_dict: dict, msg:bytes, format: Table):
    # msg level : struct
    msg_st = recv_dict.get("msg_struct",[])
    print(f"msg_struct count: {len(msg_st)}")
    for st in msg_st: 
        offset: int = st.get('byte_offset')
        data_type:str = st.get('data_type')

        # u8 u16 u32 match
        data = 0
        scale: float = st.get('scale', 1.0)
        byte_seq: str = st.get('byte_seq')
        match data_type:
            case "u8":        
                data = msg[offset]
                #format.add_row(f"{st.get('description',str)} : {data}")

            case "u16":
                if byte_seq != "big":
                    data = (msg[offset + 1] << 8) + msg[offset]            
                else:
                    data = (msg[offset] << 8) + msg[offset + 1]
                # handle sensor fault
                if data == SENSOR_FAULT:
                    data = 0
                    #format.add_row(f"{st.get('description',str)} : SENSOR FAULT")
                    #continue
                else:    
                    # scale
                    if scale != None:
                        data = data * scale
                        #format.add_row(f"{st.get('description',str)} : {data}, high:{msg[offset]:#x}, low:{msg[offset + 1]:#x}")
            case "u32":
                if byte_seq != "big":
                    data = (msg[offset + 3] << 24) + (msg[offset + 2] << 16) + (msg[offset + 1] << 8) + msg[offset]            
                else:
                    data = (msg[offset] << 24) + (msg[offset + 1] << 16) + (msg[offset + 2] << 8) + msg[offset + 3]

        # show the data
        format.add_row(f"{st.get('description',str)}", f"{data}", f"high:{msg[offset]:#x}, low:{msg[offset + 1]:#x}")


# parse and show message in terminal interface
def parse_and_show_msg(reply:bytes, msg_dict: dict):
    msg_list:list = msg_dict.get("recv",[])

    # match the message type
    match_msg = None
    # list level: recv
    for msg_recv in msg_list:
        msg_type_desc = msg_recv.get("msg_type_desc")
        msg_type_code = msg_recv.get("msg_type_code",{})
        value = msg_type_code.get("value");   
        type_code_offset = msg_type_code.get("byte_offset")
        print(f"current message type code : {value:#x}")
        if type_code_offset is not None and reply[type_code_offset] == value:
            match_msg = msg_recv
            if match_msg == None:
                print("no matched message")
            else:
                print(f"matched message type : {msg_type_desc}")
            break
    # get format table
    format = init_display_format()
    console = Console()

    match value:
        case 0x70:
            parse_run_time(match_msg, reply,format)

    console.print(format)


