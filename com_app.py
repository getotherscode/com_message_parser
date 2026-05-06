import serial
import serial.tools.list_ports

# show the avaliable ports list, find the target port
# f is content in {} will be format string

def load_the_com(com_desc:str, baudrate:int):
    print(f"target is % {com_desc} %")

    # find the target com in avalible ports list
    ports = serial.tools.list_ports.comports()
    targetport = None
    if not ports:
        print("no ports can be found")
    else:
        print("ports list :")
        for port in ports:
            print(f"com: {port.device} - description: {port.description} ") 
            if com_desc in port.description:
                targetport = port
                break
            else:
                continue

    if targetport is not None:
        print(f"find the target port :{targetport.device}, description:{targetport.description}")
    else:
        print("not find the target")
        exit()

        

    # config the port and check if it can be used
    target_serial = serial.Serial()

    target_serial.port = targetport.device
    target_serial.baudrate = baudrate
    target_serial.BYTESIZES = serial.EIGHTBITS
    target_serial.parity = serial.PARITY_NONE
    target_serial.stopbits = 1
    target_serial.timeout = 1

    try:
        target_serial.open()
        print(f"{target_serial.port} open success")
    except Exception as e:
        print(f"{target_serial.port} open failed, Error Msg :{e}")
        target_serial.close()
    return target_serial



