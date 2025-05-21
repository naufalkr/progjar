import json
import logging
import shlex
import base64

from n_file_interface import FileInterface

"""
* class FileProtocol bertugas untuk memproses 
data yang masuk, dan menerjemahkannya apakah sesuai dengan
protokol/aturan yang dibuat

* data yang masuk dari client adalah dalam bentuk bytes yang 
pada akhirnya akan diproses dalam bentuk string

* class FileProtocol akan memproses data yang masuk dalam bentuk
string
"""



class FileProtocol:
    def __init__(self):
        self.file = FileInterface()
        
    def proses_string(self,string_datamasuk=''):
        # Bersihkan string dari karakter kontrol seperti \r\n
        string_datamasuk = string_datamasuk.strip()
        logging.warning(f"string diproses: {string_datamasuk[:100]}...")  # Hanya log sebagian dari data untuk menghindari log yang terlalu besar
        try:
            # Handle UPLOAD command specially due to potential large data
            if string_datamasuk.startswith('UPLOAD '):
                # Find the first two spaces to separate command, filename, and data
                first_space = string_datamasuk.find(' ')
                if first_space != -1:
                    second_space = string_datamasuk.find(' ', first_space + 1)
                    if second_space != -1:
                        c_request = 'upload'
                        filename = string_datamasuk[first_space + 1:second_space].strip()
                        file_data = string_datamasuk[second_space + 1:].strip()
                        
                        # Ensure proper base64 padding
                        padding_needed = len(file_data) % 4
                        if padding_needed:
                            file_data += '=' * (4 - padding_needed)
                            
                        # Verify this is valid base64 data
                        try:
                            base64.b64decode(file_data)
                            params = [filename, file_data]
                            cl = self.file.upload(params)
                            return json.dumps(cl)
                        except Exception as e:
                            logging.error(f"Base64 decode error: {str(e)}")
                            return json.dumps(dict(status='ERROR', data=f'Invalid base64 data: {str(e)}'))
            
            # Process other commands normally
            parts = string_datamasuk.split(' ', 2)  # Pisahkan maksimal jadi 3 bagian (command, filename, data)
            c_request = parts[0].strip().lower()
            logging.warning(f"memproses request: {c_request}")
            
            params = []
            # Tentukan parameter berdasarkan jenis request
            if c_request == 'list':
                # LIST tidak memerlukan parameter tambahan
                pass
            elif c_request == 'get' and len(parts) > 1:
                # GET hanya memerlukan nama file
                params = [parts[1].strip()]
            elif c_request == 'delete' and len(parts) > 1:
                # DELETE hanya memerlukan nama file
                params = [parts[1].strip()]
            else:
                # Jika format tidak sesuai
                return json.dumps(dict(status='ERROR', data='Format perintah tidak valid'))
            
            # Panggil method yang sesuai di FileInterface
            if c_request in ['list', 'get', 'delete']:
                cl = getattr(self.file, c_request)(params)
                return json.dumps(cl)
            else:
                return json.dumps(dict(status='ERROR', data='request tidak dikenali'))
        except Exception as e:
            logging.error(f"Error processing request: {str(e)}")
            return json.dumps(dict(status='ERROR', data=f'request error: {str(e)}'))


if __name__=='__main__':
    #contoh pemakaian
    fp = FileProtocol()
    print(fp.proses_string("LIST"))
    print(fp.proses_string("GET pokijan.jpg"))
    # print(fp.proses_string("UPLOAD test.txt SGVsbG8gd29ybGQ="))
    # print(fp.proses_string("DELETE test.txt"))
