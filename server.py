from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
import uvicorn

from pdf2midi.main import imgs2midi
from server_utils import *
from tracking import audio_to_midi, tracking, extract_pitch_duration

import shutil

app = FastAPI()

manager = ConnectionManager()

@app.get("/")
async def root():
    return {"message": "root"}

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("icon/favicon.ico")

# post 사용, end-point로 pdf_to_midi
@app.post("/pdf_to_midi")
# pdf를 받으면 변환된 midi를 response
async def pdf_to_midi(item: PDFJSONRequest):
    tmp_folder = create_unique_folder()
    # 중복이 발생하지 않는 폴더 생성 (볼 필요 X)
    pdf_images = extract_pdfImg_from_json(item, tmp_folder)
     # 이미지를 이용해 midi 생성 (볼 필요 X)
    midi_bytes = imgs2midi(pdf_images, tmp_folder)
    # response 생성
    response = {"midi": midi_bytes}
    # 폴더를 재귀적으로 삭제
    shutil.rmtree(tmp_folder)
    return response

@app.websocket("/tracking_progress")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        tmp_folder = create_unique_folder()
        current_progress_time = 0

        meta_data = await websocket.receive_json()
        sheet_name = meta_data['sheet_name']

        tracking_flag = download_midi_from_server(sheet_name, tmp_folder)
        await manager.send_message({"tracking_flag":tracking_flag}, websocket)

        whole_midi = extract_pitch_duration(os.path.join(tmp_folder, f"{sheet_name}.mid"))

        while True:
            tracking_start_time = time.time()
            data = await websocket.receive_json()
            audio_request = data['audio']

            bytes_to_wav_file(audio_request, tmp_folder)
            audio_to_midi(tmp_folder)
            part_midi = extract_pitch_duration(os.path.join(tmp_folder, "audio2midi_output.mid"))
            best_start, best_end, play_time = tracking(whole_midi, part_midi, current_progress_time)
            os.remove(os.path.join(tmp_folder, "audio2midi_output.mid"))
            
            response = {
                "best_start": best_start,
                "best_end": best_end
            }
            current_progress_time += (time.time() - tracking_start_time) + play_time
            await manager.send_message(response, websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        shutil.rmtree(tmp_folder)

if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0', port=80)