import os
import json
import base64
from glob import glob

class FileInterface:
    def __init__(self):
        if not os.path.exists('files'):
            os.makedirs('files')
        os.chdir('files/')

    def list(self, params=[]):
        try:
            filelist = glob('*.*')
            return dict(status='OK', data=filelist)
        except Exception as e:
            return dict(status='ERROR', data=str(e))

    def get(self, params=[]):
        try:
            filename = params[0]
            if not filename:
                return dict(status='ERROR', data='Nama file tidak valid')
            with open(filename, 'rb') as f:
                file_data = base64.b64encode(f.read()).decode()
            return dict(status='OK', data_namafile=filename, data_file=file_data)
        except Exception as e:
            return dict(status='ERROR', data=str(e))

    def upload(self, params=[]):
        try:
            if len(params) < 2:
                return dict(status='ERROR', data='Parameter tidak lengkap')
            filename = params[0]
            file_data = base64.b64decode(params[1])
            with open(filename, 'wb') as f:
                f.write(file_data)
            return dict(status='OK', data=f'File {filename} berhasil diupload')
        except Exception as e:
            return dict(status='ERROR', data=str(e))

    def delete(self, params=[]):
        try:
            filename = params[0]
            if not filename:
                return dict(status='ERROR', data='Nama file tidak valid')
            os.remove(filename)
            return dict(status='OK', data=f'File {filename} berhasil dihapus')
        except Exception as e:
            return dict(status='ERROR', data=str(e))

if __name__=='__main__':
    f = FileInterface()
    print(f.list())
    print(f.get(['test.txt']))