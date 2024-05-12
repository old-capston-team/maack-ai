import io
import requests
from pydantic import BaseModel

import fitz
from PIL import Image

import os
import time
import uuid

def create_unique_folder():
    # 현재 시간과 UUID를 조합하여 폴더 이름 생성
    folder_name = f"{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4()}"
    os.makedirs(folder_name)
    return folder_name

def pdf_bytes_to_images(pdf_bytes):
    # 메모리 상의 PDF 바이트 데이터로부터 문서 객체 생성
    pdf_document = fitz.open("pdf", pdf_bytes)
    
    images = []  # 이미지를 저장할 리스트
    for page_number in range(pdf_document.page_count):
        page = pdf_document[page_number]
        # 페이지를 이미지로 변환 (여기서는 300 DPI를 사용)
        pix = page.get_pixmap(matrix=fitz.Matrix(300 / 72, 300 / 72))
        img_bytes = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_bytes))
        images.append(img)  # 이미지 리스트에 추가
    
    pdf_document.close()  # 문서 객체 닫기
    return images  # 이미지 바이트 리스트 반환
    
def file_to_bytes(filename):
    # 파일을 바이너리 모드로 열고 내용을 읽음
    with open(filename, 'rb') as file:
        file_bytes = file.read()
    return file_bytes

def download_file_from_server(url, save_path):
    # 서버에서 파일을 받아옴
    response = requests.get(url)
    # 응답을 파일로 저장
    with open(save_path, 'wb') as file:
        file.write(response.content)

class PDFJSONRequest(BaseModel):
    PDF: bytes
    
class TrackingRequest(BaseModel):
    page: int
    mp3: bytes