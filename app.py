import os
import requests
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
from PyPDF2 import PdfReader
from Question_generation.Retrivel import retrieve_docs_from_all_collections
from Question_generation.models import InterviewQA, session
from Evaluation_module.evaluation import evaluate_answer, extract_evaluation
from Question_generation.llm_utils import parallel_llm_queries
import re
import Resume_strengthening.resume_strengthening as rs
from RL_module.dynamic_difficulty import DynamicDifficulty
from speech_analysis import SpeechAnalysis
import tempfile

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

API_URL = "https://router.huggingface.co/novita/v3/openai/chat/completions"
API_KEY1 = os.environ.get("HF_API_KEY1", "")
API_KEY2 = os.environ.get("HF_API_KEY2", "")

resume_text_global = ""
difficulty_level_global = "Easy"
last_answer_global = ""  # Hardcoded storage for last answer
resume_strengthening_global = ""

# Initialize the dynamic difficulty adjuster
difficulty_adjuster = DynamicDifficulty(initial_difficulty="Easy")

# Initialize the speech analyzer
speech_analyzer = SpeechAnalysis()

def remove_first_think(text):
    # Remove only the first occurrence of <think>...</think> and its content
    return re.sub(r'<think>.*?</think>', '', text, count=1, flags=re.DOTALL)

@app.route('/upload_resume', methods=['POST'])
def upload_resume():
    global resume_text_global, difficulty_level_global, resume_strengthening_global, difficulty_adjuster

    if 'resume' not in request.files:
        return jsonify({'error': 'No resume uploaded'}), 400

    file = request.files['resume']
    job_description = request.form.get('job_description', '')
    difficulty = request.form.get('difficulty', 'Easy')
    difficulty_level_global = difficulty
    
    # Initialize the difficulty adjuster with the selected difficulty
    difficulty_adjuster = DynamicDifficulty(initial_difficulty=difficulty)

    if file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    filepath = os.path.join(UPLOAD_FOLDER, secure_filename(file.filename))
    file.save(filepath)

    

    try:
        reader = PdfReader(filepath)
        text = ''.join([page.extract_text() or '' for page in reader.pages])
        resume_text_global = text
        resume_strengthening_global = rs.strengthen_resume(resume_text_global, job_description)
        return jsonify({
            'text': text,
            'job_description': job_description,
            'difficulty': difficulty,
            'resume_strengthening': resume_strengthening_global
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/chat', methods=['POST'])
def chat():
    global resume_text_global, difficulty_level_global, last_answer_global, difficulty_adjuster

    data = request.get_json()
    user_message = data.get("message", "").strip()
    
    # Check if frontend is setting a manual difficulty override
    if data.get("current_difficulty") and data.get("current_difficulty") != difficulty_level_global:
        difficulty_level_global = data.get("current_difficulty")
        difficulty_adjuster.current_difficulty = difficulty_level_global

    if not user_message:
        return jsonify({"reply": "Please type a message."})

    # Get context for all questions with difficulty level
    context_docs = "\n\n".join(retrieve_docs_from_all_collections(f"{difficulty_level_global} HR interview questions", k=3))

    # If not starting, evaluate and store the previous answer
    if user_message.lower() == "start":
        # First question generation
        prompt = (
            f"You are an HR interviewer conducting a real interview.\n\n"
            f"Candidate's resume:\n{resume_text_global}\n\n"
            f"Context from {difficulty_level_global} HR questions:\n{context_docs}\n\n"
            "Your task: ask the FIRST HR interview question. "
            "IMPORTANT: Only ask the question. Do not provide answers or explanations. "
            "Output only the question. "
            "Address the candidate with his name"
        )
        messages = [
            {"role": "system", "content": "You are an HR interviewer. Your ONLY job is to ask a single HR interview question at a time. DO NOT provide answers. DO NOT provide explanations. Ask a question that is suitable for the interview. Only output the question itself."},
            {"role": "user", "content": prompt}
        ]
        
        # For first question, we only need one API call
        tasks = [(messages, API_KEY1)]
        results = parallel_llm_queries(tasks)
        reply = remove_first_think(results[0].strip())
        
        # Store the first question
        new_question = InterviewQA(
            question=reply,
            difficulty=difficulty_level_global,
            answer="",
            score=0
        )
        session.add(new_question)
        session.commit()
        
        last_answer_global = ""
        return jsonify({"reply": reply})
        

    elif(user_message.lower() == "exit"):
        # When user types "exit", return all QAs from the database as JSON (no overall feedback)
        all_qas = session.query(InterviewQA).order_by(InterviewQA.timestamp).all()
        if not all_qas:
            return jsonify({"reply": "No interview data found to generate feedback."})
        # Prepare a list of QAs
        qa_list = []
        for idx, qa in enumerate(all_qas, 1):
            qa_list.append({
                'id': qa.id,
                'question': qa.question,
                'answer': qa.answer,
                'score': qa.score,
                'feedback': qa.feedback,
                'confidence_score': getattr(qa, 'confidence_score', 0),
                'confidence_feedback': getattr(qa, 'confidence_feedback', ''),
                'difficulty': qa.difficulty,
                'timestamp': qa.timestamp.isoformat() if qa.timestamp else None
            })
        # Store the JSON in a variable before deleting
        exit_data = {"qas": qa_list, "resume_strengthening": resume_strengthening_global}
        # Optionally clear the table after returning
        session.query(InterviewQA).delete()
        session.commit()
        # Return the JSON in a frontend-friendly format (always as a 'qas' array)
        return jsonify(exit_data)

    else:
        # Get the last question from the database
        last_question = session.query(InterviewQA).order_by(InterviewQA.id.desc()).first()
        if last_question:  # Only update if answer is empty
            # Prepare evaluation messages
            eval_messages = evaluate_answer(last_question.question, user_message, difficulty_level_global)
            
            # Generate next question and evaluate answer in parallel
            next_q_messages = [
                {"role": "system", "content": "You are an HR interviewer. Your ONLY job is to ask a single HR interview question at a time. DO NOT provide answers. DO NOT provide explanations. Ask a question that is suitable for the interview. Only output the question itself."},
                {
                    "role": "user",
                    "content": (
                        f"Candidate's resume:\n{resume_text_global}\n\n"
                        f"Context from HR documentation:\n{context_docs}\n\n"
                        f"Candidate's last response: {user_message}\n\n"
                        f"Based on the resume, context, and previous response, ask the next HR question. "
                        f"Difficulty: {difficulty_level_global}. Just ask a question."
                        "IMPORTANT: Only ask the question. Do not provide answers or explanations. "
                        "Output only the question. "
                        "Address the candidate with his name"
                    )
                }
            ]
            
            # Run LLM queries in parallel
            tasks = [
                (next_q_messages, API_KEY1),  # Generate next question
                (eval_messages, API_KEY2)      # Evaluate current answer
            ]
            results = parallel_llm_queries(tasks)
            
            # Extract results
            next_question = remove_first_think(results[0].strip())
            evaluation_response = results[1]
            
            # Process evaluation
            score, reason, improvement = extract_evaluation(evaluation_response)
            
            
            last_question.answer = user_message
            last_question.score = score
            last_question.feedback = f"Reason: {reason}\nImprovement Areas: {improvement}"
            
            # Make sure confidence score is preserved if it was previously set
            if not hasattr(last_question, 'confidence_score') or last_question.confidence_score is None:
                last_question.confidence_score = 0.0
                
            # Commit changes to database
            session.commit()
            print(f"Updated question ID: {last_question.id} with score: {score}, confidence: {last_question.confidence_score}")
            
            # Use the RL module to adjust difficulty based on the user's score

            new_difficulty, explanation = difficulty_adjuster.add_score(score)
            
            # Check if difficulty changed
            difficulty_changed = new_difficulty != difficulty_level_global
            if difficulty_changed:
                difficulty_level_global = new_difficulty
            
            # Store the new question
            new_question = InterviewQA(
                question=next_question,
                difficulty=difficulty_level_global,
                answer="",
                score=0
            )
            session.add(new_question)
            session.commit()
            
            # Get confidence data if available
            confidence_score = getattr(last_question, 'confidence_score', 0)
            confidence_feedback = getattr(last_question, 'confidence_feedback', '')
            
            # Include suggested difficulty in response if changed
            if difficulty_changed:
                return jsonify({
                    "reply": next_question,
                    "suggested_difficulty": new_difficulty,
                    "difficulty_explanation": explanation,
                    "confidence_score": confidence_score,
                    "confidence_feedback": confidence_feedback
                })
            else:
                return jsonify({
                    "reply": next_question,
                    "confidence_score": confidence_score,
                    "confidence_feedback": confidence_feedback
                })
        else:
            # If we get here, we either have no last question, or the last question already has an answer
            # In both cases, we need to return something to avoid the None response error
            if last_question and last_question.answer:
                print(f"Question ID {last_question.id} already has an answer: '{last_question.answer}'")
                # Get the last question with an empty answer, or create a new one if none exists
                new_last_question = session.query(InterviewQA).filter(InterviewQA.answer == "").order_by(InterviewQA.id.desc()).first()
                
                if new_last_question:
                    print(f"Found unanswered question ID {new_last_question.id}: '{new_last_question.question}'")
                    return jsonify({
                        "reply": new_last_question.question,
                        "confidence_score": getattr(last_question, 'confidence_score', 0),
                        "message": "Continuing with existing question"
                    })
                else:
                    # No unanswered questions exist, create a new one
                    print("Creating a new question since all previous questions have answers")
                    # Generate a new question
                    new_q_messages = [
                        {"role": "system", "content": "You are an HR interviewer. Your ONLY job is to ask a single HR interview question at a time."},
                        {"role": "user", "content": f"Ask a new HR interview question at {difficulty_level_global} difficulty level."}
                    ]
                    tasks = [(new_q_messages, API_KEY1)]
                    results = parallel_llm_queries(tasks)
                    new_question_text = remove_first_think(results[0].strip())
                    
                    # Store the new question
                    new_question = InterviewQA(
                        question=new_question_text,
                        difficulty=difficulty_level_global,
                        answer="",
                        score=0
                    )
                    session.add(new_question)
                    session.commit()
                    
                    return jsonify({
                        "reply": new_question_text,
                        "message": "Created a new question"
                    })
            else:
                # No questions exist yet
                print("No questions found in database, starting with a new question")
                # Generate a first question
                first_q_messages = [
                    {"role": "system", "content": "You are an HR interviewer. Your ONLY job is to ask a single HR interview question at a time."},
                    {"role": "user", "content": f"Ask an initial HR interview question at {difficulty_level_global} difficulty level."}
                ]
                tasks = [(first_q_messages, API_KEY1)]
                results = parallel_llm_queries(tasks)
                first_question = remove_first_think(results[0].strip())
                
                # Store the first question
                new_question = InterviewQA(
                    question=first_question,
                    difficulty=difficulty_level_global,
                    answer="",
                    score=0
                )
                session.add(new_question)
                session.commit()
                
                return jsonify({
                    "reply": first_question,
                    "message": "Starting new interview"
                })
            
        # This line should never be reached as all paths now return a response
        # But keeping it as a fallback just in case
        last_answer_global = user_message
        return jsonify({"reply": "Please type 'start' to begin the interview."})
        

@app.route('/get_feedback', methods=['GET'])
def get_feedback():
    try:
        # Get all interview QAs from the database that have answers and feedback
        feedback_items = session.query(InterviewQA).filter(InterviewQA.answer != "").all()
        print(f"Found {len(feedback_items)} feedback items in database")
        
        # Convert SQLAlchemy objects to dictionaries
        feedback_data = []
        for item in feedback_items:
            # Debug each item
            print(f"Processing item ID: {item.id}, Question: {item.question[:30]}...")
            print(f"  Raw confidence_score: {item.confidence_score}, Type: {type(item.confidence_score)}")
            
            # Direct database check to verify data
            # Connect directly to the database to verify
            import sqlite3
            conn = sqlite3.connect('interview.db')
            cursor = conn.cursor()
            cursor.execute('SELECT confidence_score, confidence_feedback FROM interview_qa WHERE id = ?', (item.id,))
            db_result = cursor.fetchone()
            print(f"  From direct DB query: confidence_score={db_result[0]}, feedback={db_result[1][:30] if db_result[1] else None}")
            conn.close()
            
            # Safely get confidence_score with a fallback to 0
            try:
                if hasattr(item, 'confidence_score') and item.confidence_score is not None:
                    confidence_score = float(item.confidence_score)
                    print(f"  Converted confidence_score: {confidence_score}")
                else:
                    confidence_score = 0.0
                    print(f"  No confidence_score attribute or value is None, using default: {confidence_score}")
            except (ValueError, TypeError) as e:
                confidence_score = 0.0
                print(f"  Error converting confidence_score: {e}, using default: {confidence_score}")
                
            # Only include essential confidence feedback without verbose details
            confidence_feedback = None
            if hasattr(item, 'confidence_feedback') and item.confidence_feedback:
                # Extract just the first sentence which typically has the confidence assessment
                feedback_parts = item.confidence_feedback.split('.')
                if feedback_parts:
                    confidence_feedback = feedback_parts[0] + "."
                print(f"  Using confidence_feedback: {confidence_feedback}")
            else:
                print("  No confidence_feedback attribute or it's empty")
            
            feedback_data.append({
                'id': item.id,
                'question': item.question,
                'answer': item.answer,
                'difficulty': item.difficulty,
                'score': float(item.score),  # Ensure this is sent as a float
                'feedback': item.feedback,
                'timestamp': item.timestamp.isoformat() if item.timestamp else None,
                'confidence_score': confidence_score,
                'confidence_feedback': confidence_feedback
            })
        
        return jsonify({
            'success': True,
            'feedback': feedback_data
        })
    except Exception as e:
        print(f"Error in get_feedback: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/get_difficulty', methods=['GET'])
def get_difficulty():
    global difficulty_level_global, difficulty_adjuster
    
    return jsonify({
        'current_difficulty': difficulty_level_global,
        'available_difficulties': difficulty_adjuster.difficulties
    })
    
@app.route('/update_confidence', methods=['POST'])
def update_confidence():
    """Update confidence score for a specific question/answer."""
    try:
        data = request.get_json()
        question_id = data.get('id')
        confidence_score = data.get('confidence_score')
        
        if not question_id or confidence_score is None:
            return jsonify({'error': 'Missing question ID or confidence score'}), 400
            
        # Find the question in the database
        question = session.query(InterviewQA).filter(InterviewQA.id == question_id).first()
        if not question:
            return jsonify({'error': f'Question with ID {question_id} not found'}), 404
            
        # Update the confidence score
        question.confidence_score = float(confidence_score)
        
        # Generate new confidence feedback based on the score
        analysis = speech_analyzer.analyze_speech(question.answer if question.answer else "")
        question.confidence_feedback = analysis['feedback']
        
        session.commit()
        
        return jsonify({
            'success': True,
            'id': question.id,
            'confidence_score': question.confidence_score,
            'confidence_feedback': question.confidence_feedback
        })
    except Exception as e:
        print(f"Error in update_confidence: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/transcribe', methods=['POST'])
def transcribe_audio():
    # Check if audio file was included
    if 'audio' not in request.files:
        print("Error: No audio file provided in request")
        return jsonify({'error': 'No audio file provided'}), 400
    
    audio_file = request.files['audio']
    if audio_file.filename == '':
        print("Error: Empty filename in audio file")
        return jsonify({'error': 'Empty filename'}), 400
    
    print(f"Received audio file: {audio_file.filename}, Content-Type: {audio_file.content_type}")
    
    # Setup variables outside try block to make them available in finally
    audio_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp_audio')
    temp_audio_path = None
    temp_wav_path = None
    temp_filename = None
    transcript = None
    file_size = 0
    
    try:
        # Create directory for audio files
        os.makedirs(audio_dir, exist_ok=True)
        
        # Determine the original format from content-type
        content_type = audio_file.content_type
        extension = '.bin'  # Default binary
        
        # Map content types to extensions more accurately
        content_type_map = {
            'audio/webm': '.webm',
            'audio/ogg': '.ogg',
            'audio/mp3': '.mp3',
            'audio/wav': '.wav',
            'audio/x-wav': '.wav',
            'audio/mpeg': '.mp3',
            'audio/mp4': '.mp4',
            'video/webm': '.webm'  # Some browsers encode audio in video containers
        }
        
        # Get extension from content type or use default
        for ct_prefix, ext in content_type_map.items():
            if content_type and ct_prefix in content_type.lower():
                extension = ext
                break
                
        # Generate a unique filename with timestamp
        timestamp = int(time.time() * 1000)
        temp_filename = f"audio_{timestamp}_{os.getpid()}{extension}"
        temp_audio_path = os.path.join(audio_dir, temp_filename)
        
        # Save the audio file
        audio_file.save(temp_audio_path)
        print(f"Saved audio to temporary file: {temp_audio_path} (Content-Type: {content_type})")
        
        # Check if the file was saved correctly
        file_size = os.path.getsize(temp_audio_path)
        print(f"Temporary audio file size: {file_size} bytes")
        if file_size == 0:
            return jsonify({'error': 'Empty audio file uploaded'}), 400
            
        # Check if the file is a valid audio file
        if file_size < 100:  # Arbitrary small size that's too small for valid audio
            return jsonify({'error': 'Audio file too small to be valid'}), 400
        
        # Always convert to WAV to ensure compatibility
        print("Converting to WAV format for transcription...")
        from pydub import AudioSegment
        
        # Create a temporary WAV file
        temp_wav_path = os.path.join(audio_dir, f"converted_{timestamp}.wav")
        
        try:
            # Try to load the audio in multiple formats
            audio = None
            formats_to_try = ["wav", "webm", "mp3", "ogg", "raw"]
            
            for format_type in formats_to_try:
                try:
                    print(f"Trying to load audio as {format_type} format")
                    if format_type == "raw":
                        # For raw audio, try with different parameters
                        try:
                            audio = AudioSegment.from_file(
                                temp_audio_path,
                                format="raw",
                                frame_rate=44100,
                                channels=1,
                                sample_width=2
                            )
                            print("Successfully loaded as raw format with default parameters")
                            break
                        except:
                            try:
                                # Try another common configuration
                                audio = AudioSegment.from_file(
                                    temp_audio_path,
                                    format="raw",
                                    frame_rate=16000,
                                    channels=1,
                                    sample_width=2
                                )
                                print("Successfully loaded as raw format with 16kHz mono")
                                break
                            except Exception as raw_err:
                                print(f"Failed to load as raw format: {raw_err}")
                    else:
                        audio = AudioSegment.from_file(temp_audio_path, format=format_type)
                        print(f"Successfully loaded audio as {format_type}")
                        print(f"Audio properties: {len(audio)}ms, {audio.channels} channels, {audio.frame_rate}Hz")
                        break
                except Exception as format_err:
                    print(f"Failed to load as {format_type}: {format_err}")
            
            if audio is None:
                raise ValueError("Could not load audio file in any supported format")
            
            # Normalize audio (adjust volume)
            print("Normalizing audio...")
            normalized_audio = audio.normalize()
            
            # Convert to standard format: mono, 16-bit, 16kHz (good for speech recognition)
            print("Converting to standard format (mono, 16kHz, 16-bit)...")
            standard_audio = normalized_audio.set_channels(1).set_frame_rate(16000).set_sample_width(2)
            
            # Export with specific parameters for better compatibility
            standard_audio.export(
                temp_wav_path,
                format="wav",
                parameters=["-ac", "1", "-ar", "16000"]
            )
            print(f"Audio exported to WAV: {temp_wav_path}")
            
            # Verify the output file
            if os.path.exists(temp_wav_path) and os.path.getsize(temp_wav_path) > 0:
                print(f"Conversion successful. Output WAV size: {os.path.getsize(temp_wav_path)} bytes")
            else:
                print(f"Conversion failed. Output WAV file is missing or empty")
                raise ValueError("WAV conversion failed - output file is empty or missing")
                
        except Exception as conv_error:
            print(f"Error during WAV conversion: {conv_error}")
            import traceback
            traceback.print_exc()
            # Continue with original file as fallback
            print("Falling back to original audio file for transcription")
            temp_wav_path = temp_audio_path
        
        # After conversion to WAV, log the duration of the audio for debugging incomplete recordings
        try:
            if temp_wav_path and os.path.exists(temp_wav_path):
                from pydub import AudioSegment
                audio_segment = AudioSegment.from_wav(temp_wav_path)
                duration_sec = len(audio_segment) / 1000.0
                print(f"[AUDIO DEBUG] Converted WAV duration: {duration_sec:.2f} seconds, file size: {os.path.getsize(temp_wav_path)} bytes")
        except Exception as duration_log_err:
            print(f"[AUDIO DEBUG] Could not determine WAV duration: {duration_log_err}")
        
        # Transcribe the audio using the WAV file
        print(f"Starting audio transcription using file: {temp_wav_path}")
        transcript, error = speech_analyzer.transcribe_audio(temp_wav_path)
        
        if error:
            print(f"Transcription error: {error}")
            return jsonify({'error': f"Transcription failed: {error}"}), 500
        
        print(f"Transcription successful: '{transcript}'")
        
        # Analyze the speech
        print("Analyzing speech patterns...")
        analysis_results = speech_analyzer.analyze_speech(transcript)
        print(f"Analysis results: {analysis_results}")
        
        # If this is an answer to a question, update the database
        last_question = session.query(InterviewQA).order_by(InterviewQA.id.desc()).first()
        if last_question and last_question.answer == "":
            # First, update the answer with the transcript
            last_question.answer = transcript
            
            # Update the confidence score and feedback in database
            print(f"Updating confidence data for question ID: {last_question.id}")
            last_question.confidence_score = analysis_results['confidence_score']
            last_question.confidence_feedback = analysis_results['feedback']
            
            # Commit these changes immediately to ensure they're saved before another question is asked
            session.commit()
            print(f"Database updated with confidence score: {last_question.confidence_score}")
            
            # Return a simplified response without detailed feedback
            return jsonify({
                'transcript': transcript,
                'confidence_score': analysis_results['confidence_score'],
                'filler_count': analysis_results['filler_count'],
                'word_count': analysis_results['word_count']
            })
        else:
            # No question to update, just return the transcript
            print("No current question to update with confidence data")
            return jsonify({
                'transcript': transcript
            })
        
    except Exception as e:
        print(f"Error in transcribe_audio: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f"Processing error: {str(e)}"}), 500
        
    finally:
        # Always attempt to clean up, even if there was an error
        for path in [temp_audio_path, temp_wav_path]:
            if path and os.path.exists(path):
                try:
                    os.unlink(path)
                    print(f"Deleted temporary file: {path}")
                except Exception as cleanup_e:
                    print(f"Warning: Could not delete temporary file {path}: {str(cleanup_e)}")
        
        # Keep a log if we have the necessary information
        if temp_filename and audio_dir:
            try:
                with open(os.path.join(audio_dir, "audio_log.txt"), "a") as log_file:
                    log_file.write(f"{temp_filename}: Size={file_size}, Result={'Success' if transcript else 'Failed'}, Transcript='{transcript}'\n")
            except Exception as log_e:
                print(f"Warning: Could not write to log file: {str(log_e)}")

if __name__ == '__main__':
    app.run(debug=True, port=8000)  # Run the Flask app on port 8000