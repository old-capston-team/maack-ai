from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
import uvicorn

from pdf2midi.main import imgs2midi
from server_utils import *
from tracking import *

import shutil

app = FastAPI()

manager = ConnectionManager()

@app.get("/")
async def root():
    return {"message": "root"}

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("icon/favicon.ico")

@app.post("/midi_to_xml")
async def midi_to_xml(item: MTXJSONRequest):
    tmp_folder = create_unique_folder()
    download_midi_from_server(tmp_folder, url=item.url)
    score = converter.parse(os.path.join(tmp_folder, "target.mid"))
    output_path = os.path.join(tmp_folder, 'output.musicxml')
    score.write('musicxml', fp=output_path)
    response = {"musicxml":file_to_bytes(output_path)}
    shutil.rmtree(tmp_folder)
    return response

@app.post("/pdf_to_midi")
async def pdf_to_midi(item: PDFJSONRequest):
    tmp_folder = create_unique_folder()
    pdf_images = extract_pdfImg_from_json(item, tmp_folder)
    midi_bytes = imgs2midi(pdf_images, tmp_folder)
    response = {"midi": midi_bytes}
    shutil.rmtree(tmp_folder)
    return response

@app.websocket("/tracking_progress")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        tmp_folder = create_unique_folder()
        current_progress_time, offset = 0, 0

        meta_data = await websocket.receive_json()
        sheetMusicId = meta_data['sheet_music_id']

        tracking_flag = download_midi_from_server(tmp_folder, sheetMusicId=sheetMusicId)
        await manager.send_message(str({"tracking_flag":tracking_flag}), websocket)

        whole_midi = read_midi(os.path.join(tmp_folder, "target.mid"))
        while True:
            data = await websocket.receive_json()
            is_finished = data['is_finished']
            if not is_finished:
                audio_request = data['recording']

                bytes_to_wav_file(audio_request, tmp_folder)
                audio_to_midi(tmp_folder)
                part_midi = read_midi(os.path.join(tmp_folder, "audio2midi_output.mid"))
                best_start, best_end, play_time = tracking(whole_midi, part_midi, current_progress_time)
                
                response = {
                    "best_start": best_start + offset,
                    "best_end": best_end + offset
                }
                offset += best_end
                current_progress_time = play_time
                await manager.send_message(str(response), websocket)
            else: break
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    shutil.rmtree(tmp_folder)

if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0', port=80)