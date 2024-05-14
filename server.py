from fastapi import FastAPI
import uvicorn

from pdf2midi.main import imgs2midi
from server_utils import *
from tracking import audio2midi, tracking

import shutil

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "root"}

@app.post("/pdf_to_midi")                         # post 사용, end-point로 pdf_to_midi
async def pdf_to_midi(item: PDFJSONRequest):      # pdf를 받으면 변환된 midi를 response
    tmp_folder = create_unique_folder()           # 중복이 발생하지 않는 폴더 생성 (볼 필요 X)
    pdf_images = pdf_bytes_to_images(item.PDF)    # PDF bytes를 image들로 변환 (볼 필요 X)
    midi_list = imgs2midi(pdf_images, tmp_folder) # 이미지를 이용해 midi 생성 (볼 필요 X)
    response = {"midi": midi_list}                # response 생성
    shutil.rmtree(tmp_folder)                     # 폴더를 재귀적으로 삭제
    return response

@app.post("/tracking_progress")
async def tracking_progress(item: TrackingRequest):
    page_request = item.page
    sheet_name = item.sheet_name
    audio_request = item.audio
    tmp_folder = create_unique_folder()
    # 요청 받은 audio 파일을 wav 형태로 저장함 (볼 필요 X)
    bytes_to_wav_file(audio_request, tmp_folder) 
    # 성훈-규혁 서버에서 연주중인 악보와 page에 해당하는 midi 파일을 받아옴 (여긴 봐야할 듯)
    download_midi_from_server(sheet_name, page_request, tmp_folder) 
    # wav 파일을 midi로 변환 (볼 필요 X)
    audio2midi(f"{sheet_name}_{page_request}.mid", tmp_folder) 
    # 어디쯤 연주중인지 추적 (볼 필요 X)
    start_position, start_time = tracking(f"{tmp_folder}/audio2midi_output.mid", 
                                          f"{tmp_folder}/{sheet_name}_{page_request}.mid") 
    shutil.rmtree(tmp_folder) 
    return {"start_position":start_position, "start_time":start_time}

uvicorn.run(app, host='0.0.0.0', port=8000)