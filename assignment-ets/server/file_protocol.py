import json
import logging
import shlex
import sys
from typing import Dict, Any, Callable, List

from file_interface import FileInterface

"""
* class FileProtocol bertugas untuk memproses 
data yang masuk, dan menerjemahkannya apakah sesuai dengan
protokol/aturan yang dibuat

* data yang masuk dari client adalah dalam bentuk bytes yang 
pada akhirnya akan diproses dalam bentuk string

* class FileProtocol akan memproses data yang masuk dalam bentuk
string
"""

logger = logging.getLogger("FileProtocol")
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)
logger.setLevel(logging.INFO)


class FileProtocol:
    def __init__(self):
        self.file = FileInterface()
        self.command_handlers = {
            'list': self._handle_list,
            'get': self._handle_get,
            'upload': self._handle_upload,
            'delete': self._handle_delete,
        }
    
    def proses_string(self, command='', filename='', content=None):
        logger.info(f"Processing command: '{command}' with filename: '{filename}'")
        
        try:
            command = command.lower().strip()
            
            if command in self.command_handlers:
                return self.command_handlers[command](filename, content)
            else:
                logger.warning(f"Unknown command received: {command}")
                return {"status": "ERROR", "data": "Unknown command"}
                
        except Exception as e:
            logger.error(f"Error processing command: {str(e)}")
            return {"status": "ERROR", "data": str(e)}
    
    def _handle_list(self, filename=None, content=None):
        logger.info("Executing LIST command")
        return self.file.list()
    
    def _handle_get(self, filename='', content=None):
        if not filename:
            logger.warning("GET command missing filename")
            return {"status": "ERROR", "data": "Filename required for GET command"}
            
        logger.info(f"Executing GET command for file: {filename}")
        return self.file.get([filename])
    
    def _handle_upload(self, filename='', content=None):
        if not filename:
            logger.warning("UPLOAD command missing filename")
            return {"status": "ERROR", "data": "Filename required for UPLOAD command"}
            
        if content is None:
            logger.warning("UPLOAD command missing content")
            return {"status": "ERROR", "data": "Content required for UPLOAD command"}
            
        logger.info(f"Executing UPLOAD command for file: {filename}")
        return self.file.upload([filename, content])
    
    def _handle_delete(self, filename='', content=None):
        if not filename:
            logger.warning("DELETE command missing filename")
            return {"status": "ERROR", "data": "Filename required for DELETE command"}
            
        logger.info(f"Executing DELETE command for file: {filename}")
        return self.file.delete([filename])


if __name__=='__main__':
    fp = FileProtocol()
    print(fp.proses_string("LIST"))
    print(fp.proses_string("GET", "pokijan.jpg"))