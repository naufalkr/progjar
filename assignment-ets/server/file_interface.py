import os
import json
import base64
import logging
import functools
from glob import glob
from typing import Dict, List, Any, Optional, Callable


def error_handling(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logging.error(f"Error in {func.__name__}: {str(e)}")
            return {"status": "ERROR", "data": str(e)}
    return wrapper


class FileInterface:
    def __init__(self):
        self._ensure_files_directory()
        os.chdir('files/')
    
    def _ensure_files_directory(self):
        if not os.path.exists('files'):
            os.makedirs('files')
            logging.info("Created files directory")
    
    @error_handling
    def list(self, params=[]):
        filelist = [f for f in os.listdir('.') if os.path.isfile(f)]
        return {"status": "OK", "data": filelist}
    
    @error_handling
    def get(self, params=[]):
        filename = params[0] if params else ""
        if not filename:
            return None
            
        with open(filename, 'rb') as file:
            binary_data = file.read()
            
        encoded_content = self._encode_binary_data(binary_data)
        
        return {
            "status": "OK", 
            "data_namafile": filename, 
            "data_file": encoded_content
        }
    
    @error_handling
    def upload(self, params=[]):
        if len(params) < 2:
            return {"status": "ERROR", "data": "Missing parameters"}
            
        filename, encoded_content = params[0], params[1]
        
        if not filename or not encoded_content:
            return {"status": "ERROR", "data": "Invalid parameters"}
        
        self._write_decoded_file(filename, encoded_content)
        
        return {"status": "OK", "data": f"File {filename} uploaded successfully"}
    
    @error_handling
    def delete(self, params=[]):
        filename = params[0] if params else ""
        
        if not filename:
            return {"status": "ERROR", "data": "Invalid filename"}
        
        if not self._file_exists(filename):
            return {"status": "ERROR", "data": "File not found"}
            
        os.unlink(filename)
        
        return {"status": "OK", "data": f"File {filename} deleted successfully"}
    
    def _encode_binary_data(self, data: bytes) -> str:
        return base64.b64encode(data).decode('utf-8')
    
    def _decode_base64_data(self, encoded_data: str) -> bytes:
        return base64.b64decode(encoded_data)
    
    def _write_decoded_file(self, filename: str, encoded_content: str) -> None:
        binary_data = self._decode_base64_data(encoded_content)
        with open(filename, 'wb') as file:
            file.write(binary_data)
    
    def _file_exists(self, filename: str) -> bool:
        return os.path.isfile(filename)


if __name__=='__main__':
    f = FileInterface()
    print(f.list())
    print(f.get(['pokijan.jpg']))