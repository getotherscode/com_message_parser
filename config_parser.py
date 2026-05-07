import tomllib
from pathlib import Path
from rich.table import Table
from rich.console import Console

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

#parse message: run time
def parse_run_time(recv_dict: dict, msg:bytes):
    # msg level : struct
    msg_st = recv_dict.get("msg_struct",[])
    print(f"msg_struct count: {len(msg_st)}")

    # create the table to format showed data in terminal
    bytes_t = Table(title="Run-Time Data")

    bytes_t.add_column("Type", style="dim", width=8)
    bytes_t.add_column("Desc", style="cyan", width=25)
    bytes_t.add_column("Value", style="green", width=15,)
    bytes_t.add_column("Raw Data (Hex)", style="yellow", width=20)

    for st in msg_st: 
        byte_desc = st.get('description',str)
        offset: int = st.get('byte_offset')
        data_type:str = st.get('data_type')

        # u8 u16 u32 match
        data = 0
        scale: float = st.get('scale', 1.0)
        byte_seq: str = st.get('byte_seq')
        bit_array = st.get('bits')

        match data_type:
            case "u8":        
                data = msg[offset]
                bytes_t.add_row("[bold blue]u8[/bold blue]",f"{byte_desc}", f"{data}", f"{msg[offset]:02x}")
                bytes_t.add_section()

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

                if bit_array:
                    # main data Bytes
                    bytes_t.add_row("[bold blue]u16[/bold blue]",f"{byte_desc}", "",f"h:{msg[offset]:02x}, l:{msg[offset + 1]:02x}")
                    # Delimiter
                    bytes_t.add_section()
                    # child data bits
                    for bit in bit_array:
                        bit_offset = bit.get('bit_offset')
                        bit_desc = bit.get('description')
                        bit_value = ((1 << bit_offset) & data) >> bit_offset
                        bytes_t.add_row("[bold blue]bit[/bold blue]",f"{bit_desc}", f"{bit_value}")
                    bytes_t.add_section()
                else:
                    bytes_t.add_row("[bold blue]u16[/bold blue]",f"{byte_desc}", f"{data}",f"h:{msg[offset]:02x}, l:{msg[offset + 1]:02x}")
                    bytes_t.add_section()
                    
            case "u32":
                if byte_seq != "big":
                    data = (msg[offset + 3] << 24) + (msg[offset + 2] << 16) + (msg[offset + 1] << 8) + msg[offset]            
                else:
                    data = (msg[offset] << 24) + (msg[offset + 1] << 16) + (msg[offset + 2] << 8) + msg[offset + 3]

                bytes_t.add_row("[bold blue]u32[/bold blue]", f"{byte_desc}", f"{data}",f"h3:{msg[offset]:02x}, h2:{msg[offset + 1]:02x}, \
                                 h1:{msg[offset + 2]:02x}, h0:{msg[offset + 3]:02x}")
                bytes_t.add_section()
    
    # show the data
    console = Console()
    console.print(bytes_t)
            
        


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

    match value:
        case 0x70:
            parse_run_time(match_msg, reply)
    


