import crcmod.predefined
from typing import Callable
import time

#rich
#from rich.table import Table
#from rich.live import Live
#from rich.console import Console
#from rich.columns import Columns

#textual
from textual.app import App, ComposeResult
from textual.widgets import DataTable, Header, Footer, RichLog
from textual.worker import Worker, get_current_worker

#code file
from config_parser import load_toml_file, parse_msg, frame_spliter
from com_app import load_the_com

# MACRO
MODE = "listen"
FRAME_TIMEOUT = 0.015

# UI
class MessageMonitorApp(App):
    TITLE = "Monitor"
    BINDINGS = [("q","quit","Quit")]
    CSS = """
    #main-table {
        height: 1fr; /* 占据剩余所有空间 */
    }
    #com-log {
        height: 6;   /* 日志区固定 6 行高度 */
        border-top: solid green; /* 加个上边框区分 */
    }
    """

    def compose(self)->ComposeResult:
        yield Header()
        yield DataTable(id="main-table")
        yield RichLog(id="com-log", highlight=True, markup=True) # 用来显示串口日志
        yield Footer()

    def on_mount(self)->None:
        table = self.query_one(DataTable)
        self.col_key_type = table.add_column("Type")
        self.col_key_desc = table.add_column("Desc")
        self.col_key_value = table.add_column("Value")
        self.col_key_raw = table.add_column("Raw Data (Hex)")
        
        self.row_keys = {}

        # load the configure file    
        config_obj = load_toml_file()
        serial_config = config_obj.get("serial")
        self.msg_dict = config_obj.get("message")

        # configure and open the com, loop query the run time data and parse the data by toml
        self.com_obj = load_the_com(serial_config.get("description"),serial_config.get("baudrate"))
        query_run_time_msg:bytes = bytes.fromhex("02 70 00")
        
        # get crc check
        crc_fun:Callable = crcmod.predefined.mkPredefinedCrcFun('modbus')
        crc_value:int = crc_fun(query_run_time_msg)

        # splice the message
        self.query_run_time_msg_with_crc:bytes = query_run_time_msg + crc_value.to_bytes(2,'little')

        # start thread
        self.run_worker(self.serial_worker, thread=True, exclusive=True)
    
    def serial_worker(self) -> None:
        worker = get_current_worker()
        log = self.query_one(RichLog)
        try:
            for frame in frame_spliter(self.com_obj, FRAME_TIMEOUT):
                if worker.is_cancelled:
                    break
                if MODE == "poll":
                    # send query message
                    self.com_obj.write(self.query_run_time_msg_with_crc)
                    self.call_from_thread(log.write, f"[dim]SEND: {' '.join(f'{b:02X}' for b in self.query_run_time_msg_with_crc)}[/dim]")
                    time.sleep(1)

                elif MODE == "listen":
                    pass

                new_data = parse_msg(frame, self.msg_dict, len(frame))

                if new_data is not None:
                    # log
                    self.call_from_thread(log.write, f"[bold green]RECV: {' '.join(f'{b:02x}' for b in frame)}[/bold green]")
                    # push new data update table
                    self.call_from_thread(self.update_table, new_data)
        except Exception as e:
            self.call_from_thread(log.write, f"[bold red]ERROR: {e}[/bold red]")
        finally:
            if self.com_obj and self.com_obj.is_open:
                self.com_obj.close()
    
    def update_table(self, data_list: list)-> None:
        table = self.query_one(DataTable)

        for row_data in data_list:
            row_id = row_data["id"]
            if row_id not in self.row_keys:
                row_key = table.add_row(
                    row_data["type"], 
                    row_data["desc"], 
                    row_data["value"], 
                    row_data["raw"])
                self.row_keys[row_id] = row_key
            else:
                row_key = self.row_keys[row_id]
                if row_key in table.rows:
                    try:
                        table.update_cell(row_key, self.col_key_value, row_data["value"])
                        table.update_cell(row_key, self.col_key_raw, row_data["raw"])
                    except Exception as e:
                        log = self.query_one(RichLog)
                        log.write(f"[bold red]Update Error at {row_id}: {e}[/bold red]")
                else:
                    new_row_key = table.add_row(
                        row_data["type"], 
                        row_data["desc"], 
                        row_data["value"], 
                        row_data["raw"]
                    )
                    self.row_keys[row_id] = new_row_key

if __name__ == "__main__":
    app = MessageMonitorApp()
    app.run()
        