import io
import requests
from pydantic import BaseModel
from fastapi import WebSocket

import fitz
from PIL import Image

import os
import time
import uuid

def create_unique_folder():
    # 현재 시간과 UUID를 조합하여 폴더 이름 생성
    folder_name = f"{time.time()}_{uuid.uuid4()}"
    os.makedirs(folder_name)
    return folder_name

def download_pdf(url, job_dir):
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()  # Check if the request was successful
        
        with open(os.path.join(job_dir, "convert_it.pdf"), 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
    
    except requests.exceptions.RequestException as e:
        print(f"Failed to download PDF: {e}")

def convert_pdf_to_images(job_dir, dpi=300):
    document = fitz.open(os.path.join(job_dir, "convert_it.pdf"))
    
    images = []
    for page_number in range(len(document)):
        page = document.load_page(page_number)  # 페이지 객체 로드
        pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72)) 
        image_path = os.path.join(job_dir, f"page_{page_number + 1}.png")
        pix.save(image_path)  # 이미지 파일로 저장
        img = Image.open(image_path)
        images.append(img)

    document.close()

    return images

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
    
    pdf_document.close()
    return images 

def extract_pdfImg_from_json(json_data, job_dir):
    pdf_url = json_data.url

    download_pdf(pdf_url, job_dir)
    pdf_imgs = convert_pdf_to_images(job_dir)
    return pdf_imgs
    
def file_to_bytes(filename):
    # 파일을 바이너리 모드로 열고 내용을 읽음
    with open(filename, 'rb') as file:
        file_bytes = file.read()
    return file_bytes

def bytes_to_wav_file(file_bytes, save_dir):
    with open(os.path.join(save_dir, "part.m4a"), 'wb') as file:
        file.write(file_bytes)

def download_midi_from_server(sheet_name, save_dir):
    # 서버에서 파일을 받아옴
    url = f"http://0.0.0.0:30080/{sheet_name}"
    response = requests.get(url)
    
    # 응답을 파일로 저장
    if response.status_code == 200:
        with open(os.path.join(save_dir, f"{sheet_name}.mid"), 'wb') as file:
            file.write(response.content)
        return True
    else:
        return False

class PDFJSONRequest(BaseModel):
    url: str
    
class TrackingInitRequest(BaseModel):
    sheet_name: str

class TrackingAudioRequest(BaseModel):
    audio: bytes

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)