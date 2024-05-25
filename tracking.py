import mido
from fastdtw import fastdtw
from scipy.spatial.distance import euclidean

import pretty_midi
from pydub import AudioSegment
from madmom.features.onsets import OnsetPeakPickingProcessor, RNNOnsetProcessor
from madmom.features.notes import RNNPianoNoteProcessor, NotePeakPickingProcessor
import os

def merge_notes(notes, threshold_time=0.1):
    """
    Merge close notes into one.
    :param notes: list of tuples (pitch, onset, duration)
    :param threshold_time: maximum time difference to merge notes
    :return: list of merged notes
    """
    if not notes:
        return []

    # Sort notes by onset time
    notes.sort(key=lambda x: x[1])

    merged_notes = []
    current_note = list(notes[0])
    
    for note in notes[1:]:
        if note[1] - current_note[1] < threshold_time:
            # Merge the note
            current_note[0] = note[0]  # Use the latest pitch
            current_note[2] = max(current_note[2], note[1] + note[2] - current_note[1])  # Update the duration
        else:
            # Append the current note and start a new one
            merged_notes.append(tuple(current_note))
            current_note = list(note)

    # Append the last note
    merged_notes.append(tuple(current_note))

    return merged_notes

def audio_to_midi(audio_path, midi_path, thres=0.9, smooth=0.2):=
    unique_folder = os.path.dirname(audio_path)

    # Load the audio file and convert to mono
    audio = AudioSegment.from_file(audio_path).set_channels(1)
    audio.export(f"{unique_folder}/temp.wav", format="wav")
    
    # Use madmom to detect onsets with higher sensitivity
    onset_processor = RNNOnsetProcessor()
    onsets = onset_processor(f"{unique_folder}/temp.wav")
    onset_processor = OnsetPeakPickingProcessor(fps=100, threshold=thres, smooth=smooth
    )  # Adjusted threshold and smooth
    onsets = onset_processor(onsets)

    # Use madmom to detect notes with higher sensitivity
    note_processor = RNNPianoNoteProcessor()
    notes = note_processor(f"{unique_folder}/temp.wav")
    note_processor = NotePeakPickingProcessor(threshold=thres, smooth=smooth
    )  # Adjusted threshold and smooth
    notes = note_processor(notes)

    # Create a list of (pitch, onset, duration)
    note_list = [(int(note[1]), note[0], 0.5) for note in notes]  # Default duration set to 0.5 seconds

    # Merge close notes
    merged_notes = merge_notes(note_list)

    # Create PrettyMIDI object
    midi = pretty_midi.PrettyMIDI()
    instrument = pretty_midi.Instrument(program=0)

    # Convert merged notes to MIDI notes
    for pitch, onset, duration in merged_notes:
        midi_note = pretty_midi.Note(
            velocity=100,  # Set a fixed velocity
            pitch=pitch,
            start=onset,
            end=onset + duration  # Use the merged duration
        )
        instrument.notes.append(midi_note)

    midi.instruments.append(instrument)

    # Write the MIDI file
    with open(midi_path, "wb") as output_file:
        midi.write(output_file)

def tracking(whole_midi_path, part_midi_path):
    whole_midi_notes = extract_notes(read_midi(whole_midi_path))
    part_midi_notes = extract_notes(read_midi(part_midi_path))

    distance, path = fastdtw(whole_midi_notes, part_midi_notes, dist=euclidean)

    start_position = path[0][0]

    start_time = calculate_dtw_time(whole_midi_notes, start_position)

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
