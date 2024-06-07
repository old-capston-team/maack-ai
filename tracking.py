from fastdtw import fastdtw
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

def audio_to_midi(unique_folder, thres=0.9, smooth=0.2):
    audio_path = os.path.join(unique_folder, "part.m4a")
    midi_path = os.path.join(unique_folder, "audio2midi_output.mid")

    # Load the audio file and convert to mono
    audio = AudioSegment.from_file(audio_path).set_channels(1)
    audio.export(f"{unique_folder}/temp.wav", format="wav")
    
    # Use madmom to detect onsets with higher sensitivity
    onset_processor = RNNOnsetProcessor()
    onsets = onset_processor(f"{unique_folder}/temp.wav")
    onset_processor = OnsetPeakPickingProcessor(fps=100, threshold=thres, smooth=smooth)
    onsets = onset_processor(onsets)

    # Use madmom to detect notes with higher sensitivity
    note_processor = RNNPianoNoteProcessor()
    notes = note_processor(f"{unique_folder}/temp.wav")
    note_processor = NotePeakPickingProcessor(threshold=thres, smooth=smooth)
    notes = note_processor(notes)

    # Create a list of (pitch, onset, duration)
    note_list = [(int(note[1]), note[0], 0.5) for note in notes] 

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

def read_midi(midi_path):
    """
    Extract pitch and duration from a MIDI file.
    :param midi_path: Path to the MIDI file
    :return: List of tuples (pitch, duration)
    """
    midi_data = pretty_midi.PrettyMIDI(midi_path)
    notes = []

    for instrument in midi_data.instruments:
        for note in instrument.notes:
            pitch = note.pitch
            duration = note.end - note.start
            notes.append((pitch, note.start, duration))

    return notes

def calculate_dtw_distance(seq1, seq2):
    """
    Calculate the DTW distance between two sequences.
    :param seq1: First sequence
    :param seq2: Second sequence
    :return: DTW distance
    """
    distance, _ = fastdtw(seq1, seq2)
    return distance

def find_best_matching_section(whole_midi, part_midi, window_size):
    """
    Find the section in whole_midi that best matches part_midi.
    :param whole_midi: List of (pitch, duration) for the whole MIDI
    :param part_midi: List of (pitch, duration) for the part MIDI
    :param window_size: Size of the sliding window
    :return: Best start and end positions in the whole MIDI
    """
    best_distance = float('inf')
    best_start = 0
    best_end = 0

    for start in range(0, len(whole_midi) - window_size + 1):
        end = start + window_size
        window = whole_midi[start:end]
        distance = calculate_dtw_distance(window, part_midi)
        if distance < best_distance:
            best_distance = distance
            best_start = start
            best_end = end

    return best_start, best_end, best_distance

def filter_by_start_time(whole_midi, start_time):
    filtered = []
    for midi in whole_midi:
        if midi[1] > start_time + 5:
            break
        elif midi[1] >= start_time:
            filtered.append(midi)
    return filtered

def tracking(whole_midi, part_midi, start_time):
    whole_midi = filter_by_start_time(whole_midi, start_time)

    window_size = len(part_midi)
    best_start, best_end, best_distance = find_best_matching_section(whole_midi, part_midi, window_size)
    play_time = whole_midi[best_end][1]

    return best_start, best_end, play_time
