import tensorflow as tf
from magenta.models.onsets_frames_transcription import model as of_model
import note_seq

import mido
from fastdtw import fastdtw
from scipy.spatial.distance import euclidean

def audio2midi(unique_dir, audio_sample_rate=16000):
    checkpoint_path = tf.train.latest_checkpoint(checkpoint_dir)

    model = of_model.OnsetsAndFrames()
    model.initialize()
    model.load_weights(checkpoint_path)

    audio_tensor = tf.io.read_file(f'{unique_dir}/part.wav')
    audio_samples = note_seq.audio_io.wav_data_to_samples(audio_tensor, sample_rate=audio_sample_rate)

    midi = model.transcribe(audio_samples)

    note_seq.sequence_proto_to_midi_file(midi, f'{unique_dir}/audio2midi_output.mid')

def tracking(whole_midi_path, part_midi_path):
    whole_midi_notes = extract_notes(read_midi(whole_midi_path))
    part_midi_notes = extract_notes(read_midi(part_midi_path))

    distance, path = fastdtw(whole_midi_notes, part_midi_notes, dist=euclidean)
    print(f"Distance: {distance}")

    start_position = path[0][0]
    print(f"B MIDI starts at position {start_position} in MIDI A")

    start_time = calculate_dtw_time(whole_midi_notes, start_position)
    print(f"B MIDI starts at {start_time} seconds in MIDI A")

    return start_position, start_time

def read_midi(file_path):
    # MIDI 파일 읽기
    midi_data = mido.MidiFile(file_path)
    return midi_data

def extract_notes(midi_file):
    notes = []
    for msg in midi_file:
        if not msg.is_meta and msg.type == 'note_on':
            note = msg.note  # MIDI 노트 번호
            velocity = msg.velocity  # 타격 강도
            time = msg.time  # 이벤트 발생 시간
            if velocity > 0:
                notes.append((note, velocity, time))
    return notes

def calculate_dtw_time(midi_data, position):
    time = 0
    count = 0
    for msg in midi_data:
        if not msg.is_meta and msg.type == 'note_on' and msg.velocity > 0:
            if count == position:
                break
            count += 1
            time += msg.time
    return time
