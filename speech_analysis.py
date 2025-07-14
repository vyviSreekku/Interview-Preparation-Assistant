"""
Speech analysis module for the Interview Preparation Assistant.
This module handles audio transcription and analysis of speech patterns.
"""
import re
import speech_recognition as sr
import os
import math
import numpy as np
import time
from tempfile import NamedTemporaryFile
import sys

# Set up ffmpeg path before importing pydub
ffmpeg_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ffmpeg', 'bin')
os.environ["PATH"] += os.pathsep + ffmpeg_dir
print(f"Added ffmpeg directory to PATH: {ffmpeg_dir}")

# Check if ffmpeg exists in the specified path
ffmpeg_exe = os.path.join(ffmpeg_dir, "ffmpeg.exe")
if os.path.exists(ffmpeg_exe):
    print(f"ffmpeg.exe found at: {ffmpeg_exe}")
else:
    print(f"WARNING: ffmpeg.exe not found at expected location: {ffmpeg_exe}")

# Now import pydub after setting the path
from pydub import AudioSegment

# Directly configure pydub to use the local ffmpeg binaries
AudioSegment.converter = ffmpeg_exe
AudioSegment.ffmpeg = ffmpeg_exe
AudioSegment.ffprobe = os.path.join(ffmpeg_dir, "ffprobe.exe")

print(f"Configured pydub with: converter={AudioSegment.converter}")
print(f"Python version: {sys.version}")
print(f"Pydub version: {AudioSegment.__version__ if hasattr(AudioSegment, '__version__') else 'unknown'}")

# List of common filler words to detect
FILLER_WORDS = {
    'um', 'uh', 'ah', 'er', 'like', 'you know', 'so', 'basically', 'actually', 
    'literally', 'kinda', 'sorta', 'i mean', 'i guess', 'right', 'okay', 'hmm'
}

class SpeechAnalysis:
    def __init__(self):
        self.recognizer = sr.Recognizer()
    
    def convert_to_wav(self, audio_file_path):
        """Convert audio file to WAV format if needed."""
        try:
            # Check if file exists
            if not os.path.exists(audio_file_path):
                print(f"Error: Audio file does not exist at path: {audio_file_path}")
                return None, "Audio file not found"
                
            # Check file size
            file_size = os.path.getsize(audio_file_path)
            print(f"Input audio file size: {file_size} bytes")
            if file_size == 0:
                print(f"Error: Audio file is empty: {audio_file_path}")
                return None, "Audio file is empty"
            
            # Create a temporary WAV file in temp_audio directory
            temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp_audio')
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)
            temp_wav = NamedTemporaryFile(suffix='.wav', delete=False, dir=temp_dir).name
            print(f"Created temporary WAV file: {temp_wav}")
            
            # Get the file extension from the path
            _, file_extension = os.path.splitext(audio_file_path)
            print(f"Input file extension: {file_extension}")
            
            # Even if the file has .wav extension, we'll convert it to a standard format
            # as browser-recorded audio can have incorrect formats despite the extension
            
            # Load the audio and export as WAV
            print(f"Converting audio to standard WAV format (ignoring extension: {file_extension})")
            try:
                # Instead of relying on the extension, try to load the audio in multiple formats
                audio = None
                formats_to_try = ["wav", "webm", "mp3", "ogg", "raw"]
                errors = []
                
                for format_type in formats_to_try:
                    try:
                        print(f"Trying to load audio as {format_type} format")
                        if format_type == "raw":
                            # For raw audio, try with different parameters
                            try:
                                # Try with 44.1kHz mono
                                audio = AudioSegment.from_file(
                                    audio_file_path, 
                                    format="raw",
                                    frame_rate=44100,
                                    channels=1,
                                    sample_width=2
                                )
                                print("Successfully loaded as raw format with 44.1kHz mono")
                                break
                            except:
                                # Try with 16kHz mono
                                try:
                                    audio = AudioSegment.from_file(
                                        audio_file_path, 
                                        format="raw",
                                        frame_rate=16000,
                                        channels=1,
                                        sample_width=2
                                    )
                                    print("Successfully loaded as raw format with 16kHz mono")
                                    break
                                except Exception as raw_err:
                                    errors.append(f"Raw format error: {str(raw_err)}")
                        else:
                            audio = AudioSegment.from_file(audio_file_path, format=format_type)
                            print(f"Successfully loaded audio as {format_type}")
                            print(f"Audio properties: {len(audio)}ms, {audio.channels} channels, {audio.frame_rate}Hz")
                            break
                    except Exception as format_err:
                        errors.append(f"{format_type} format error: {str(format_err)}")
                        print(f"Failed to load as {format_type}: {format_err}")
                    except Exception as format_err:
                        print(f"Failed to load as {format_type}: {format_err}")
                
                if audio is None:
                    raise ValueError("Could not load audio file in any supported format")
                
                # Normalize audio (adjust volume)
                normalized_audio = audio.normalize()
                
                # Convert to standard format: mono, 16-bit, 16kHz (good for speech recognition)
                standard_audio = normalized_audio.set_channels(1).set_frame_rate(16000).set_sample_width(2)
                
                # Export with specific parameters for better compatibility
                standard_audio.export(
                    temp_wav, 
                    format="wav",
                    parameters=["-ac", "1", "-ar", "16000"]
                )
                print(f"Audio exported to {temp_wav}")
                
                # Verify the output file
                if os.path.exists(temp_wav) and os.path.getsize(temp_wav) > 0:
                    print(f"Conversion successful. Output size: {os.path.getsize(temp_wav)} bytes")
                    return temp_wav, None
                else:
                    print(f"Conversion failed. Output file is missing or empty")
                    return None, "Audio conversion failed"
            except Exception as conv_error:
                print(f"Error during audio conversion: {conv_error}")
                return None, f"Audio conversion error: {str(conv_error)}"
        except Exception as e:
            print(f"Unexpected error in convert_to_wav: {e}")
            import traceback
            traceback.print_exc()
            return None, f"Audio processing error: {str(e)}"
    
    def transcribe_audio(self, audio_file_path):
        """Transcribe audio file to text."""
        temp_file_created = False
        wav_file = None
        
        try:
            # First check if the input file exists and has content
            if not os.path.exists(audio_file_path):
                error_msg = f"Input audio file not found: {audio_file_path}"
                print(error_msg)
                return None, error_msg
                
            if os.path.getsize(audio_file_path) == 0:
                error_msg = "Input audio file is empty"
                print(error_msg)
                return None, error_msg
                
            # Log file info
            print(f"Processing audio file: {audio_file_path}")
            print(f"File size: {os.path.getsize(audio_file_path)} bytes")
            print(f"File last modified: {time.ctime(os.path.getmtime(audio_file_path))}")
            
            # Convert to WAV if needed
            print(f"Converting audio file to WAV: {audio_file_path}")
            wav_file, error = self.convert_to_wav(audio_file_path)
            if error:
                print(f"Error in conversion: {error}")
                return None, error
                
            if wav_file != audio_file_path:
                temp_file_created = True
                
            print(f"Using WAV file for transcription: {wav_file}")
            
            # Check WAV file exists and has content
            if not os.path.exists(wav_file):
                error_msg = f"WAV file not found: {wav_file}"
                print(error_msg)
                return None, error_msg
                
            if os.path.getsize(wav_file) == 0:
                error_msg = "WAV file is empty"
                print(error_msg)
                return None, error_msg
                
            # Skip WAV header validation since we'll convert all files anyway
            print("Proceeding with transcription...")
                
            # Use SpeechRecognition to transcribe
            try:
                print("Opening audio file for transcription")
                with sr.AudioFile(wav_file) as source:
                    print("Recording audio data from file")
                    audio_data = self.recognizer.record(source)
                    
                    print("Sending to Google Speech Recognition")
                    # Use Google's speech recognition
                    text = self.recognizer.recognize_google(audio_data)
                    print(f"Transcription result: '{text}'")
                    
                    return text, None
            except sr.UnknownValueError:
                print("Speech Recognition could not understand audio")
                return None, "Could not understand audio. Please speak more clearly or check your microphone."
            except sr.RequestError as e:
                print(f"Speech Recognition service error: {e}")
                return None, f"Speech recognition service unavailable: {e}"
            except Exception as transcribe_err:
                print(f"Error during transcription: {transcribe_err}")
                import traceback
                traceback.print_exc()
                return None, f"Transcription error: {str(transcribe_err)}"
                
        except Exception as e:
            print(f"Unexpected error in transcribe_audio: {e}")
            import traceback
            traceback.print_exc()
            return None, f"Audio processing error: {str(e)}"
        finally:
            # Delete temporary WAV if we created one
            if temp_file_created and wav_file and os.path.exists(wav_file):
                try:
                    os.remove(wav_file)
                    print(f"Deleted temporary WAV file: {wav_file}")
                except Exception as cleanup_err:
                    print(f"Warning: Could not delete temporary file: {cleanup_err}")
    
    def analyze_speech(self, transcript, audio_duration_sec=None):
        """Analyze speech for fillers, rate of speech, etc. Optionally use audio_duration_sec for accurate WPM."""
        if not transcript:
            return {
                'fillers': [],
                'filler_count': 0,
                'filler_rate': 0,
                'word_count': 0,
                'confidence_score': 0,
                'rate_of_speech': 0,
                'feedback': "Unable to analyze empty transcript."
            }
        
        # Make lowercase for analysis
        text = transcript.lower()
        
        # Get word count - better tokenization
        words = re.findall(r'\b[a-z\']+\b', text)  # Find actual words, ignore punctuation
        word_count = len(words)
        
        print(f"Analyzing transcript with {word_count} words: '{transcript[:50]}...'")
        
        if word_count < 3:
            print(f"Warning: Very short transcript with only {word_count} words")
            return {
                'fillers': [],
                'filler_count': 0,
                'filler_rate': 0,
                'word_count': word_count,
                'confidence_score': 5.0,  # Neutral score for very short answers
                'rate_of_speech': 0,
                'feedback': f"Your response was very brief ({word_count} words). Consider providing a more detailed answer."
            }
        
        # Analyze fillers with improved pattern matching
        fillers_found = []
        for filler in FILLER_WORDS:
            pattern = r'\b' + re.escape(filler) + r'\b'
            matches = re.findall(pattern, text)
            for match in matches:
                fillers_found.append(match)
        
        filler_count = len(fillers_found)
        filler_rate = filler_count / word_count if word_count > 0 else 0
        
        # --- Rate of Speech Calculation ---
        # Use provided audio_duration_sec if available, else estimate
        if audio_duration_sec and audio_duration_sec > 0:
            duration_min = audio_duration_sec / 60.0
        else:
            # Estimate duration using average speaking rate (150 wpm)
            duration_min = word_count / 150 if word_count > 0 else 1
        rate_of_speech = word_count / duration_min if duration_min > 0 else 0
        print(f"Estimated/actual rate of speech: {rate_of_speech:.1f} WPM")
        
        # --- Confidence Score Calculation (improved) ---
        # Start with 10, subtract a small penalty for all answers
        confidence_base = 9.5  # Max is now 9.5 unless perfect
        # Filler penalty
        confidence_base -= (filler_rate * 100) * 0.12  # More sensitive to fillers
        # Length factor (more influential)
        if word_count < 10:
            confidence_base -= 2.0  # Strong penalty for too short
        elif word_count < 30:
            confidence_base -= 1.0  # Mild penalty for short
        elif word_count > 200:
            confidence_base -= 0.5  # Slight penalty for rambling
        elif 40 <= word_count <= 120:
            confidence_base += 0.5  # Reward ideal range
        # Rate of speech factor (more influential)
        if rate_of_speech < 90:
            confidence_base -= 1.0
        elif rate_of_speech > 180:
            confidence_base -= 1.0
        elif 120 <= rate_of_speech <= 150:
            confidence_base += 0.5  # Reward ideal speaking rate
        
        # Clamp between 0-10, but only allow 10 if all ideal
        confidence_score = min(10, max(0, round(confidence_base, 1)))
        
        # If truly perfect (no fillers, ideal length, ideal rate), allow 10
        if (
            filler_count == 0 and
            40 <= word_count <= 120 and
            120 <= rate_of_speech <= 150
        ):
            confidence_score = 10.0
        
        # Generate feedback
        feedback = self._generate_feedback(confidence_score, filler_count, filler_rate, word_count, rate_of_speech)
        
        result = {
            'fillers': fillers_found,
            'filler_count': filler_count,
            'filler_rate': filler_rate,
            'word_count': word_count,
            'confidence_score': confidence_score,
            'rate_of_speech': round(rate_of_speech, 1),
            'feedback': feedback
        }
        
        print(f"Speech analysis result: {result}")
        return result
    
    def _generate_feedback(self, confidence_score, filler_count, filler_rate, word_count, rate_of_speech=None):
        """Generate more detailed and helpful feedback based on speech analysis, including rate of speech."""
        feedback_parts = []
        
        # Confidence level assessment
        if confidence_score >= 8.5:
            feedback_parts.append("Your speech shows excellent confidence and clarity.")
        elif confidence_score >= 7:
            feedback_parts.append("Your speech shows very good confidence overall.")
        elif confidence_score >= 6:
            feedback_parts.append("Your speech shows good confidence.")
        elif confidence_score >= 4:
            feedback_parts.append("Your speech shows moderate confidence.")
        elif confidence_score >= 2:
            feedback_parts.append("Your speech shows some hesitation that may impact perceived confidence.")
        else:
            feedback_parts.append("Your speech confidence could use improvement.")
        
        # Always define filler_percentage
        filler_percentage = 0
        # Filler word feedback with specific tips
        if filler_count > 0:
            filler_percentage = filler_rate * 100
            if filler_percentage > 15:
                feedback_parts.append(f"You used many filler words ({filler_count}, {filler_percentage:.1f}% of speech). Try to pause silently instead.")
            elif filler_percentage > 8:
                feedback_parts.append(f"You used several filler words ({filler_count}, {filler_percentage:.1f}% of speech). Practice replacing them with brief pauses.")
            elif filler_percentage > 3:
                feedback_parts.append(f"You used some filler words ({filler_count}, {filler_percentage:.1f}% of speech).")
        else:
            feedback_parts.append("You effectively avoided filler words, which strengthens your delivery.")
        
        # Rate of speech feedback
        if rate_of_speech is not None:
            if rate_of_speech < 90:
                feedback_parts.append(f"You spoke quite slowly ({rate_of_speech:.0f} words per minute). Try to speak a bit faster for a more natural flow.")
            elif rate_of_speech > 180:
                feedback_parts.append(f"You spoke very quickly ({rate_of_speech:.0f} words per minute). Try to slow down for clarity.")
            elif 110 <= rate_of_speech <= 160:
                feedback_parts.append(f"Your speaking rate ({rate_of_speech:.0f} WPM) was ideal for clear communication.")
        
        # Answer length feedback
        if word_count < 10:
            feedback_parts.append("Your answer was very brief. Consider providing more detail in your responses.")
        elif word_count < 30:
            feedback_parts.append("Your answer was somewhat brief. More elaboration could strengthen your response.")
        elif word_count > 200:
            feedback_parts.append("Your answer was quite detailed, which can be good but ensure you're staying focused on the key points.")
        
        # Join feedback parts into one comprehensive feedback string
        comprehensive_feedback = " ".join(feedback_parts)
        
        # Add an improvement tip based on the biggest issue
        if filler_percentage > 10:
            comprehensive_feedback += " Tip: Record yourself practicing answers and listen for filler words."
        elif word_count < 30:
            comprehensive_feedback += " Tip: Try the STAR method (Situation, Task, Action, Result) to structure more complete answers."
        
        return comprehensive_feedback
