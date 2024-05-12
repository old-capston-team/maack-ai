from fastapi import FastAPI
import uvicorn

from pdf2midi.main import imgs2midi
from server_utils import *

import shutil

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "root"}

@app.post("/pdf_to_midi")                         # post 사용, end-point로 pdf_to_midi
async def pdf_to_midi(item: PDFJSONRequest):      # pdf를 받으면 변환된 midi를 response
    tmp_folder = create_unique_folder()           # 중복이 발생하지 않는 폴더 생성
    pdf_images = pdf_bytes_to_images(item.PDF)    # PDF bytes를 image들로 변환
    midi_list = imgs2midi(pdf_images, tmp_folder) # 이미지를 이용해 midi 생성 (볼 필요 X)
    response = {"midi": midi_list}                # response 생성
    shutil.rmtree(tmp_folder)                     # 폴더 재귀 삭제
    return response

@app.post("/tracking_progress")
async def tracking_progress(item: TrackingRequest):
    page_request = item.page
    mp3_request = item.midis
    download_file_from_server(pdf_url)
    pdf_imgs = convert_pdf_from_bytes(pdf_request)

    return "Updated"

uvicorn.run(app, host='0.0.0.0', port=8000)